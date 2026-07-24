# Starts the police (cop) side of a local demo game.
# Run this in its own terminal window; run scripts/run_thief.ps1 in another.
param(
    [string]$GameId = "local-demo",
    [string]$OutputDir = "logs/$GameId",
    [double]$MaxWaitSeconds = 60
)

Set-Location (Split-Path -Parent $PSScriptRoot)
uv run python -m police_thief peer `
    --role police `
    --config-dir config `
    --game-id $GameId `
    --output-dir $OutputDir `
    --max-wait-seconds $MaxWaitSeconds
