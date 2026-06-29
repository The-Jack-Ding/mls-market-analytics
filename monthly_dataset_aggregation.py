from pathlib import Path
import pandas as pd

CSV_DIR = Path("../csv")
OUTPUT_DIR = CSV_DIR / "combined_outputs"

MONTHS_TO_PULL = [
    "202401", "202402", "202403", "202404", "202405", "202406",
    "202407", "202408", "202409", "202410", "202411", "202412",
    "202501", "202502", "202503", "202504", "202505", "202506",
    "202507", "202508", "202509", "202510", "202511", "202512",
    "202601", "202602", "202603", "202604", "202605",
]

def read_listing_file(month):
    file_path = CSV_DIR / f"CRMLSListing{month}.csv"

    if not file_path.exists():
        print(f"Missing listing file: {file_path}")
        return None

    df = pd.read_csv(file_path, low_memory=False)
    return df


def read_sold_file(month):
    normal_file = CSV_DIR / f"CRMLSSold{month}.csv"
    filled_file = CSV_DIR / f"CRMLSSold{month}_filled.csv"

    if normal_file.exists():
        df = pd.read_csv(normal_file, low_memory=False)
        return df

    if filled_file.exists():
        df = pd.read_csv(filled_file, low_memory=False)
        df = df.iloc[:, :-2]
        return df

    print(f"Missing sold file: {normal_file} or {filled_file}")
    return None


def filter_residential(df):
    return df[df["PropertyType"] == "Residential"].copy()


def combine_files(file_type):
    monthly_dfs = []
    count_rows = []

    for month in MONTHS_TO_PULL:
        if file_type == "listing":
            df = read_listing_file(month)
        else:
            df = read_sold_file(month)

        if df is None:
            continue

        rows_before_filter = len(df)
        monthly_dfs.append(df)

        count_rows.append({
            "dataset": file_type,
            "month": month,
            "rows_before_filter": rows_before_filter,
        })

        print(f"Loaded {file_type} {month}: {rows_before_filter:,} rows")

    combined = pd.concat(monthly_dfs, ignore_index=True)

    rows_after_concat = len(combined)

    residential = filter_residential(combined)

    rows_after_residential_filter = len(residential)

    print()
    print(f"{file_type.upper()} summary:")
    print(f"Rows after concat: {rows_after_concat:,}")
    print(f"Rows after Residential filter: {rows_after_residential_filter:,}")
    print()

    summary = pd.DataFrame(count_rows)
    summary["rows_after_concat_total"] = rows_after_concat
    summary["rows_after_residential_filter_total"] = rows_after_residential_filter

    return residential, summary



def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start_month = MONTHS_TO_PULL[0]
    end_month = MONTHS_TO_PULL[-1]

    listing_residential, listing_counts = combine_files("listing")
    sold_residential, sold_counts = combine_files("sold")

    listing_output = OUTPUT_DIR / f"CRMLSListing_combined_{start_month}_to_{end_month}_Residential.csv"
    sold_output = OUTPUT_DIR / f"CRMLSSold_combined_{start_month}_to_{end_month}_Residential.csv"
    counts_output = OUTPUT_DIR / "week1_aggregation_row_counts.csv"

    listing_residential.to_csv(listing_output, index=False)
    sold_residential.to_csv(sold_output, index=False)

    all_counts = pd.concat([listing_counts, sold_counts], ignore_index=True)
    all_counts.to_csv(counts_output, index=False)

    print("Saved files:")
    print(listing_output)
    print(sold_output)
    print(counts_output)


if __name__ == "__main__":
    main()
