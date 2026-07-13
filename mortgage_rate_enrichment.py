from argparse import ArgumentParser
from pathlib import Path

import pandas as pd


FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
LISTING_FILE = "CRMLSListing_combined_202401_to_202605_Residential.csv"
SOLD_FILE = "CRMLSSold_combined_202401_to_202605_Residential.csv"


def get_monthly_rates():
    """Download weekly 30-year mortgage rates and calculate monthly averages."""
    rates = pd.read_csv(FRED_URL)
    rates.columns = ["date", "rate_30yr_fixed"]
    rates["date"] = pd.to_datetime(rates["date"], errors="coerce")
    rates["rate_30yr_fixed"] = pd.to_numeric(
        rates["rate_30yr_fixed"], errors="coerce"
    )
    rates = rates.dropna(subset=["date", "rate_30yr_fixed"])
    rates["year_month"] = rates["date"].dt.to_period("M")

    return (
        rates.groupby("year_month", as_index=False)["rate_30yr_fixed"]
        .mean()
        .round({"rate_30yr_fixed": 3})
    )


def add_rates(input_path, date_column, monthly_rates, output_path):
    """Merge monthly mortgage rates into one MLS dataset and save the result."""
    data = pd.read_csv(input_path, low_memory=False)
    data[date_column] = pd.to_datetime(data[date_column], errors="coerce")
    data["year_month"] = data[date_column].dt.to_period("M")
    enriched = data.merge(monthly_rates, on="year_month", how="left")

    missing_dates = enriched[date_column].isna().sum()
    missing_rates = enriched["rate_30yr_fixed"].isna().sum()

    print(f"\n{input_path.name}")
    print(f"Rows: {len(enriched):,}")
    print(f"Missing or invalid {date_column} values: {missing_dates:,}")
    print(f"Rows without a matching mortgage rate: {missing_rates:,}")

    if missing_rates:
        missing_months = (
            enriched.loc[enriched["rate_30yr_fixed"].isna(), "year_month"]
            .value_counts(dropna=False)
            .sort_index()
        )
        print("Unmatched months:")
        print(missing_months.to_string())
        raise ValueError("Mortgage-rate merge has unmatched rows; output was not saved.")

    enriched.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")


def main():
    parser = ArgumentParser(description="Add monthly FRED mortgage rates to MLS data.")
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "csv",
        help="Folder containing the combined_outputs directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional output folder; defaults to csv/combined_outputs",
    )
    args = parser.parse_args()

    combined_dir = args.csv_dir / "combined_outputs"
    output_dir = args.output_dir or combined_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    listing_path = combined_dir / LISTING_FILE
    sold_path = combined_dir / SOLD_FILE
    for path in (listing_path, sold_path):
        if not path.exists():
            raise FileNotFoundError(f"Combined dataset not found: {path}")

    monthly_rates = get_monthly_rates()
    monthly_rates.to_csv(output_dir / "week3_monthly_mortgage_rates.csv", index=False)

    add_rates(
        sold_path,
        "CloseDate",
        monthly_rates,
        output_dir / "CRMLSSold_residential_with_mortgage_rates.csv",
    )
    add_rates(
        listing_path,
        "ListingContractDate",
        monthly_rates,
        output_dir / "CRMLSListing_residential_with_mortgage_rates.csv",
    )

    print("\nValidation passed: every row has a mortgage rate.")


if __name__ == "__main__":
    main()
