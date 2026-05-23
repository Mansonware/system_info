import platform
import socket
import getpass
import psutil

def system_info():
    print("\n===== SYSTEM INFO TOOL =====\n")

    print(f"User: {getpass.getuser()}")
    print(f"System: {platform.system()}")
    print(f"Node Name: {platform.node()}")
    print(f"Release: {platform.release()}")
    print(f"Version: {platform.version()}")
    print(f"Machine: {platform.machine()}")

    print("\n--- CPU ---")
    print(f"CPU Usage: {psutil.cpu_percent()}%")

    print("\n--- MEMORY ---")
    mem = psutil.virtual_memory()
    print(f"Total: {mem.total / (1024**3):.2f} GB")
    print(f"Available: {mem.available / (1024**3):.2f} GB")
    print(f"Used: {mem.used / (1024**3):.2f} GB")

    print("\n--- NETWORK ---")
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    print(f"Hostname: {hostname}")
    print(f"Local IP: {ip}")

    print("\n===========================\n")

if __name__ == "__main__":
    system_info()
