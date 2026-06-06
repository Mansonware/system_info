#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
System Info Tool - Versão Mobile/Desktop
Melhorias:
- Tratamento de erros (psutil, rede, disco)
- Interface responsiva (largura automática)
- Cores ANSI (opcional)
- IP público + interfaces locais
- Uso de disco, processos top, bateria
- Loop interativo
"""

import os
import sys
import platform
import socket
import getpass
import subprocess
from datetime import datetime

try:
    import psutil
except ImportError:
    print("Erro: psutil não está instalado. Execute: pip install psutil")
    sys.exit(1)

# ========= CONFIGURAÇÕES =========
USE_COLORS = True          # Mude para False se o terminal não suportar
CELLULAR_MODE = True       # Ajusta largura e quebras de linha

# Cores ANSI (se suportado)
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

if not USE_COLORS:
    for attr in dir(Colors):
        if not attr.startswith("__"):
            setattr(Colors, attr, "")

def get_term_width():
    """Obtém largura do terminal, limitada para celular."""
    try:
        width = os.get_terminal_size().columns
    except:
        width = 80
    if CELLULAR_MODE:
        width = min(width, 50)  # Força quebras amigáveis no celular
    return width

def print_header(title):
    """Imprime cabeçalho estilizado."""
    width = get_term_width()
    print(Colors.CYAN + "=" * width + Colors.RESET)
    print(Colors.BOLD + title.center(width) + Colors.RESET)
    print(Colors.CYAN + "=" * width + Colors.RESET)

def print_section(name):
    """Imprime nome da seção."""
    print(f"\n{Colors.YELLOW}▶ {name}{Colors.RESET}")

def safe_get(func, default="N/A"):
    """Executa função com tratamento de erro."""
    try:
        return func()
    except Exception as e:
        return f"{default} ({str(e)})"

# ========= FUNÇÕES DE INFORMAÇÕES =========

def get_system_info():
    """Sistema operacional, usuário, hostname."""
    user = getpass.getuser()
    system = platform.system()
    node = platform.node()
    release = platform.release()
    version = platform.version()
    machine = platform.machine()
    boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "Usuário": user,
        "Sistema": system,
        "Nome do nó": node,
        "Kernel/Release": release,
        "Versão": version,
        "Arquitetura": machine,
        "Inicialização": boot_time
    }

def get_cpu_info():
    """Uso da CPU, núcleos, frequência."""
    usage = psutil.cpu_percent(interval=0.5)
    freq = psutil.cpu_freq()
    freq_cur = freq.current if freq else None
    cores_fisicos = psutil.cpu_count(logical=False)
    cores_logicos = psutil.cpu_count(logical=True)
    
    return {
        "Uso": f"{usage}%",
        "Frequência": f"{freq_cur:.0f} MHz" if freq_cur else "N/A",
        "Cores físicos": cores_fisicos or "N/A",
        "Cores lógicos": cores_logicos or "N/A"
    }

def get_memory_info():
    """RAM (total, disponível, usado, porcentagem)."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "RAM Total": f"{mem.total / (1024**3):.2f} GB",
        "RAM Disponível": f"{mem.available / (1024**3):.2f} GB",
        "RAM Usado": f"{mem.used / (1024**3):.2f} GB",
        "RAM %": f"{mem.percent}%",
        "Swap Total": f"{swap.total / (1024**3):.2f} GB" if swap.total else "N/A",
        "Swap %": f"{swap.percent}%" if swap.total else "N/A"
    }

def get_disk_info():
    """Partições e uso de disco."""
    partitions = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "Dispositivo": part.device,
                "Ponto": part.mountpoint,
                "Total": f"{usage.total / (1024**3):.2f} GB",
                "Usado": f"{usage.used / (1024**3):.2f} GB",
                "Livre": f"{usage.free / (1024**3):.2f} GB",
                "Uso%": f"{usage.percent}%"
            })
        except PermissionError:
            continue
    return partitions

def get_network_info():
    """IP local, hostname, interfaces, IP público."""
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "N/A"
    
    # Interfaces detalhadas (IPv4)
    interfaces = {}
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                interfaces[iface] = addr.address
                break
    
    # IP público (via API simples)
    public_ip = "N/A"
    try:
        import urllib.request
        with urllib.request.urlopen("https://api.ipify.org", timeout=3) as response:
            public_ip = response.read().decode().strip()
    except:
        public_ip = "Não foi possível obter"
    
    return {
        "Hostname": hostname,
        "IP Local": local_ip,
        "IP Público": public_ip,
        "Interfaces": interfaces
    }

