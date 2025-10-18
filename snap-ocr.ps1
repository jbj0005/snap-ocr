$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $base ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $py)) { $py = Join-Path $base ".venv\Scripts\python.exe" }
& $py -m snap_ocr @args

