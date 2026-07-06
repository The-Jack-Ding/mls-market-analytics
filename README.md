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