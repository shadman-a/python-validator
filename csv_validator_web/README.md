# CSV Validator Web

A lightweight, file-based CSV validation web UI. Runs locally with a single command and stores all artifacts on disk.

## Install

```bash
pip install -e .
```

Or install requirements directly:

```bash
pip install fastapi uvicorn jinja2 polars pyyaml rapidfuzz python-multipart orjson
```

## Run

```bash
python app.py
```

Options:

```bash
python app.py --host 0.0.0.0 --port 8787 --no-open
```

## Mappings

Mappings live under `mappings/` as YAML and map logical field names to left/right columns. In compare mode, rules reference these logical field names.

## Rules

Rules are YAML under `rules/` and define validators to run. Single-mode rules can reference raw column names. Compare rules refer to logical field names.

## Runs

Runs and their artifacts are stored under `runs/<run_id>/`.

## Packaging

To build a Windows executable using PyInstaller:

```bash
pyinstaller --onefile app.py
```

Note: the resulting executable is large because it bundles Python.

## Limits

Uploads are limited by `MAX_UPLOAD_MB` in `app.py`.
