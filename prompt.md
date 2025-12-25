Nice. Here’s a one-shot set of “Codex instructions” updated to make the whole thing a lightweight web UI, but still file-based, portable, and started with one command.

Plan: single Python process runs FastAPI. The UI does mapping, rules selection, run execution, and browsing results. No separate frontend build step, just server-rendered pages plus tiny JS.

Below is the full spec you can paste into Codex.

---

## Codex instructions: Build a lightweight web UI CSV validation app in Python

### Goal

Build a lightweight local web app in Python for validating data quality using CSV files. It must run locally on Windows/Mac/Linux and start with one command. It must support:

* Upload CSVs or choose file paths
* Interactive mapping UI: pick keys, map columns, auto-guess mappings, skip fields, set normalization
* Save and load mappings as YAML
* Define validations using YAML rule files
* Run validations and produce artifacts under `runs/<run_id>/`
* Browse runs and view issues in the web UI
* Download issues and bad rows as CSV
* No database, everything stored as files on disk
* UI is very lightweight: server-side HTML templates, minimal JS for table filtering and mapping interactions

### One command to run

Primary run command:

```bash
python app.py
```

Defaults:

* host: 127.0.0.1
* port: 8787
* auto open browser

Also allow:

```bash
python app.py --host 0.0.0.0 --port 8787 --no-open
```

### Tech stack

* FastAPI + uvicorn
* Jinja2 templates for HTML
* Polars for CSV reads and processing
* PyYAML for rule and mapping YAML
* Rich for console logs only (optional)
* Minimal vanilla JS for client-side filtering and dynamic mapping rows
* No React, no node, no external CDN

### Project structure

Generate:

```
csv_validator_web/
  app.py
  pyproject.toml
  README.md
  rules/
    example_single.yaml
    example_compare.yaml
  mappings/
    README.md
  runs/
    .gitkeep
  src/
    core/
      io.py
      models.py
      normalize.py
      mapping_guess.py
      mapping_store.py
      rules_loader.py
      runner.py
      issue_writer.py
      html_report.py
      utils.py
    validators/
      required_columns.py
      required_non_null.py
      unique_key.py
      regex.py
      range.py
      allowed_values.py
      type_checks.py
      cross_file_match.py
      compare_fields.py
      row_rules.py
    web/
      server.py
      forms.py
      templates/
        base.html
        home.html
        new_run.html
        mapping.html
        run.html
        run_issues.html
        runs.html
      static/
        app.js
        app.css
```

### Data model for Issues

Create Issue model with these fields:

* run_id
* issue_id
* severity: INFO, WARN, ERROR
* issue_type
* message
* file_side: SINGLE, LEFT, RIGHT, BOTH
* row_index (nullable)
* record_key (nullable)
* column (nullable)
* left_value (nullable)
* right_value (nullable)
* suggested_fix (nullable)
* tags (nullable, list)

Write issues to `issues.csv` with columns:
`run_id,severity,issue_type,file_side,record_key,row_index,column,left_value,right_value,message,suggested_fix,tags`

### Run artifacts

Each run writes:

```
runs/<run_id>/
  inputs.json
  mapping_used.yaml (if compare mode)
  rules_used.yaml
  report.json
  summary.txt
  issues.csv
  bad_rows.csv (single mode)
  bad_rows_left.csv + bad_rows_right.csv (compare mode)
  report.html
  logs.txt
```

### UI pages

All pages server-rendered with Jinja2.

1. Home `/`

* Buttons: New Run, Runs, Mappings
* Show last 5 runs

2. New Run `/new`

* Choose mode: Single CSV or Compare two CSVs
* Upload file(s) OR provide local file paths
* Select rule file from `rules/` dropdown
* For compare mode:

  * option to load existing mapping from `mappings/`
  * or create new mapping

3. Mapping UI `/mapping/new` and `/mapping/edit/{mapping_name}`
   This is the key page. Must include:

* Left CSV and Right CSV selected (uploaded or file path)
* Dropdowns to pick Left Key and Right Key
* Mapping table with rows:

  * Left column dropdown
  * Right column dropdown
  * Skip checkbox
  * Normalization selector (multi-select) with sensible defaults
  * Optional value map editor (simple key-value table per field)
  * Confidence score and reason for auto-mapped suggestions

Buttons:

* Auto-guess mappings (re-run guesser)
* Clear mappings
* Save mapping (writes YAML under `mappings/<name>.yaml`)
* Save and Start Run (creates run immediately)
* Load mapping (select existing YAML and populate UI)

4. Runs list `/runs`

* list runs with timestamp, mode, total rows, errors, warnings
* click to open run detail

5. Run detail `/runs/{run_id}`

* show summary counts
* show issue type breakdown
* show first 500 issues in a table
* links to download issues.csv and bad_rows files
* link to open report.html

6. Issues page `/runs/{run_id}/issues`

* full issues table with client-side search box
* allow filtering by severity and issue_type using dropdowns
* do filtering in JS, not server-side

7. Mappings list `/mappings`

