import socket
import os

def serveur():
    os.makedirs("received_screenshots", exist_ok=True)
    log_file = open("received_logs.txt", "a", encoding="utf-8")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 4444))
    s.listen(1)
    print("En attente de connexion...")
    conn, addr = s.accept()
    print(f"Connecté par {addr}")

    try:
        while True:
            header = b""
            # Lire la ligne d'en-tête (finie par \n)
            while not header.endswith(b"\n"):
                chunk = conn.recv(1)
                if not chunk:
                    raise ConnectionError("Connexion fermée")
                header += chunk

            header = header.decode().strip()
            if header.startswith("LOG|"):
                # Log reçu
                message = header[4:]
                print(f"[LOG] {message}")
                log_file.write(message + "\n")
                log_file.flush()

            elif header.startswith("IMAGE|"):
                # Format: IMAGE|filename|taille
                parts = header.split("|")
                if len(parts) != 3:
                    print("Header image mal formé :", header)
                    continue

                _, filename, taille_str = parts
                taille = int(taille_str)

                print(f"[IMAGE] Réception de {filename} ({taille} bytes)")

                # Lire le contenu de l'image
                remaining = taille
                image_data = b""
                while remaining > 0:
                    data = conn.recv(min(4096, remaining))
                    if not data:
                        raise ConnectionError("Connexion fermée pendant transfert image")
                    image_data += data
                    remaining -= len(data)

                # Sauvegarder l'image
                chemin = os.path.join("received_screenshots", filename)
                with open(chemin, "wb") as f:
                    f.write(image_data)

                print(f"[IMAGE] Enregistrée : {chemin}")

            else:
                print("[INFO] Header inconnu :", header)

    except Exception as e:
        print(f"[Erreur] {e}")

    finally:
        log_file.close()
        conn.close()
        s.close()

if __name__ == "__main__":
    serveur()