# Single-terminal demo: starts both peers as background jobs, waits for the
# game to finish, then runs the Replay Viewer on the produced log and prints
# the verdict. For a more realistic two-terminal demo, run run_police.ps1
# and run_thief.ps1 in separate windows instead.
param(
    [string]$GameId = "demo-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    [double]$MaxWaitSeconds = 60
)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$policeOut = "logs/$GameId/police"
$thiefOut  = "logs/$GameId/thief"

Write-Host "Starting police and thief peers (game_id=$GameId)..."

$policeJob = Start-Job -ScriptBlock {
    param($root, $GameId, $policeOut, $MaxWaitSeconds)
    Set-Location $root
    uv run python -m police_thief peer --role police --config-dir config `
        --game-id $GameId --output-dir $policeOut --max-wait-seconds $MaxWaitSeconds
} -ArgumentList $root, $GameId, $policeOut, $MaxWaitSeconds

$thiefJob = Start-Job -ScriptBlock {
    param($root, $GameId, $thiefOut, $MaxWaitSeconds)
    Set-Location $root
    uv run python -m police_thief peer --role thief --config-dir config `
        --game-id $GameId --output-dir $thiefOut --max-wait-seconds $MaxWaitSeconds
} -ArgumentList $root, $GameId, $thiefOut, $MaxWaitSeconds

Write-Host "Waiting for both peers to finish (timeout: $($MaxWaitSeconds + 60)s)..."
Wait-Job -Job $policeJob, $thiefJob -Timeout ($MaxWaitSeconds + 60) | Out-Null

Write-Host ""
Write-Host "===== police output ====="
Receive-Job -Job $policeJob
Write-Host ""
Write-Host "===== thief output ====="
Receive-Job -Job $thiefJob

Remove-Job -Job $policeJob, $thiefJob -Force -ErrorAction SilentlyContinue

$logPath = "logs/$GameId/police/log_${GameId}_g01.json"
if (Test-Path $logPath) {
    Write-Host ""
    Write-Host "===== Replay Viewer ====="
    uv run python -m police_thief replay --log $logPath
} else {
    Write-Warning "No log file found at $logPath -- the game may not have completed."
}
