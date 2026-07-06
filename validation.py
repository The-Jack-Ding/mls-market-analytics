from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

csv_dirs = [Path(__file__).resolve().parent.parent / "csv"]
CSV_DIR = next((p for p in csv_dirs if p.exists()), None)
OUTPUT_DIR = CSV_DIR / "combined_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

MONTHS_TO_PULL = [
    "202401", "202402", "202403", "202404", "202405", "202406",
    "202407", "202408", "202409", "202410", "202411", "202412",
    "202501", "202502", "202503", "202504", "202505", "202506",
    "202507", "202508", "202509", "202510", "202511", "202512",
    "202601", "202602", "202603", "202604", "202605",
]


def read_sold_file(month):
    normal_file = CSV_DIR / f"CRMLSSold{month}.csv"
    filled_file = CSV_DIR / f"CRMLSSold{month}_filled.csv"

    if normal_file.exists():
        print(f"Reading: {normal_file.name}")
        return pd.read_csv(normal_file, low_memory=False)

    if filled_file.exists():
        print(f"Reading: {filled_file.name}")
        df = pd.read_csv(filled_file, low_memory=False)
        df = df.iloc[:, :-2]
        return df

    print(f"Missing sold file for month: {month}")
    return None


monthly_dfs = []

for month in MONTHS_TO_PULL:
    df = read_sold_file(month)

    if df is not None:
        monthly_dfs.append(df)

if not monthly_dfs:
    raise FileNotFoundError("No monthly CRMLSSold files were found.")

sold = pd.concat(monthly_dfs, ignore_index=True)

input_file = "Raw monthly CRMLSSold files, concatenated before Residential filter"

print(f"Loaded raw sold dataset from monthly files.")
print(f"Monthly files loaded: {len(monthly_dfs)}")
print("\n--- Filtering Summary ---")
print("Filter applied: PropertyType cleaned with strip().lower() == 'residential'")



# Basic structure summary
original_rows, original_cols = sold.shape
print("\n--- Dataset Structure ---")
print(f"Input source: {input_file}")
print(f"Rows before filtering: {original_rows:,}")
print(f"Columns before filtering: {original_cols:,}")

dtype_summary = sold.dtypes.reset_index().rename(columns={"index": "column", 0: "dtype"})
dtype_summary_path = OUTPUT_DIR / "week2_3_dtype_summary.csv"
dtype_summary.to_csv(dtype_summary_path, index=False)

# Unique property types
property_type_counts = sold["PropertyType"].fillna("(missing)").astype(str).str.strip().replace("", "(blank)").value_counts(dropna=False).reset_index()
property_type_counts.columns = ["PropertyType", "row_count"]
property_type_counts["row_percent"] = (property_type_counts["row_count"] / len(sold) * 100).round(2)

property_type_path = OUTPUT_DIR / "week2_3_unique_property_types.csv"
property_type_counts.to_csv(property_type_path, index=False)

print("\n--- Unique Property Types Found ---")
print(property_type_counts)


# Filtering 
property_type_clean = sold["PropertyType"].astype("string").str.strip().str.lower()
sold_residential = sold[property_type_clean == "residential"].copy()
filtered_rows, filtered_cols = sold_residential.shape

print("\n--- Filtering Summary ---")
print("Filter applied: PropertyType cleaned with strip().lower() == 'residential'")
print(f"Rows before Residential filter: {original_rows:,}")
print(f"Rows after Residential filter: {filtered_rows:,}")
print(f"Rows removed: {original_rows - filtered_rows:,}")
print(f"Columns after filtering: {filtered_cols:,}")

filtering_summary = pd.DataFrame([{
    "filter_applied": "PropertyType cleaned with strip().lower() == 'residential'",
    "rows_before_filter": original_rows,
    "rows_after_filter": filtered_rows,
    "rows_removed": original_rows - filtered_rows,
    "columns_before_filter": original_cols,
    "columns_after_filter": filtered_cols
}])

filtering_summary_path = OUTPUT_DIR / "week2_3_filtering_summary.csv"
filtering_summary.to_csv(filtering_summary_path, index=False)