def get_battery_info():
    """Bateria (se disponível)."""
    if not hasattr(psutil, "sensors_battery"):
        return None
    battery = psutil.sensors_battery()
    if battery:
        return {
            "Percentual": f"{battery.percent}%",
            "Carregando": "Sim" if battery.power_plugged else "Não",
            "Tempo restante": f"{battery.secsleft // 60} min" if battery.secsleft != -1 else "Indeterminado"
        }
    return None

def get_top_processes(n=5):
    """Top N processos por uso de CPU."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            pinfo['cpu_percent'] = pinfo['cpu_percent'] or 0.0
            processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    processes.sort(key=lambda p: p['cpu_percent'], reverse=True)
    return processes[:n]

# ========= FUNÇÃO PRINCIPAL DE EXIBIÇÃO =========

def show_full_info():
    """Exibe todas as informações formatadas para mobile."""
    width = get_term_width()
    print_header(f" SYSTEM INFO - {datetime.now().strftime('%H:%M:%S')} ")
    
    # Sistema
    print_section("SISTEMA OPERACIONAL")
    sys_info = get_system_info()
    for key, val in sys_info.items():
        print(f"  {Colors.BOLD}{key}:{Colors.RESET} {val}")
    
    # CPU
    print_section("CPU")
    cpu_info = get_cpu_info()
    for key, val in cpu_info.items():
        print(f"  {Colors.BOLD}{key}:{Colors.RESET} {val}")
    
    # Memória
    print_section("MEMÓRIA RAM")
    mem_info = get_memory_info()
    for key, val in mem_info.items():
        print(f"  {Colors.BOLD}{key}:{Colors.RESET} {val}")
    
    # Disco
    print_section("DISCO (PARTIÇÕES)")
    disks = get_disk_info()
    if disks:
        for d in disks:
            print(f"  📀 {Colors.BOLD}{d['Dispositivo']}{Colors.RESET} ({d['Ponto']})")
            print(f"     Total: {d['Total']} | Usado: {d['Usado']} | Uso: {d['Uso%']}")
    else:
        print("  Nenhuma partição acessível")
    
    # Rede
    print_section("REDE")
    net_info = get_network_info()
    print(f"  {Colors.BOLD}Hostname:{Colors.RESET} {net_info['Hostname']}")
    print(f"  {Colors.BOLD}IP Local:{Colors.RESET} {net_info['IP Local']}")
    print(f"  {Colors.BOLD}IP Público:{Colors.RESET} {net_info['IP Público']}")
    if net_info["Interfaces"]:
        print(f"  {Colors.BOLD}Interfaces ativas:{Colors.RESET}")
        for iface, ip in net_info["Interfaces"].items():
            print(f"     {iface}: {ip}")
    
    # Bateria
    battery = get_battery_info()
    if battery:
        print_section("BATERIA")
        for key, val in battery.items():
            print(f"  {Colors.BOLD}{key}:{Colors.RESET} {val}")
    
    # Processos Top
    print_section(f"TOP {5} PROCESSOS POR CPU")
    top_procs = get_top_processes(5)
    for i, proc in enumerate(top_procs, 1):
        cpu = proc['cpu_percent']
        mem = proc['memory_percent']
        name = proc['name'][:20]  # corta nome longo
        print(f"  {i}. {Colors.BOLD}{name}{Colors.RESET} | CPU: {cpu:.1f}% | MEM: {mem:.1f}%")
    
    print(Colors.CYAN + "=" * width + Colors.RESET)

# ========= INTERATIVO PARA MOBILE =========

def interactive_loop():
    """Loop simples para celular: atualizar, menu, sair."""
    while True:
        show_full_info()
        print("\n[ENTER] Atualizar   [Q] Sair")
        choice = input("> ").strip().lower()
        if choice == 'q':
            print("\nEncerrando...")
            break
        # Limpa tela (compatível com Termux, etc.)
        os.system('clear' if os.name == 'posix' else 'cls')

# ========= PONTO DE ENTRADA =========

if __name__ == "__main__":
    try:
        # Verifica se está em ambiente móvel (Termux, iSH)
        if "ANDROID_ROOT" in os.environ or "TERMUX" in os.environ:
            CELLULAR_MODE = True
            print(Colors.GREEN + "Modo celular detectado (Termux)" + Colors.RESET)
        elif "iOS" in platform.system() or "iPad" in platform.system():
            CELLULAR_MODE = True
            print(Colors.GREEN + "Modo iOS detectado" + Colors.RESET)
        
        interactive_loop()
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário.")
    except Exception as e:
        print(f"\n{Colors.RED}Erro inesperado: {e}{Colors.RESET}")