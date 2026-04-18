# Restart Hermes Desktop Server
Set-Location C:\hermes-desktop

# Kill any existing python processes on port 8765
Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

# Check API key
if (-not $env:HERMES_DESKTOP_KEY) {
    Write-Host "WARNING: HERMES_DESKTOP_KEY environment variable is not set."
    Write-Host "A random API key will be auto-generated. See server console for the key."
    Write-Host "To set a permanent key: [System.Environment]::SetEnvironmentVariable('HERMES_DESKTOP_KEY', 'your-key', 'User')"
    Write-Host ""
}

# Start server
$proc = Start-Process -FilePath "python" -ArgumentList "C:\hermes-desktop\windows_desktop_server.py" -PassThru -WindowStyle Hidden -Environment @{"HERMES_DESKTOP_KEY"=$env:HERMES_DESKTOP_KEY}
Write-Host "Started server with PID: $($proc.Id)"
Start-Sleep -Seconds 3

# Check if still running
if ($proc.HasExited) {
    Write-Host "[ERROR] Server exited with code: $($proc.ExitCode)"
    exit 1
}

# Check port
$listenPort = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listenPort) {
    Write-Host "[OK] Server listening on $($listenPort.LocalAddress):$($listenPort.LocalPort) by PID $($listenPort.OwningProcess)"
} else {
    Write-Host "[WARN] Port 8765 not listening yet"
}
