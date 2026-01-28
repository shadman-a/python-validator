from __future__ import annotations

import json
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml

from ..core.io import read_csv, read_csv_columns, sample_values
from ..core.mapping_guess import guess_mappings
from ..core.mapping_store import load_mapping, save_mapping
from ..core.rules_loader import load_rules
from ..core.runner import run_validation
from ..core.utils import ensure_dir, format_timestamp, human_bool, is_subpath, sanitize_filename

BASE_DIR = Path(__file__).resolve().parents[2]
RULES_DIR = BASE_DIR / "rules"
MAPPINGS_DIR = BASE_DIR / "mappings"
RUNS_DIR = BASE_DIR / "runs"
UPLOADS_DIR = RUNS_DIR / "_uploads"


def create_app() -> FastAPI:
    app = FastAPI()
    templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "web" / "templates"))

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "src" / "web" / "static")), name="static")

    def _list_rules() -> list[str]:
        return sorted([p.name for p in RULES_DIR.glob("*.yaml")])

    def _list_mappings() -> list[str]:
        return sorted([p.name for p in MAPPINGS_DIR.glob("*.yaml")])

    def _mapping_summaries() -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for path in sorted(MAPPINGS_DIR.glob("*.yaml")):
            data = load_mapping(path)
            if not isinstance(data, dict):
                continue
            fields = data.get("fields") or {}
            if not isinstance(fields, dict):
                fields = {}
            left_columns = []
            right_columns = []
            for config in fields.values():
                if not isinstance(config, dict):
                    continue
                left = config.get("left")
                right = config.get("right")
                if left:
                    left_columns.append(left)
                if right:
                    right_columns.append(right)
            keys = data.get("keys") if isinstance(data.get("keys"), dict) else {}
            summaries.append(
                {
                    "name": path.name,
                    "left_columns": left_columns,
                    "right_columns": right_columns,
                    "left_key": (keys or {}).get("left", ""),
                    "right_key": (keys or {}).get("right", ""),
                    "field_count": len(fields),
                }
            )
        return summaries

    def _list_runs() -> list[dict[str, Any]]:
        runs = []
        for run_dir in sorted(RUNS_DIR.glob("*")):
            if not run_dir.is_dir() or run_dir.name.startswith("_"):
                continue
            report_path = run_dir / "report.json"
            if report_path.exists():
                report = json.loads(report_path.read_text())
                runs.append({
                    "run_id": run_dir.name,
                    "mode": report.get("mode"),
                    "errors": report.get("errors", 0),
                    "warnings": report.get("warnings", 0),
                    "rows_left": report.get("rows_left", 0),
                    "rows_right": report.get("rows_right", 0),
                })
        return sorted(runs, key=lambda item: item["run_id"], reverse=True)

    def _save_upload(upload: UploadFile) -> Path:
        ensure_dir(UPLOADS_DIR)
        filename = sanitize_filename(upload.filename or "upload.csv")
        path = UPLOADS_DIR / f"{datetime.now().timestamp()}_{filename}"
        with path.open("wb") as handle:
            handle.write(upload.file.read())
        return path

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        runs = _list_runs()[:5]
        return templates.TemplateResponse("home.html", {"request": request, "runs": runs})

    @app.get("/new", response_class=HTMLResponse)
    async def new_run(request: Request):
        return templates.TemplateResponse(
            "new_run.html",
            {
                "request": request,
                "rules": _list_rules(),
                "mappings": _list_mappings(),
                "mapping_summaries": _mapping_summaries(),
            },
        )

    @app.post("/new", response_class=HTMLResponse)
    async def new_run_submit(
        request: Request,
        mode: str = Form(...),
        rule_file: str = Form(...),
        left_path: str | None = Form(None),
        right_path: str | None = Form(None),
        mapping_choice: str | None = Form(None),
        mapping_file: str | None = Form(None),
        left_upload: UploadFile | None = File(None),
        right_upload: UploadFile | None = File(None),
    ):
        left = Path(left_path) if left_path else None
        right = Path(right_path) if right_path else None
        if left_upload and left_upload.filename:
            left = _save_upload(left_upload)
        if right_upload and right_upload.filename:
            right = _save_upload(right_upload)

        if not left or not left.exists():
            return templates.TemplateResponse(
                "new_run.html",
                {
                    "request": request,
                    "rules": _list_rules(),
                    "mappings": _list_mappings(),
                    "mapping_summaries": _mapping_summaries(),
                    "error": "Left CSV path is required and must exist.",
                },
            )
        if mode == "compare" and (not right or not right.exists()):
            return templates.TemplateResponse(
                "new_run.html",
                {
                    "request": request,
                    "rules": _list_rules(),
                    "mappings": _list_mappings(),
                    "mapping_summaries": _mapping_summaries(),
                    "error": "Right CSV path is required for compare mode.",
                },
            )

        rules = load_rules(RULES_DIR / rule_file)

        if mode == "compare" and mapping_choice == "existing" and mapping_file:
            mapping = load_mapping(MAPPINGS_DIR / mapping_file)
            result = run_validation(mode, left, right, rules, mapping, RUNS_DIR)
            return RedirectResponse(url=f"/runs/{result.run_id}", status_code=302)

        if mode == "compare" and mapping_choice == "create":
            return await mapping_new(request, left, right, rule_file)

        result = run_validation(mode, left, right, rules, None, RUNS_DIR)
        return RedirectResponse(url=f"/runs/{result.run_id}", status_code=302)

    @app.get("/mapping/new", response_class=HTMLResponse)
    async def mapping_new_get(request: Request, left_path: str, right_path: str, rule_file: str | None = None):
        return await mapping_new(request, Path(left_path), Path(right_path), rule_file)

    async def mapping_new(request: Request, left: Path, right: Path, rule_file: str | None):
        left_df = read_csv(left)
        right_df = read_csv(right)
        left_samples = sample_values(left_df)
        right_samples = sample_values(right_df)
        suggestions = guess_mappings(left_df.columns, right_df.columns, left_samples, right_samples)
        return templates.TemplateResponse(
            "mapping.html",
            {
                "request": request,
                "left_path": str(left),
                "right_path": str(right),
                "left_columns": left_df.columns,
                "right_columns": right_df.columns,
                "suggestions": suggestions,
                "mapping": None,
                "mapping_name": "",
                "rule_file": rule_file,
            },
        )

    @app.get("/mapping/edit/{mapping_name}", response_class=HTMLResponse)
    async def mapping_edit(request: Request, mapping_name: str):
        mapping = load_mapping(MAPPINGS_DIR / mapping_name)
        return templates.TemplateResponse(
            "mapping.html",
            {
                "request": request,
                "left_path": "",
                "right_path": "",
                "left_columns": [],
                "right_columns": [],
                "suggestions": [],
                "mapping": mapping,
                "mapping_name": mapping_name.replace(".yaml", ""),
                "rule_file": None,
                "mapping_yaml": yaml.safe_dump(mapping, sort_keys=False),
            },
        )

    @app.post("/mapping/save", response_class=HTMLResponse)
    async def mapping_save(
        request: Request,
        mapping_name: str = Form(...),
        left_path: str | None = Form(None),
        right_path: str | None = Form(None),
        left_key: str = Form(...),
        right_key: str = Form(...),
        action: str = Form("save"),
        rule_file: str | None = Form(None),
        field_name: list[str] = Form(...),
        left_column: list[str] = Form(...),
        right_column: list[str] = Form(...),
        skip: list[str] = Form([]),
        normalize: list[str] = Form([]),
        value_map: list[str] = Form([]),
    ):
        fields: dict[str, Any] = {}
        for idx, name in enumerate(field_name):
            if not name:
                continue
            value_map_data = None
            if idx < len(value_map) and value_map[idx].strip():
                try:
                    value_map_data = json.loads(value_map[idx])
                except json.JSONDecodeError:
                    value_map_data = None
            norm_steps = []
            if idx < len(normalize) and normalize[idx].strip():
                norm_steps = [step.strip() for step in normalize[idx].split(",") if step.strip()]
            fields[name] = {
                "left": left_column[idx] if idx < len(left_column) else "",
                "right": right_column[idx] if idx < len(right_column) else "",
                "skip": str(idx) in skip,
                "normalize": norm_steps,
            }
            if value_map_data:
                fields[name]["value_map"] = value_map_data

        mapping_payload = {
            "meta": {"name": mapping_name, "created_at": datetime.now().isoformat()},
            "keys": {"left": left_key, "right": right_key},
            "fields": fields,
        }
        mapping_path = save_mapping(MAPPINGS_DIR, mapping_name, mapping_payload)

        if action == "save_and_run" and left_path and right_path and rule_file:
            rules = load_rules(RULES_DIR / rule_file)
            result = run_validation("compare", Path(left_path), Path(right_path), rules, mapping_payload, RUNS_DIR)
            return RedirectResponse(url=f"/runs/{result.run_id}", status_code=302)

        return RedirectResponse(url=f"/mapping/edit/{mapping_path.name}", status_code=302)

    @app.get("/mapping/guess")
    async def mapping_guess_endpoint(left_path: str, right_path: str):
        left_df = read_csv(Path(left_path))
        right_df = read_csv(Path(right_path))
        suggestions = guess_mappings(
            left_df.columns,
            right_df.columns,
            sample_values(left_df),
            sample_values(right_df),
        )
        payload = [
            {
                "left_column": item.left_column,
                "best_right": item.best_right,
                "confidence": item.confidence,
                "reasons": item.reasons,
            }
            for item in suggestions
        ]
        return payload

    @app.get("/files/columns")
    async def files_columns(left_path: str | None = None, right_path: str | None = None):
        payload: dict[str, Any] = {"left_columns": [], "right_columns": []}
        if left_path:
            left = Path(left_path)
            if not left.exists():
                return Response("Left path not found", status_code=404)
            try:
                payload["left_columns"] = read_csv_columns(left)
            except Exception:
                return Response("Unable to read left CSV", status_code=400)
        if right_path:
            right = Path(right_path)
            if not right.exists():
                return Response("Right path not found", status_code=404)
            try:
                payload["right_columns"] = read_csv_columns(right)
            except Exception:
                return Response("Unable to read right CSV", status_code=400)
        return payload

    @app.get("/runs", response_class=HTMLResponse)
    async def runs(request: Request):
        return templates.TemplateResponse("runs.html", {"request": request, "runs": _list_runs()})

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    async def run_detail(request: Request, run_id: str):
        run_dir = RUNS_DIR / run_id
        report = json.loads((run_dir / "report.json").read_text())
        issues = []
        issues_path = run_dir / "issues.csv"
        if issues_path.exists():
            lines = issues_path.read_text().splitlines()[1:501]
            for line in lines:
                issues.append(line.split(","))
        return templates.TemplateResponse(
            "run.html",
            {
                "request": request,
                "run_id": run_id,
                "report": report,
                "issues": issues,
            },
        )

    @app.get("/runs/{run_id}/issues", response_class=HTMLResponse)
    async def run_issues(request: Request, run_id: str):
        run_dir = RUNS_DIR / run_id
        issues = []
        issues_path = run_dir / "issues.csv"
        if issues_path.exists():
            lines = issues_path.read_text().splitlines()[1:5001]
            for line in lines:
                issues.append(line.split(","))
        return templates.TemplateResponse(
            "run_issues.html",
            {"request": request, "run_id": run_id, "issues": issues},
        )

    @app.get("/download/{run_id}/{filename}")
    async def download_file(run_id: str, filename: str):
        run_dir = RUNS_DIR / run_id
        file_path = run_dir / filename
        if not file_path.exists():
            return Response("Not found", status_code=404)
        if not is_subpath(file_path, run_dir):
            return Response("Invalid path", status_code=400)
        return Response(file_path.read_bytes(), media_type="application/octet-stream")

    @app.get("/mappings", response_class=HTMLResponse)
    async def mappings(request: Request):
        mappings = _list_mappings()
        return templates.TemplateResponse("mappings.html", {"request": request, "mappings": mappings})

    @app.get("/mappings/download/{mapping_name}")
    async def mapping_download(mapping_name: str):
        mapping_path = MAPPINGS_DIR / mapping_name
        if not mapping_path.exists():
            return Response("Not found", status_code=404)
        return Response(mapping_path.read_bytes(), media_type="text/yaml")

    @app.post("/mappings/delete/{mapping_name}")
    async def mapping_delete(mapping_name: str):
        mapping_path = MAPPINGS_DIR / mapping_name
        trash_dir = ensure_dir(MAPPINGS_DIR / "_trash")
        if mapping_path.exists():
            mapping_path.rename(trash_dir / mapping_path.name)
        return RedirectResponse(url="/mappings", status_code=302)

    return app


def run(host: str, port: int, open_browser: bool = True) -> None:
    app = create_app()
    if open_browser:
        webbrowser.open(f"http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
        if mode == "compare" and mapping_choice == "existing" and not mapping_file:
            return templates.TemplateResponse(
                "new_run.html",
                {
                    "request": request,
                    "rules": _list_rules(),
                    "mappings": _list_mappings(),
                    "mapping_summaries": _mapping_summaries(),
                    "error": "Select a mapping file or choose to create a new mapping.",
                },
            )
