from pathlib import Path

import geopandas as gpd
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent
COMBINED_DIR = PROJECT_DIR / "csv" / "combined_outputs"
DISTRICT_FILE = (
    PROJECT_DIR
    / "csv"
    / "reference_data"
    / "California_School_District_Areas_2025_26.geojson"
)
INPUT_FILE = COMBINED_DIR / "CRMLSSold_residential_week4_5_cleaned.csv"
OUTPUT_FILE = COMBINED_DIR / "CRMLSSold_residential_week6_enriched.csv"

DATE_COLUMNS = ["CloseDate", "PurchaseContractDate", "ListingContractDate"]
NUMERIC_COLUMNS = [
    "ClosePrice",
    "OriginalListPrice",
    "LivingArea",
    "DaysOnMarket",
    "Latitude",
    "Longitude",
]


def require_columns(data, columns):
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Required columns are missing: {', '.join(missing)}")


def add_market_metrics(data):
    for column in DATE_COLUMNS:
        data[column] = pd.to_datetime(data[column], errors="coerce")
    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data["PriceRatio"] = (data["ClosePrice"] / data["OriginalListPrice"]).where(
        data["OriginalListPrice"] > 0
    )
    data["CloseToOriginalListRatio"] = data["PriceRatio"]
    data["PricePerSqFt"] = (data["ClosePrice"] / data["LivingArea"]).where(
        data["LivingArea"] > 0
    )
    data["Year"] = data["CloseDate"].dt.year.astype("Int64")
    data["Month"] = data["CloseDate"].dt.month.astype("Int64")
    data["YrMo"] = data["CloseDate"].dt.strftime("%Y-%m")
    data["ListingToContractDays"] = (
        data["PurchaseContractDate"] - data["ListingContractDate"]
    ).dt.days.astype("Int64")
    data["ContractToCloseDays"] = (
        data["CloseDate"] - data["PurchaseContractDate"]
    ).dt.days.astype("Int64")


def add_school_districts(data):
    districts = gpd.read_file(DISTRICT_FILE)
    require_columns(districts, ["DistrictType", "DistrictName", "geometry"])

    unified = districts.loc[
        districts["DistrictType"].eq("Unified"), ["DistrictName", "geometry"]
    ].dropna(subset=["DistrictName", "geometry"])
    unified = unified.copy()
    unified["geometry"] = unified.geometry.make_valid()

    valid_coordinates = (
        data["Latitude"].notna()
        & data["Longitude"].notna()
        & data["Latitude"].between(32.0, 42.1)
        & data["Longitude"].between(-124.5, -114.0)
    )

    points = gpd.GeoDataFrame(
        {"row_id": data.index[valid_coordinates]},
        geometry=gpd.points_from_xy(
            data.loc[valid_coordinates, "Longitude"],
            data.loc[valid_coordinates, "Latitude"],
        ),
        crs="EPSG:4326",
    ).to_crs(unified.crs)

    joined = gpd.sjoin(points, unified, how="left", predicate="within")
    matched = joined.dropna(subset=["DistrictName"])

    district_count = matched.groupby("row_id")["DistrictName"].nunique()
    if (district_count > 1).any():
        raise ValueError("Some properties matched more than one Unified district.")

    assignments = matched.groupby("row_id")["DistrictName"].first()
    data["DistrictName"] = pd.Series(pd.NA, index=data.index, dtype="string")
    data.loc[assignments.index, "DistrictName"] = assignments.astype("string")

    return unified, valid_coordinates, len(assignments)


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Cleaned dataset not found: {INPUT_FILE}")
    if not DISTRICT_FILE.exists():
        raise FileNotFoundError(f"School district GeoJSON not found: {DISTRICT_FILE}")

    sold = pd.read_csv(INPUT_FILE, low_memory=False)
    rows_before = len(sold)
    require_columns(sold, DATE_COLUMNS + NUMERIC_COLUMNS + ["CountyOrParish"])

    add_market_metrics(sold)
    unified, valid_coordinates, matched_rows = add_school_districts(sold)

    if len(sold) != rows_before:
        raise ValueError("The spatial join changed the number of property rows.")

    engineered_columns = [
        "PriceRatio",
        "CloseToOriginalListRatio",
        "PricePerSqFt",
        "Year",
        "Month",
        "YrMo",
        "ListingToContractDays",
        "ContractToCloseDays",
        "DistrictName",
    ]
    sample_columns = [
        "ListingKey",
        "CountyOrParish",
        "CloseDate",
        "ClosePrice",
        "OriginalListPrice",
        "LivingArea",
        "DaysOnMarket",
        "PurchaseContractDate",
        "ListingContractDate",
        "Latitude",
        "Longitude",
    ] + engineered_columns
    sample = sold.dropna(subset=engineered_columns)[sample_columns].head(25)

    county_summary = (
        sold.groupby("CountyOrParish", dropna=False)
        .agg(
            sold_records=("ClosePrice", "size"),
            median_close_price=("ClosePrice", "median"),
            median_original_list_price=("OriginalListPrice", "median"),
            median_price_ratio=("PriceRatio", "median"),
            median_price_per_sq_ft=("PricePerSqFt", "median"),
            median_days_on_market=("DaysOnMarket", "median"),
            median_listing_to_contract_days=("ListingToContractDays", "median"),
            median_contract_to_close_days=("ContractToCloseDays", "median"),
            unified_districts_represented=("DistrictName", "nunique"),
            district_match_percent=(
                "DistrictName",
                lambda values: values.notna().mean() * 100,
            ),
        )
        .round(3)
        .reset_index()
        .sort_values("sold_records", ascending=False)
    )

    metric_summary = pd.DataFrame(
        {
            "metric": engineered_columns,
            "populated_rows": [int(sold[column].notna().sum()) for column in engineered_columns],
        }
    )
    metric_summary["populated_percent"] = (
        metric_summary["populated_rows"] / len(sold) * 100
    ).round(3)

    district_summary = pd.DataFrame(
        {
            "check": [
                "Total property rows",
                "Rows with usable California coordinates",
                "Rows excluded for unusable coordinates",
                "Rows matched to a Unified district",
                "Usable-coordinate rows without a district match",
                "Unified polygon records in source",
                "Unique Unified district names in source",
            ],
            "rows": [
                len(sold),
                int(valid_coordinates.sum()),
                int((~valid_coordinates).sum()),
                matched_rows,
                int(valid_coordinates.sum()) - matched_rows,
                len(unified),
                unified["DistrictName"].nunique(),
            ],
        }
    )

    sold.to_csv(OUTPUT_FILE, index=False)
    sample.to_csv(COMBINED_DIR / "week6_sample_output.csv", index=False)
    county_summary.to_csv(
        COMBINED_DIR / "week6_segment_summary_by_CountyOrParish.csv", index=False
    )
    metric_summary.to_csv(
        COMBINED_DIR / "week6_metric_quality_summary.csv", index=False
    )
    district_summary.to_csv(
        COMBINED_DIR / "week6_school_district_mapping_summary.csv", index=False
    )

    print(f"Rows before: {rows_before:,}")
    print(f"Rows after:  {len(sold):,}")
    print(f"Unified district matches: {matched_rows:,}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
