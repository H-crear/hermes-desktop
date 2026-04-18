---
name: hermes-desktop-api
description: Hermes Windows Desktop Control Server API - correct endpoint format and usage patterns
triggers:
  - desktop control
  - windows automation
  - hermes desktop
  - 桌面控制
  - windows 自动化
  - control windows from wsl
  - 操控 Windows 桌面
---

# Hermes Desktop Control Server API

## Overview
HTTP API server running on Windows for desktop automation control.

**Server path:** `C:\hermes-desktop\windows_desktop_server.py`
**Default port:** 8765
**Host IP:** `{WINDOWS_IP}` (WSL访问Windows，如 172.31.32.1 或 127.0.0.1)

## Authentication
- API Key: `{YOUR_API_KEY}`
- Header: `X-API-Key: {YOUR_API_KEY}`

## Critical: Correct API Format

**MISTAKE:** Using `/execute` endpoint or `{"command": "..."}`
**CORRECT:** POST to root path `/` with `{"action": "...", ...}`

### ✅ Correct Call Pattern
```bash
curl -s --connect-timeout 5 -m 10 -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "run_powershell", "command": "...", "timeout": 10}'
```

### Available Actions

| Action | Parameters | Description |
|--------|-----------|-------------|
| `run_powershell` | `command`, `timeout` | Execute PowerShell command |
| `screenshot` | `filename` (optional) | Take screenshot |
| `move_mouse` | `x`, `y`, `duration` | Move mouse |
| `click` | `x`, `y`, `button`, `clicks` | Click mouse |
| `double_click` | `x`, `y` | Double click |
| `right_click` | `x`, `y` | Right click |
| `scroll` | `clicks` | Scroll |
| `type_text` | `text`, `interval` | Type text |
| `press` | `key`, `presses` | Press key |
| `hotkey` | `keys` (array) | Press hotkey combo |
| `key_down` | `key` | Hold key |
| `key_up` | `key` | Release key |
| `get_mouse_position` | - | Get cursor position |
| `get_pixel_color` | `x`, `y` | Get pixel RGB |
| `get_screen_size` | - | Get resolution |
| `find_on_screen` | `image_path`, `confidence` | Image recognition |
| `activate_window` | `title` | Focus window by title |
| `windows` | - | List all windows |
| `active_window` | - | Get foreground window |
| `screen_size` | - | Get resolution |

## HTTP/1.1 Timeout Behavior

**Important:** Server uses HTTP/1.1 keep-alive. curl may timeout (exit code 28) even when command succeeds.

- ✅ Command output IS returned in response body — check it
- ✅ A timeout does NOT mean the command failed
- ⚠️ However, some commands genuinely hang (e.g. starting GUI apps that never return)

**Always use `--connect-timeout 5 -m 10`** (or higher timeout) to give commands time to complete.

**Pattern for long-running commands (like starting a server):**
```bash
# Use Start-Process so command returns immediately, then verify separately
Start-Process powershell -ArgumentList "-Command","python C:\\path\\to\\server.py" -WindowStyle Hidden
Start-Sleep -Seconds 3
Write-Output "DONE"
```

---

## Health Check & Service Verification

**Before running any task**, verify the service is running:

```bash
curl -s --connect-timeout 3 -m 5 -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "screen_size"}'
```

**Expected success response:**
```json
{"success": true, "width": 1920, "height": 1080}
```

**If connection refused:** Server is not running on Windows. Need to start it:
```powershell
# On Windows, run:
python C:\hermes-desktop\windows_desktop_server.py
```

---

## Screenshot — Troubleshooting

**Problem:** Screenshot action times out or returns error

**Diagnosis steps:**
```bash
# Step 1: Verify service is healthy
curl -s --connect-timeout 5 -m 10 -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "screen_size"}'

# Step 2: Try PowerShell fallback method
curl -s --connect-timeout 5 -m 10 -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "run_powershell", "command": "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width", "timeout": 10}'
```

**If PowerShell screenshot works but built-in action doesn't:** Use the PowerShell method as fallback. It is slower but reliable.

**Screenshot files:** Save to `C:\\Users\\{USERNAME}\\Pictures\\` or `C:\\Users\\{USERNAME}\\Desktop\\`, then copy to WSL:
```bash
cp "/mnt/c/Users/{USERNAME}/Pictures/screenshot.png" "/tmp/screenshot.png"
```

## PowerShell Command Pitfalls

Complex PowerShell commands with nested quotes/escapes cause `{"error": "Invalid JSON"}`.
**Workaround:** Write script to .ps1 file on disk first, execute with `Start-Process`.

