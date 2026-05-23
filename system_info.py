import platform
import socket
import getpass
import psutil


def get_real_ip():
    """Pega o IP real da rede (não o localhost do WSL)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"


def system_info():
    print("\n===== SYSTEM INFO TOOL =====\n")

    # Usuário
    print(f"User: {getpass.getuser()}")

    # Sistema
    print(f"System: {platform.system()}")
    print(f"Node Name: {platform.node()}")
    print(f"Release: {platform.release()}")
    print(f"Version: {platform.version()}")
    print(f"Machine: {platform.machine()}")

    # CPU
    print("\n--- CPU ---")
    print(f"CPU Usage: {psutil.cpu_percent(interval=1)}%")

    # Memória
    print("\n--- MEMORY ---")
    memory = psutil.virtual_memory()
    print(f"Total: {memory.total / (1024**3):.2f} GB")
    print(f"Available: {memory.available / (1024**3):.2f} GB")
    print(f"Used: {memory.used / (1024**3):.2f} GB")

    # Rede
    print("\n--- NETWORK ---")
    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    print(f"Local IP: {get_real_ip()}")

    print("\n===========================\n")


if __name__ == "__main__":
    system_info()