# Null-count summary table
def build_null_summary(df: pd.DataFrame) -> pd.DataFrame:
    null_counts = df.isna().sum()
    null_percents = (null_counts / len(df) * 100).round(2)

    summary = pd.DataFrame({
        "column": df.columns,
        "dtype": df.dtypes.astype(str).values,
        "null_count": null_counts.values,
        "null_percent": null_percents.values,
        "non_null_count": (len(df) - null_counts).values
    })

    summary = summary.sort_values(by=["null_percent", "null_count"],ascending=False).reset_index(drop=True)
    return summary

null_summary = build_null_summary(sold_residential)
null_summary_path = OUTPUT_DIR / "week2_3_null_count_summary.csv"
null_summary.to_csv(null_summary_path, index=False)

print("\n--- Null Count Summary: Top 20 Highest Missing Columns ---")
print(null_summary.head(20))


# Missing value report: >90% null
null_report = null_summary[null_summary["null_percent"] > 90].copy()
null_path = OUTPUT_DIR / "week2_3_columns_over_90_percent_null.csv"
null_report.to_csv(null_path, index=False)

print("\n--- Columns Above 90% Null ---")
if null_report.empty:
    print("No columns are above 90% null.")
else:
    print(null_report)


# Numeric distribution summary
numeric_fields = ["ClosePrice", "LivingArea", "DaysOnMarket"]

def clean_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    cleaned = (
        series.astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"": np.nan, "nan": np.nan, "None": np.nan})
    )

    return pd.to_numeric(cleaned, errors="coerce")


distribution_rows = []

for col in numeric_fields:
    if col not in sold_residential.columns:
        distribution_rows.append({
            "field": col,
            "status": "COLUMN NOT FOUND",
            "count": np.nan,
            "missing_count": np.nan,
            "min": np.nan,
            "p01": np.nan,
            "p05": np.nan,
            "p10": np.nan,
            "p25": np.nan,
            "median_p50": np.nan,
            "mean": np.nan,
            "p75": np.nan,
            "p90": np.nan,
            "p95": np.nan,
            "p99": np.nan,
            "max": np.nan,
        })
        continue

    numeric_series = clean_numeric(sold_residential[col])
    sold_residential[col] = numeric_series

    non_null = numeric_series.dropna()

    if non_null.empty:
        distribution_rows.append({
            "field": col,
            "status": "NO NUMERIC VALUES",
            "count": 0,
            "missing_count": numeric_series.isna().sum(),
            "min": np.nan,
            "p01": np.nan,
            "p05": np.nan,
            "p10": np.nan,
            "p25": np.nan,
            "median_p50": np.nan,
            "mean": np.nan,
            "p75": np.nan,
            "p90": np.nan,
            "p95": np.nan,
            "p99": np.nan,
            "max": np.nan,
        })
        continue

    distribution_rows.append({
        "field": col,
        "status": "OK",
        "count": int(non_null.count()),
        "missing_count": int(numeric_series.isna().sum()),
        "min": non_null.min(),
        "p01": non_null.quantile(0.01),
        "p05": non_null.quantile(0.05),
        "p10": non_null.quantile(0.10),
        "p25": non_null.quantile(0.25),
        "median_p50": non_null.median(),
        "mean": non_null.mean(),
        "p75": non_null.quantile(0.75),
        "p90": non_null.quantile(0.90),
        "p95": non_null.quantile(0.95),
        "p99": non_null.quantile(0.99),
        "max": non_null.max(),
    })


numeric_distribution = pd.DataFrame(distribution_rows)

# Round numeric columns for readability
for col in numeric_distribution.columns:
    if col not in ["field", "status"]:
        numeric_distribution[col] = pd.to_numeric(
            numeric_distribution[col], errors="coerce"
        ).round(2)

numeric_distribution_path = OUTPUT_DIR / "week2_3_numeric_distribution_summary.csv"
numeric_distribution.to_csv(numeric_distribution_path, index=False)

print("\n--- Numeric Distribution Summary ---")
print(numeric_distribution)


# Save
filtered_dataset_path = OUTPUT_DIR / "CRMLSSold_residential_week2_3_filtered.csv"
sold_residential.to_csv(filtered_dataset_path, index=False)

print("\n--- Filtered Dataset Saved ---")
print(f"Saved to: {filtered_dataset_path}")