@echo off
setlocal
cd /d "%~dp0"

rem Use the Python launcher if available; otherwise fall back to python on PATH.
if exist "%SystemRoot%\py.exe" (
  py -3 app.py
) else (
  python app.py
)

endlocal
