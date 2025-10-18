@echo off
setlocal
set BASE=%~dp0
set PY=%BASE%\.venv\Scripts\pythonw.exe
if not exist "%PY%" set PY=%BASE%\.venv\Scripts\python.exe
"%PY%" -m snap_ocr %*
endlocal

