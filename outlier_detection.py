from pathlib import Path

import pandas as pd


output_dir = Path(__file__).resolve().parent.parent / "csv" / "combined_outputs"
input_file = output_dir / "CRMLSSold_residential_week6_enriched.csv"
fields = ["ClosePrice", "LivingArea", "DaysOnMarket"]


def main():
    sold = pd.read_csv(input_file, low_memory=False)
    threshold_rows = []
    flags = []

    for field in fields:
        sold[field] = pd.to_numeric(sold[field], errors="coerce")

        q1 = sold[field].quantile(0.25)
        q3 = sold[field].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        flag = f"{field}_outlier_flag"
        sold[flag] = sold[field].notna() & ~sold[field].between(lower, upper)
        flags.append(flag)

        threshold_rows.append({
            "field": field,
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower,
            "upper_bound": upper,
            "outlier_rows": int(sold[flag].sum()),
        })

    sold["any_iqr_outlier_flag"] = sold[flags].any(axis=1)
    filtered = sold[~sold["any_iqr_outlier_flag"]]

    comparison_rows = [{
        "metric": "Dataset rows",
        "before_filtering": len(sold),
        "after_filtering": len(filtered),
    }]

    for field in fields:
        comparison_rows.append({
            "metric": f"Median {field}",
            "before_filtering": sold[field].median(),
            "after_filtering": filtered[field].median(),
        })

    pd.DataFrame(threshold_rows).to_csv(
        output_dir / "week7_iqr_thresholds.csv", index=False
    )
    pd.DataFrame(comparison_rows).to_csv(
        output_dir / "week7_before_after_comparison.csv", index=False
    )
    sold.to_csv(
        output_dir / "CRMLSSold_residential_week7_flagged.csv", index=False
    )
    filtered.to_csv(
        output_dir / "CRMLSSold_residential_week7_filtered.csv", index=False
    )

    print(f"Saved {len(sold):,} flagged rows and {len(filtered):,} filtered rows.")


if __name__ == "__main__":
    main()