* list mapping files
* edit mapping
* delete mapping (soft delete: move to `mappings/_trash/`)

### CSV handling

Support two ways to provide CSVs:

* Upload through browser: store uploaded files inside `runs/<run_id>/uploads/` or a temp folder and reference the path
* Local file path: allow user to type a path. Validate it exists. Do not allow directory traversal outside allowed base if configured.

### Mapping YAML format

Use a “logical fields” mapping so rules are portable.

Example:

```yaml
meta:
  name: fis_to_salesforce_accounts
  created_at: "2025-12-25T02:20:00-05:00"

keys:
  left: Integration_Key__c
  right: Integration_Key__c

fields:
  primary_language:
    left: FinServ__PrimaryLanguage__pc
    right: CUST_LANG_PREF_CDE
    normalize: [trim, upper]
    value_map:
      "ENG": "EN"
  secondary_phone:
    left: Secondary_Phone__pc
    right: SCNDY_PH_NBR
    normalize: [normalize_phone_us]
    skip: false
```

Notes:

* Any field can set `skip: true`
* `normalize` is a list of steps
* `value_map` optional dict

### How mapping guessing works

Implement in `src/core/mapping_guess.py`.

Input:

* list of left columns
* list of right columns
* sample values for each column (read first N rows, default 2000)

Compute mapping suggestions with confidence:

1. name match score:

* exact after normalization of header names
* fuzzy match using rapidfuzz

2. data type score:

* detect email-like, phone-like, numeric-like, date-like

3. overlap score:

* normalized value overlap percentage between candidate pairs

Return top suggestion for each left column plus 2 alternates:

* best right column
* confidence 0 to 100
* reasons list like: ["header fuzzy 92", "type phone", "overlap 35%"]

Add dependency `rapidfuzz`.

### Rules file format

Rules are YAML and refer to logical field names from mapping in compare mode.

Compare rules example:

```yaml
mode: compare
name: Account compare rules

validators:
  - type: required_columns
    severity: ERROR
    columns:
      left: [Integration_Key__c]
      right: [Integration_Key__c]

  - type: unique_key
    severity: ERROR
    key:
      left: Integration_Key__c
      right: Integration_Key__c

  - type: compare_fields
    severity: WARN
    fields: ["primary_language", "secondary_phone"]
    ignore_if_both_blank: true
```

Single rules can refer to actual column names.

### Normalization steps

Implement in `src/core/normalize.py`:

* trim, lower, upper, collapse_whitespace, remove_punctuation, digits_only, null_if_blank
* normalize_email
* normalize_phone_us
* remove_suffixes (jr, sr, ii, iii)
  All must safely handle nulls.

### Validators

Implement pluggable validators. Each validator returns Issues and must be efficient with Polars.

Validators:

* required_columns
* required_non_null
* unique_key
* allowed_values
* regex
* type_checks
* range
* row_rules
* cross_file_match
* compare_fields (compare logical fields based on mapping)

compare_fields logic:

* For each logical field in mapping, get left and right columns
* Apply normalization pipeline for that field
* Apply value_map
* Compare
* Emit MISMATCH_FIELD issues with left_value and right_value
* Support ignore_if_both_blank
* Support numeric tolerance if configured on the field

### Runner

Implement in `src/core/runner.py`:

* Create run_id like `YYYY-MM-DD_HHMMSS_<random6>`
* Create run folder
* Save inputs.json, rules_used.yaml, mapping_used.yaml
* Load CSVs with Polars
* Execute validators
* Write issues.csv
* Write bad rows files
* Write report.json and report.html
* Return summary stats for web UI

### Web execution model

When the user clicks “Start Run”, the server should run validation in-process and then redirect to the run detail page.
Keep it simple and synchronous.
Add a max upload size setting and a note in README.

### Safety and robustness

* Validate user file paths and handle errors cleanly
* Never crash the server on bad CSV, show error page
* Limit issues displayed in UI to first 5000 but keep full in issues.csv
* Use clear messages and show where outputs are stored

### Static assets

* `app.css` basic clean layout, no heavy styling
* `app.js` for:

  * filtering issues table
  * adding/removing mapping rows
  * showing confidence reasons tooltips
    Keep JS small.

### README

Include:

* Install steps: `pip install -e .` or `pip install -r requirements`
* Run: `python app.py`
* How mappings work
* How rules work
* Where runs are stored
* Packaging for Windows exe using PyInstaller:

  * `pyinstaller --onefile app.py`
    Mention that the exe will be large because it bundles Python.

### Dependencies in pyproject.toml

* fastapi
* uvicorn
* jinja2
* polars
* pyyaml
* rapidfuzz
* python-multipart (for file upload)
* orjson (optional)

### Deliverables

Generate all code files.
Ensure:

* Server starts with `python app.py`
* User can upload two small CSVs, map columns, save mapping, run compare, and see issues in UI
* User can browse runs and download artifacts

End.

---

If you want an extra nice touch: add a “Download mapping YAML” button and a “Copy mapping YAML to clipboard” button. That makes it easy to share mappings across environments.
