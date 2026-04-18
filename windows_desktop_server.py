#!/usr/bin/env python3
"""
Hermes Windows Desktop Control Server
HTTP API with API Key authentication for desktop automation.
Run on Windows: python windows_desktop_server.py

Security: All requests require X-API-Key header.
Set HERMES_DESKTOP_KEY environment variable to your API key.
If not set, a random key will be generated on first run (shown in console).
"""

import json
import os
import sys
import threading
import socketserver
import subprocess
import secrets
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import io

# Install dependencies check
try:
    import pyautogui
    import PIL.Image
    import win32gui
    import win32con
    import win32api
    import mss
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install pyautogui pillow pywin32 mss")
    sys.exit(1)

# Configuration
PORT = 8765
HOST = "0.0.0.0"

# API Key configuration
# Get from environment variable, or generate a random one on first run
API_KEY = os.environ.get("HERMES_DESKTOP_KEY", "")

def generate_api_key():
    """Generate a secure random API key"""
    return secrets.token_urlsafe(32)

def verify_api_key(request_key):
    """Verify the API key from request header"""
    if not API_KEY:
        return False  # No key configured means authentication disabled
    if not request_key:
        return False
    return secrets.compare_digest(API_KEY, request_key)

# Thread-safe screenshot lock
screenshot_lock = threading.Lock()


class DesktopHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, format, *args):
        """Suppress noisy logs"""
        pass

    def send_json(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_error_json(self, status, error_msg):
        """Send error response"""
        self.send_json({"error": error_msg}, status)

    def check_auth(self):
        """Check API key authentication. Returns True if authorized, False otherwise."""
        api_key = self.headers.get("X-API-Key", "")
        if verify_api_key(api_key):
            return True
        # If no key is configured in environment, allow request
        # This is for initial setup when user hasn't set HERMES_DESKTOP_KEY
        if not API_KEY:
            return True
        return False

    def do_GET(self):
        """Handle GET requests"""
        if not self.check_auth():
            self.send_error_json(401, "Unauthorized: Invalid or missing API key. Set X-API-Key header.")
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/status":
            self.send_json({"status": "running", "service": "hermes-desktop-control"})
        elif path == "/screen_size":
            try:
                size = pyautogui.size()
                self.send_json({"width": size.width, "height": size.height})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        elif path == "/windows":
            try:
                windows = []
                def enum_handler(hwnd, ctx):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            windows.append({"hwnd": hwnd, "title": title})
                win32gui.EnumWindows(enum_handler, None)
                self.send_json({"windows": windows})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        elif path == "/active_window":
            try:
                hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(hwnd)
                self.send_json({"hwnd": hwnd, "title": title})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        else:
            self.send_json({"error": "Unknown endpoint"}, 404)

    def do_POST(self):
        """Handle POST requests"""
        if not self.check_auth():
            self.send_error_json(401, "Unauthorized: Invalid or missing API key. Set X-API-Key header.")
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        action = data.get("action", "")

        try:
            result = self._handle_action(action, data)
            self.send_json(result)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def _handle_action(self, action, data):
        """Route action to handler"""
        handlers = {
            "move_mouse": self._move_mouse,
            "click": self._click,
            "double_click": self._double_click,
            "right_click": self._right_click,
            "scroll": self._scroll,
            "get_mouse_position": self._get_mouse_position,
            "type_text": self._type_text,
            "press": self._press,
            "hotkey": self._hotkey,
            "key_down": self._key_down,
            "key_up": self._key_up,
            "screenshot": self._screenshot,
            "get_pixel_color": self._get_pixel_color,
            "get_screen_size": self._get_screen_size,
            "find_on_screen": self._find_on_screen,
            "activate_window": self._activate_window,
            "run_powershell": self._run_powershell,
        }

        if action not in handlers:
            return {"error": f"Unknown action: {action}"}

        return handlers[action](data)

    def _move_mouse(self, data):
        x = data.get("x", 0)
        y = data.get("y", 0)
        duration = data.get("duration", 0)
        pyautogui.moveTo(x, y, duration=duration)
        return {"success": True, "x": x, "y": y}

    def _click(self, data):
        x = data.get("x")
        y = data.get("y")
        button = data.get("button", "left")
        clicks = data.get("clicks", 1)
        if x is not None and y is not None:
            pyautogui.click(x, y, clicks=clicks, button=button)
        else:
            pyautogui.click(button=button)
        return {"success": True}

    def _double_click(self, data):
        x = data.get("x")
        y = data.get("y")
        if x is not None and y is not None:
            pyautogui.doubleClick(x, y)
        else:
            pyautogui.doubleClick()
        return {"success": True}

    def _right_click(self, data):
        x = data.get("x")
        y = data.get("y")
        if x is not None and y is not None:
            pyautogui.rightClick(x, y)
        else:
            pyautogui.rightClick()
        return {"success": True}

    def _scroll(self, data):
        clicks = data.get("clicks", 3)
        pyautogui.scroll(clicks)
        return {"success": True, "clicks": clicks}

    def _get_mouse_position(self, data):
        pos = pyautogui.position()
        return {"x": pos.x, "y": pos.y}

    def _type_text(self, data):
        text = data.get("text", "")
        interval = data.get("interval", 0)
        pyautogui.write(text, interval=interval)
        return {"success": True}

    def _press(self, data):
        key = data.get("key", "")
        presses = data.get("presses", 1)
        pyautogui.press(key, presses=presses)
        return {"success": True}

    def _hotkey(self, data):
        keys = data.get("keys", [])
        if isinstance(keys, str):
            keys = [keys]
        pyautogui.hotkey(*keys)
        return {"success": True}

    def _key_down(self, data):
        key = data.get("key", "")
        pyautogui.keyDown(key)
        return {"success": True}

    def _key_up(self, data):
        key = data.get("key", "")
        pyautogui.keyUp(key)
        return {"success": True}

    def _screenshot(self, data):
        filename = data.get("filename")
        with screenshot_lock:
            with mss.mss() as sct:
                # Grab all monitors, use the primary one (index 1)
                sct.shot(output=filename or "screenshot.png")
                if filename:
                    return {"success": True, "filename": filename}
                else:
                    # Read back and encode as base64
                    with open("screenshot.png", "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    # Clean up temp file
                    import os
                    os.remove("screenshot.png")
                    return {"success": True, "image": b64, "format": "png"}

    def _get_pixel_color(self, data):
        x = data.get("x", 0)
        y = data.get("y", 0)
        rgb = pyautogui.pixel(x, y)
        return {"r": rgb[0], "g": rgb[1], "b": rgb[2], "hex": "#{02x}{02x}{02x}".format(*rgb)}

    def _get_screen_size(self, data):
        size = pyautogui.size()
        return {"width": size.width, "height": size.height}

    def _find_on_screen(self, data):
        image_path = data.get("image_path")
        confidence = data.get("confidence", 0.9)
        if not image_path or not os.path.exists(image_path):
            return {"error": f"Image not found: {image_path}"}
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                return {"found": True, "x": location.left, "y": location.top, "width": location.width, "height": location.height}
            else:
                return {"found": False}
        except Exception as e:
            return {"error": str(e)}

    def _activate_window(self, data):
        title = data.get("title", "")
        if not title:
            return {"error": "title is required"}
        result = None
        def enum_handler(hwnd, ctx):
            nonlocal result
            if win32gui.IsWindowVisible(hwnd):
                win_title = win32gui.GetWindowText(hwnd)
                if title.lower() in win_title.lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    result = {"success": True, "hwnd": hwnd, "title": win_title}
        win32gui.EnumWindows(enum_handler, None)
        if result:
            return result
        return {"error": f"Window not found: {title}"}

    def _run_powershell(self, data):
        """Run a PowerShell command and return stdout/stderr"""
        command = data.get("command", "")
        timeout = data.get("timeout", 30)
        if not command:
            return {"error": "command is required"}
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            return {
                "success": True,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"error": str(e)}


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    global API_KEY

    # If no API key is set, generate one and display it
    if not API_KEY:
        API_KEY = generate_api_key()
        print("=" * 60)
        print("WARNING: No HERMES_DESKTOP_KEY environment variable set!")
        print("A random API key has been generated for this session.")
        print("To set a permanent key, run: setx HERMES_DESKTOP_KEY <your-key>")
        print("=" * 60)
        print(f"Generated API Key: {API_KEY}")
        print("=" * 60)
        print()
        print("To use this key, add the following header to all requests:")
        print(f"  X-API-Key: {API_KEY}")
        print()
        print("For example:")
        print(f'  curl -H "X-API-Key: {API_KEY}" http://localhost:{PORT}/status')
        print("=" * 60)
        print()

    server = ThreadedHTTPServer((HOST, PORT), DesktopHandler)
    print(f"Hermes Desktop Control Server running on http://localhost:{PORT}")
    print("Ready to accept commands...")
    print(f"API Key authentication: {'Enabled' if os.environ.get('HERMES_DESKTOP_KEY') else 'Auto-generated (see above)'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    # Enable PyAutoGUI failsafe
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1

    main()
