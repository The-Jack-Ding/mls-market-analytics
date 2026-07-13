# IDX Exchange MLS Market Analytics

This project prepares CRMLS listing and sold transaction data for residential real estate market analysis.

## Project Structure

```text
IDX-Exchange/
├── csv/
│   ├── CRMLSListingYYYYMM.csv
│   ├── CRMLSSoldYYYYMM.csv
│   ├── CRMLSSoldYYYYMM_filled.csv
│   └── combined_outputs/
└── mls-market-analytics/
    ├── monthly_dataset_aggregation.py
    ├── validation.py
    └── README.md
```

## Scripts

### `monthly_dataset_aggregation.py`

Combines monthly MLS listing and sold CSV files from January 2024 through May 2026.

Main tasks:

- load monthly listing files
- load monthly sold files
- concatenate files into combined datasets
- filter to `PropertyType == "Residential"`
- save combined Residential datasets
- save row-count summary

Run:

```bash
python monthly_dataset_aggregation.py
```

### `validation.py`

Validates the sold dataset for Weeks 2–3.

Main tasks:

- document unique property types before filtering
- filter sold records to Residential
- create data type summary
- create null-count summary
- flag columns above 90% null
- summarize numeric distributions for:
  - `ClosePrice`
  - `LivingArea`
  - `DaysOnMarket`
- save the filtered Residential sold dataset

Run:

```bash
python validation.py
```

## Outputs

All output files are saved in:

```text
csv/combined_outputs/
```

Key outputs include:

```text
CRMLSListing_combined_202401_to_202605_Residential.csv
CRMLSSold_combined_202401_to_202605_Residential.csv
week1_aggregation_row_counts.csv
week2_3_unique_property_types.csv
week2_3_filtering_summary.csv
week2_3_dtype_summary.csv
week2_3_null_count_summary.csv
week2_3_columns_over_90_percent_null.csv
week2_3_numeric_distribution_summary.csv
CRMLSSold_residential_week2_3_filtered.csv
```

## Filtering Logic

Residential records are selected using:

```python
sold["PropertyType"].astype("string").str.strip().str.lower() == "residential"
```

This handles small formatting differences such as extra spaces or capitalization.

# IDX Exchange MLS Market Analysis — Week 3

`mortgage_rate_enrichment.py` completes the mortgage-rate enrichment portion of
the Weeks 2–3 deliverable. It:

- downloads the FRED `MORTGAGE30US` weekly series
- calculates the average 30-year fixed mortgage rate for each month
- merges rates into sold records using `CloseDate`
- merges rates into listing records using `ListingContractDate`
- stops without saving enriched datasets if any row has no matching rate

## Run with the existing project data

From this folder:

```bash
python mortgage_rate_enrichment.py --csv-dir /Users/jack/Desktop/IDX-Exchange/csv
```

The script reads the Week 1 combined Residential datasets and saves these files
in `csv/combined_outputs`:

```text
week3_monthly_mortgage_rates.csv
CRMLSSold_residential_with_mortgage_rates.csv
CRMLSListing_residential_with_mortgage_rates.csv
```

The two enriched datasets contain these added fields:

- `year_month`: monthly join key derived from the appropriate MLS date
- `rate_30yr_fixed`: monthly average national 30-year fixed mortgage rate

The internet connection must be active when the script runs because the latest
rate history is downloaded directly from FRED.
