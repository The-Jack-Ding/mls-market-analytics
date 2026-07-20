from argparse import ArgumentParser
from pathlib import Path

import pandas as pd


INPUT_FILE = "CRMLSSold_residential_with_mortgage_rates.csv"
OUTPUT_FILE = "CRMLSSold_residential_week4_5_cleaned.csv"

DATE_COLUMNS = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate",
]

NUMERIC_COLUMNS = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
    "Latitude",
    "Longitude",
    "rate_30yr_fixed",
]

# Contact and street-address fields are not needed for market analysis.
DROP_COLUMNS = ["ListAgentEmail", "UnparsedAddress"]


def require_columns(data, columns):
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Required columns are missing: {', '.join(missing)}")


def add_date_flags(data):
    listing = data["ListingContractDate"]
    purchase = data["PurchaseContractDate"]
    close = data["CloseDate"]

    data["listing_after_close_flag"] = listing.notna() & close.notna() & (listing > close)
    data["purchase_after_close_flag"] = purchase.notna() & close.notna() & (purchase > close)
    data["negative_timeline_flag"] = (
        (listing.notna() & purchase.notna() & (listing > purchase))
        | data["listing_after_close_flag"]
        | data["purchase_after_close_flag"]
    )


def add_coordinate_flags(data):
    latitude = data["Latitude"]
    longitude = data["Longitude"]

    data["missing_coordinates_flag"] = latitude.isna() | longitude.isna()
    data["zero_coordinates_flag"] = (latitude == 0) | (longitude == 0)
    data["positive_longitude_flag"] = longitude > 0

    # Approximate California bounds. Null coordinates have their own flag.
    data["implausible_coordinates_flag"] = (
        latitude.notna()
        & longitude.notna()
        & ~latitude.between(32.0, 42.1)
        | latitude.notna()
        & longitude.notna()
        & ~longitude.between(-124.5, -114.0)
    )
    data["invalid_coordinates_flag"] = data[
        [
            "missing_coordinates_flag",
            "zero_coordinates_flag",
            "positive_longitude_flag",
            "implausible_coordinates_flag",
        ]
    ].any(axis=1)


def flag_counts(data, columns):
    rows = len(data)
    return pd.DataFrame(
        {
            "check": columns,
            "flagged_rows": [int(data[column].sum()) for column in columns],
            "flagged_percent": [round(data[column].mean() * 100, 3) for column in columns],
            "total_rows": rows,
        }
    )


def main():
    parser = ArgumentParser(description="Clean the Residential CRMLS sold dataset.")
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "csv",
        help="Folder containing the combined_outputs directory",
    )
    args = parser.parse_args()

    output_dir = args.csv_dir / "combined_outputs"
    input_path = output_dir / INPUT_FILE
    output_path = output_dir / OUTPUT_FILE

    if not input_path.exists():
        raise FileNotFoundError(f"Week 3 dataset not found: {input_path}")

    data = pd.read_csv(input_path, low_memory=False)
    rows_before, columns_before = data.shape
    require_columns(data, DATE_COLUMNS + NUMERIC_COLUMNS)

    # Invalid strings become null so they cannot silently pass as valid values.
    for column in DATE_COLUMNS:
        data[column] = pd.to_datetime(data[column], errors="coerce")

    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    add_date_flags(data)
    add_coordinate_flags(data)

    date_flags = [
        "listing_after_close_flag",
        "purchase_after_close_flag",
        "negative_timeline_flag",
    ]
    coordinate_flags = [
        "missing_coordinates_flag",
        "zero_coordinates_flag",
        "positive_longitude_flag",
        "implausible_coordinates_flag",
        "invalid_coordinates_flag",
    ]

    flag_counts(data, date_flags).to_csv(
        output_dir / "week4_5_date_consistency_summary.csv", index=False
    )
    flag_counts(data, coordinate_flags).to_csv(
        output_dir / "week4_5_geographic_quality_summary.csv", index=False
    )

    invalid_rules = {
        "ClosePrice <= 0": data["ClosePrice"].notna() & (data["ClosePrice"] <= 0),
        "LivingArea <= 0": data["LivingArea"].notna() & (data["LivingArea"] <= 0),
        "DaysOnMarket < 0": data["DaysOnMarket"].notna() & (data["DaysOnMarket"] < 0),
        "BedroomsTotal < 0": data["BedroomsTotal"].notna() & (data["BedroomsTotal"] < 0),
        "BathroomsTotalInteger < 0": (
            data["BathroomsTotalInteger"].notna()
            & (data["BathroomsTotalInteger"] < 0)
        ),
    }

    invalid_row = pd.concat(invalid_rules, axis=1).any(axis=1)
    cleaning_summary = pd.DataFrame(
        [
            {
                "check": rule,
                "flagged_rows": int(mask.sum()),
                "flagged_percent": round(mask.mean() * 100, 3),
            }
            for rule, mask in invalid_rules.items()
        ]
    )
    cleaning_summary.loc[len(cleaning_summary)] = {
        "check": "Any invalid numeric rule (rows removed)",
        "flagged_rows": int(invalid_row.sum()),
        "flagged_percent": round(invalid_row.mean() * 100, 3),
    }

    cleaned = data.loc[~invalid_row].copy()
    cleaned.drop(columns=[c for c in DROP_COLUMNS if c in cleaned.columns], inplace=True)

    cleaning_summary["rows_before"] = rows_before
    cleaning_summary["rows_after"] = len(cleaned)
    cleaning_summary["columns_before"] = columns_before
    cleaning_summary["columns_after"] = cleaned.shape[1]
    cleaning_summary.to_csv(
        output_dir / "week4_5_cleaning_summary.csv", index=False
    )

    dtype_summary = pd.DataFrame(
        {
            "column": DATE_COLUMNS + NUMERIC_COLUMNS,
            "dtype_after_cleaning": [
                str(cleaned[column].dtype) for column in DATE_COLUMNS + NUMERIC_COLUMNS
            ],
            "null_count": [
                int(cleaned[column].isna().sum())
                for column in DATE_COLUMNS + NUMERIC_COLUMNS
            ],
        }
    )
    dtype_summary.to_csv(output_dir / "week4_5_dtype_summary.csv", index=False)

    cleaned.to_csv(output_path, index=False)

    print("\n--- Week 4-5 Cleaning Summary ---")
    print(f"Rows before cleaning: {rows_before:,}")
    print(f"Rows after cleaning:  {len(cleaned):,}")
    print(f"Rows removed:         {rows_before - len(cleaned):,}")
    print(f"Columns before:       {columns_before}")
    print(f"Columns after:        {cleaned.shape[1]}")
    print("\nDate consistency flags:")
    print(flag_counts(data, date_flags).to_string(index=False))
    print("\nGeographic quality flags:")
    print(flag_counts(data, coordinate_flags).to_string(index=False))
    print(f"\nSaved cleaned dataset: {output_path}")


if __name__ == "__main__":
    main()
