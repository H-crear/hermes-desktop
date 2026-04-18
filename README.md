# Hermes Desktop Control

> 通过 HTTP API 远程控制 Windows 桌面，支持鼠标、键盘、截图、窗口管理等操作。

[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 功能特点

- 鼠标控制 — 像素级精准移动、点击、拖拽、滚动
- 键盘控制 — 文字输入、组合键、快捷键
- 屏幕截图 — 实时获取屏幕画面
- 窗口管理 — 获取窗口信息、激活窗口
- API 认证 — 请求头密钥验证
- 简单易用 — HTTP API 设计，无需复杂配置

## 系统要求

- Windows 10/11
- Python 3.8+
- 网络连接（WSL/Linux 与 Windows 互通）

## 安装依赖

```powershell
pip install pyautogui pillow pywin32 mss
```

## 快速开始

### 1. 配置 API 密钥

生成密钥：
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

设置环境变量（永久）：
```powershell
setx HERMES_DESKTOP_KEY "your-generated-key"
```

### 2. 启动服务

```powershell
# 方式1：双击启动
start_server.bat

# 方式2：手动启动
cd C:\hermes-desktop
python windows_desktop_server.py
```

服务地址：`http://{WINDOWS_IP}:8765`

### 3. 验证服务

```bash
# 健康检查
curl -s --connect-timeout 5 -m 10 -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "screen_size"}'

# 预期响应
# {"success": true, "width": 1920, "height": 1080}
```

## API 文档

### 认证

所有请求需要包含 `X-API-Key` 请求头：

```bash
-H "X-API-Key: {YOUR_API_KEY}"
```

### 重要：正确的 API 格式

**错误用法：** 使用 `/execute` 端点或 `{"command": "..."}`

**正确用法：** POST 到根路径 `/`，使用 `{"action": "...", ...}`

### GET 查询类

| URL | 说明 |
|-----|------|
| `/status` | 服务状态 |
| `/screen_size` | 屏幕分辨率 |
| `/windows` | 所有窗口列表 |
| `/active_window` | 当前前台窗口 |

### POST 执行类

所有 POST 请求发送到 `/`，body 为 JSON：

```json
{"action": "action_name", "param1": "value1"}
```

| Action | 参数 | 说明 |
|--------|------|------|
| `move_mouse` | x, y, duration | 移动鼠标 |
| `click` | x, y, button, clicks | 点击 |
| `double_click` | x, y | 双击 |
| `right_click` | x, y | 右键 |
| `scroll` | clicks | 滚轮 |
| `get_mouse_position` | - | 鼠标坐标 |
| `type_text` | text, interval | 输入文本 |
| `press` | key, presses | 按键 |
| `hotkey` | keys[] | 组合键 |
| `key_down` | key | 按下按键 |
| `key_up` | key | 松开按键 |
| `screenshot` | filename(可选) | 截图 |
| `get_pixel_color` | x, y | 像素颜色 |
| `find_on_screen` | image_path, confidence | 找图 |
| `activate_window` | title | 激活窗口 |
| `run_powershell` | command, timeout | 执行 PowerShell |

## 使用示例

### 截图

```bash
# 保存到文件
curl -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "screenshot", "filename": "C:\\Users\\{USERNAME}\\screenshot.png"}'

# 返回 base64
curl -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "screenshot"}'
```

### 鼠标操作

```bash
# 移动鼠标
curl -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "move_mouse", "x": 500, "y": 300}'

# 点击
curl -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "click", "x": 500, "y": 300}'
```

### 执行 PowerShell

```bash
curl -X POST "http://{WINDOWS_IP}:8765/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {YOUR_API_KEY}" \
  -d '{"action": "run_powershell", "command": "Get-Process | Select-Object -First 5", "timeout": 10}'
```

### Python 客户端

```python
import requests

API = "http://{WINDOWS_IP}:8765/"
HEADERS = {"X-API-Key": "{YOUR_API_KEY}"}

def desktop(action, **kwargs):
    resp = requests.post(API, headers=HEADERS, json={**kwargs, "action": action}, timeout=15)
    return resp.json()

# 获取屏幕尺寸
print(desktop("screen_size"))

# 截图
print(desktop("screenshot", filename="screenshot.png"))

# 执行 PowerShell
print(desktop("run_powershell", command="Get-Date", timeout=5))
```

## 故障排查

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| `Connection refused` | 服务没启动 | Windows 上运行 `python C:\hermes-desktop\windows_desktop_server.py` |
| curl 超时但命令成功 | HTTP keep-alive | 忽略 exit code 28，检查 response body |
| 截图超时 | screenshot action 不稳定 | 用 PowerShell 方法替代 |
| pip install 失败 | 用了 hermes-agent venv 的 Python | 用完整路径 `C:\Users\{USERNAME}\AppData\Local\Programs\Python\Python311\python.exe` |
| GUI 程序启动后卡住 | Start-Process 没加 `-WindowStyle Hidden` | 用 `Start-Process ... -WindowStyle Hidden` |

## HTTP/1.1 超时说明

服务器使用 HTTP/1.1 keep-alive。curl 可能超时（exit code 28）但命令实际已成功：

- 命令输出在 response body 中 — 务必检查
- 超时不代表命令失败
- 建议使用 `--connect-timeout 5 -m 10`（或更长）

**长命令模式（如启动服务器）：**
```bash
Start-Process powershell -ArgumentList "-Command","python C:\\path\\to\\server.py" -WindowStyle Hidden
Start-Sleep -Seconds 3
Write-Output "DONE"
```

## PowerShell 命令陷阱

复杂 PowerShell 命令（含嵌套引号/转义）会导致 `{"error": "Invalid JSON"}`。

**解决方法：** 先写入 .ps1 文件，再执行

```bash
# 错误 - 嵌套命令会失败
{"action": "run_powershell", "command": "python -c \"import os; print('hello')\""}

# 正确 - 先写文件
# 1. 写入文件: {"action": "run_powershell", "command": "Set-Content -Path 'C:/test.ps1' -Value 'python stuff'"}
# 2. 执行: Start-Process powershell -ArgumentList "-File", "C:/test.ps1"
```

## 开机自启动

**方式A：快捷方式放入启动文件夹**
```powershell
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\HermesDesktop.lnk")
$Shortcut.TargetPath = "python.exe"
$Shortcut.Arguments = "C:\hermes-desktop\windows_desktop_server.py"
$Shortcut.WorkingDirectory = "C:\hermes-desktop"
$Shortcut.Description = "Hermes Desktop Control Service"
$Shortcut.Save()
```

**方式B：任务计划程序**
```powershell
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "C:\hermes-desktop\windows_desktop_server.py" -WorkingDirectory "C:\hermes-desktop"
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "HermesDesktop" -Action $action -Trigger $trigger -Description "Hermes Desktop Control Service" -RunLevel Highest
```

## 安全机制

### FAILSAFE 保护

PyAutoGUI 内置四角紧急停止保护：移动鼠标到屏幕任意一角立即停止所有自动化操作。

### 敏感操作

`run_powershell` 可执行任意 Windows 命令，请勿将端口暴露在公网。

## 项目结构

```
hermes-desktop/
├── windows_desktop_server.py   # 主服务（含 API 认证）
├── start_server.bat            # 启动脚本
├── restart_server.ps1          # 重启脚本
├── skills/
│   └── hermes-desktop-api/    # Hermes Agent skill
│       └── SKILL.md
├── .env.example               # 环境变量示例
└── README.md                  # 本文档
```

## License

MIT License
