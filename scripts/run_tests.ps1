# Full verification pass: formatting, linting, type checking, and tests.
# Pass -Full to also run the slow real-two-process e2e test (~1 min extra).
param(
    [switch]$Full
)

Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "===== uv sync ====="
uv sync
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "===== ruff format --check ====="
uv run ruff format --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "===== ruff check ====="
uv run ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "===== mypy ====="
uv run mypy src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
if ($Full) {
    Write-Host "===== pytest (full suite, including e2e) ====="
    uv run pytest -v
} else {
    Write-Host "===== pytest (fast subset, skipping e2e; use -Full for everything) ====="
    uv run pytest -m "not e2e" -v
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "===== pytest --cov ====="
uv run pytest --cov=src --cov-report=term-missing -m "not e2e" -q
