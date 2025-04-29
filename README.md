# real-time-sent-airflow

## How to Run the System

### 1. Activate the Environment
```bash
conda activate seanchoi
```

### 2. Set Up Dependencies  
If the system hasn't been set up yet, choose one of the following methods to install dependencies.  
> **Recommended**: Option 2 (Docker image)

**Option 1: Install Locally**
```bash
pip download --dest /data/seanchoi/airflow/airflow_docker/deps -r /data/seanchoi/airflow/airflow_docker/requirements.txt --use-deprecated=legacy-resolver
```

**Option 2: Load Prebuilt Docker Image**
```bash
docker load -i /data/seanchoi/airflow/airflow_docker/seanchoi_image.tar
```

> _Note for Hao_: You can skip this step if you're testing the system on the server — the setup and image are already in place.

### 3. Launch the System
Navigate to the project directory and start the services:
```bash
cd /data/seanchoi/airflow
docker compose up
```
(Optional) If an image is not built, build an image first:
```bash
docker compose build
```

(Optional) If the system is already running, stop it first:
```bash
docker compose down
```

### 4. Access the Airflow UI
Open in browser:
```
http://20.77.80.201:3000/home
```
Login credentials:
- **Username**: `admin`
- **Password**: `admin`

---

## Data Directory Structure

Root path:  
```
/data/seanchoi/airflow/data/SP500/
```

```
├── AnalysisReports/
├── constituents/
│   ├── firms/
│   └── market/
├── logs/
├── NASDAQ100/
└── SP500/
    ├── calls/
    │   ├── firm/
    │   └── market/
    ├── reports/
    │   ├── firm/
    │   └── market/
    ├── sec/
        ├── firm/
        └── market/
```

---

## Folder: `firm/`
Contains data for **individual S&P 500 companies**.

### Subfolders:
- `company_df/` — Firm-specific data by CIK (e.g., `0001045810/`)
- `dtm/` — Document-Term Matrices
  - `_SUCCESS`: Spark job completion marker  
  - `.parquet` files: DTM data
- `filtered/` — Preprocessed datasets (e.g., `batch_filtered_0.parquet`) which remains only active SP500 firm per year. The output of SP500 Dynamism filter (Please check the Financial Text Retrieval Model at the thesis)
- `html/` — SEC filings in HTML format
- `intermediate/` — Temporary processing outputs
- `outcome/` — Final metrics
  - `mod_sent_ret.csv`: Sentiment-based returns
  - `mod_sent_vol.csv`: Sentiment-based volatility
- `processed/` — Clean datasets ready for modeling
- `txt/` — Plain text SEC filings
- `json/` — Transcripts and Reports in JSON format

---

## Folder: `market/`
Contains **aggregated data across the S&P 500**.

Structure mirrors the `firm/` folder:
- `company_df/`: Aggregated data by CIK
- `dtm/`, `filtered/`, `html/`, `intermediate/`, `outcome/`, `processed/`, `txt/`, `json/`: Same function as in `firm/`

---

##  How to Use or Modify the Data

### Adding New Data
Place raw files into:
- `html/` for HTML filings
- `txt/` for plain text

### Processing Data
- Store intermediate results in `intermediate/`, `filtered/`
- Save final metrics in `outcome/`

### Analyzing Results
Use:
- `outcome/mod_sent_ret.csv` and  
- `outcome/mod_sent_vol.csv`  
for analysis and plotting.

### Debugging
Check `filtered/` and `intermediate/` to verify preprocessing steps and troubleshoot issues.


## Core Code at Plugins Directory Structure

The plugins directory contains custom modules, scripts, and utilities that extend the functionality of the real-time system. It is organized into main subfolders:

```
/data/seanchoi/airflow/plugins
├── __init__.py
├── common/
├── packages/
└── shell/
```

### 1. Folder: `common/`
Contains shared utility functions and scripts used across the system.

#### Key Files:
- `__init__.py`: Initializes the module
- `common_func.py`: General utilities (e.g., file importers, SFTP handlers)
- `sec10k_item1a_extractor.py`: Extracts "Item 1A: Risk Factors" from SEC filings (text + HTML)
- `time_log_decorator.py`: Decorator to log function execution times

#### Key Functions:
- `process_files_for_cik`: Processes filings for a specific CIK
- `process_files_for_cik_with_italic`: Handles italicized SEC content
- `save_error_info`: Logs errors during processing

#### Use Cases:
- Use `common_func.py` for file operations
- Use `sec10k_item1a_extractor.py` for SEC section extraction and preprocessing

### 2. Folder: `packages/`
Specialized modules organized by functionality

#### Subfolders:
- **FTRM/** (Financial Text Retrieval Model)
  - `sec_crawler.py`: Crawls SEC filings
  - `extract_report_ids.py`: Retrieves report IDs
  - `annual_report_reader.py`: Preprocesses annual reports
  - **Use case**: Retrieving and preparing financial documents

- **PDCM/** (Processing and Document Construction Module)
  - `constructDTM.py`: Builds Document-Term Matrices
  - `vol_reader_fun.py`: Processes volatility and returns
  - **Use case**: Preprocessing and feature construction

- **SSPM/** (Sentiment and Signal Processing Module)
  - `model.py`: Trains sentiment models; Kalman filters
  - `sent_predictor_firm.py`: Predicts sentiment at firm-level
  - `sent_predictor_market_deprecated.py`: (Deprecated) Market-level sentiment. Check the local version which is used in the system (sec_sent_predictor_local.py at /data/seanchoi/SSPM_local)
    
  - **Use case**: Sentiment modeling and signal generation