```bash
# ❌ Bad - complex nested commands fail
{"action": "run_powershell", "command": "python -c \"import os; print('hello')\""}

# ✅ Good - write to .ps1 file first
# 1. Write file with action: run_powershell, command: "Set-Content -Path 'C:/test.ps1' -Value 'python stuff'"
# 2. Execute: Start-Process powershell -ArgumentList "-File", "C:/test.ps1"
```

---

## Quick Reference: Common Issues

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| `Connection refused` | 服务没启动 | Windows 上运行 `python C:\hermes-desktop\windows_desktop_server.py` |
| curl 超时但命令成功 | HTTP keep-alive | 忽略 exit code 28，检查 response body |
| 截图超时 | screenshot action 不稳定 | 用 PowerShell 方法替代 |
| pip install 失败 | 用了 hermes-agent venv 的 Python | 用完整路径 `C:\Users\{USERNAME}\AppData\Local\Programs\Python\Python311\python.exe` |
| GUI 程序启动后卡住 | Start-Process 没加 `-WindowStyle Hidden` | 用 `Start-Process ... -WindowStyle Hidden` |

---

## Python Client
```python
import requests

API = "http://{WINDOWS_IP}:8765/"
HEADERS = {"X-API-Key": "{YOUR_API_KEY}"}

def desktop(action, **kwargs):
    resp = requests.post(API, headers=HEADERS, json={**kwargs, "action": action}, timeout=15)
    return resp.json()
```

## Process Management
```powershell
# Find process by name
Get-Process | Where-Object {$_.ProcessName -like "*JianYing*"}

# Start process
Start-Process "C:\\path\\to\\app.exe"

# Kill process
Stop-Process -Name "JianYingPro" -Force

# Start hidden background process
Start-Process powershell -ArgumentList "-NoExit","-Command","& { ... }" -WindowStyle Hidden

# Start app and verify
Start-Process "C:\\Users\\{USERNAME}\\AppData\\Local\\JianyingPro\\Apps\\JianYingPro.exe"
Start-Sleep -Seconds 5
Get-Process | Where-Object {$_.ProcessName -like "*JianYing*"} | ConvertTo-Json
```

## Background Task Pattern (Critical)

When starting long-running services, use Start-Process with -WindowStyle Hidden + file-based script:

```powershell
# 1. Write startup script to disk
# Content: cd C:\path\to\backend; python app.py

# 2. Execute via Start-Process
Start-Process powershell -ArgumentList "-NoExit","-Command","& { C:/path/to/start.ps1 }" -WindowStyle Hidden
Start-Sleep -Seconds 4
Write-Output "SERVER_STARTED"
```

## Screenshot Methods

### Method 1: Built-in screenshot action (fastest)
```json
{"action": "screenshot", "filename": "C:\\Users\\{USERNAME}\\screenshot.png"}
```

### Method 2: Pure PowerShell (when action unavailable)
```powershell
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screenshot = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screenshot.Bounds.Width, $screenshot.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screenshot.Bounds.Location, [System.Drawing.Point]::Empty, $screenshot.Bounds.Size)
$bitmap.Save("C:\\Users\\{USERNAME}\\screenshot.png")
$graphics.Dispose(); $bitmap.Dispose()
Write-Output "SCREENSHOT_SAVED"
```

Note: Screenshots saved to Windows paths (`C:\...`) need to be copied to WSL (`/mnt/c/...`) before vision analysis.

## Known Paths
```
JianYingPro:  C:\Users\{USERNAME}\AppData\Local\JianyingPro\Apps\JianYingPro.exe
WSL Chrome:    ~/.local/chrome/ + ~/.agent-browser/browsers/
OpenClaw:      C:\Users\{USERNAME}\.openclaw\
Data folders:  C:\Users\{USERNAME}\.openclaw\workspace\data\
```

## Python Environment Conflict (Critical)

When executing Python via `run_powershell`, the `python` command may resolve to the hermes-agent venv, which lacks pip:

```
C:\Users\{USERNAME}\AppData\Local\{AGENT_DIR}\hermes-agent\venv\python.exe
```

**Symptoms**: pip install fails with "No module named pip", or modules installed but not found.

**Detection**: Check which python is used:
```powershell
python --version  # shows venv Python, NOT system Python
Get-Command python | Select-Object -ExpandProperty Source
```

**Solution**: Use the full system Python path:
```
C:\Users\{USERNAME}\AppData\Local\Programs\Python\Python311\python.exe
```

Or use the full path to install/run:
```powershell
C:\Users\{USERNAME}\AppData\Local\Programs\Python\Python311\python.exe -m pip install flask flask-cors
C:\Users\{USERNAME}\AppData\Local\Programs\Python\Python311\python.exe app.py
```
