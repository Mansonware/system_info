#!/usr/bin/env python3
"""
SYSTEM INTELLIGENCE TOOL  ::  recon-grade host profiler
=======================================================

Coleta e exibe inteligência profunda sobre o host: identidade, kernel,
CPU, memória, discos, rede (interfaces + IP público + conexões), bateria,
sensores térmicos e os processos mais ativos. Saída no estilo terminal
hacker (cores ANSI, banner, painéis) e responsiva para desktop e mobile
(Termux / iSH). Suporta export JSON, watch mode e seleção de seções.

Uso:
    python3 system_info.py                 # snapshot completo, colorido
    python3 system_info.py --no-color      # sem cores ANSI
    python3 system_info.py --json          # despeja inteligência em JSON
    python3 system_info.py --watch         # refresh contínuo (Ctrl-C p/ sair)
    python3 system_info.py -s cpu,net      # apenas seções escolhidas
    python3 system_info.py --no-net        # pula a coleta de IP público

Dependência opcional: psutil (degrada graciosamente se ausente).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import getpass
import json
import os
import platform
import shutil
import socket
import sys
import time

try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except Exception:  # pragma: no cover - ambiente sem psutil
    psutil = None  # type: ignore
    _HAS_PSUTIL = False


__version__ = "2.0.0"

# Seções disponíveis, na ordem de renderização. "host" é sempre coletada.
ALL_SECTIONS = ("host", "cpu", "memory", "disks", "network", "sensors", "processes")

# --------------------------------------------------------------------------- #
#  Camada de apresentação (cores ANSI / layout)                               #
# --------------------------------------------------------------------------- #

class C:
    """Paleta ANSI no estilo terminal hacker (verde-fosforado)."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[38;5;46m"
    DGREEN = "\033[38;5;28m"
    CYAN = "\033[38;5;51m"
    AMBER = "\033[38;5;214m"
    RED = "\033[38;5;196m"
    GREY = "\033[38;5;245m"
    WHITE = "\033[97m"

    _ENABLED = True

    @classmethod
    def disable(cls) -> None:
        cls._ENABLED = False

    @classmethod
    def paint(cls, text: str, color: str) -> str:
        if not cls._ENABLED:
            return text
        return f"{color}{text}{cls.RESET}"


def _term_width(default: int = 80) -> int:
    """Largura do terminal, com teto/piso amigável para mobile."""
    try:
        cols = shutil.get_terminal_size().columns
    except Exception:
        cols = default
    return max(34, min(cols, 100))


def _gauge(percent: float, width: int) -> str:
    """Barra de progresso colorida por severidade."""
    percent = max(0.0, min(100.0, float(percent)))
    filled = int(round((percent / 100.0) * width))
    if percent >= 90:
        color = C.RED
    elif percent >= 70:
        color = C.AMBER
    else:
        color = C.GREEN
    bar = "█" * filled + "░" * (width - filled)
    return C.paint(bar, color)


def _human_bytes(num: float) -> str:
    """Bytes -> string legível (KB/MB/GB/TB)."""
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num) < 1024.0:
            return f"{num:6.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} EB"


def _banner() -> str:
    art = r"""
   ___ ___  _____ _____ ___ __  __   ___ _  _ _____ ___ _
  / __/ _ \|_   _|_   _| __|  \/  | |_ _| \| |_   _| __| |
  \__ \ (_) | | |   | | | _|| |\/| |  | || .` | | | | _|| |__
  |___/\___/  |_|   |_| |___|_|  |_| |___|_|\_| |_| |___|____|
"""
    return C.paint(art, C.GREEN)


def _section(title: str, width: int) -> str:
    label = f" {title} "
    fill = "═" * max(0, width - len(label) - 4)
    line = f"{C.paint('▓▒░', C.GREEN)} {C.paint(label.strip(), C.BOLD + C.CYAN)} {C.paint(fill, C.DGREEN)}"
    return line


def _row(key: str, value, width: int, key_w: int = 16) -> str:
    key_txt = f"{key:<{key_w}}"
    return f"  {C.paint(key_txt, C.GREY)} {C.paint('›', C.DGREEN)} {C.paint(str(value), C.WHITE)}"


# --------------------------------------------------------------------------- #
#  Camada de coleta de inteligência (sem efeitos colaterais de print)         #
# --------------------------------------------------------------------------- #

def _uptime_string(boot_ts: float) -> str:
    delta = _dt.timedelta(seconds=int(time.time() - boot_ts))
    days, rem = divmod(int(delta.total_seconds()), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    parts.append(f"{hours:02d}h")
    parts.append(f"{minutes:02d}m")
    return " ".join(parts)


def get_real_ip() -> str:
    """IP da interface usada para rotas externas (não o loopback)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "N/A"


def get_public_ip(timeout: float = 2.5) -> str:
    """IP público via serviço HTTP leve (somente stdlib)."""
    import urllib.request

    for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ip = resp.read().decode("utf-8", "ignore").strip()
                if ip:
                    return ip
        except Exception:
            continue
    return "N/A (offline?)"


def collect(probe_public_ip: bool = True, sections=None) -> dict:
    """Reúne o dossiê do host num dicionário serializável.

    Apenas as ``sections`` solicitadas são sondadas — assim um run filtrado
    (``-s host``) ou em watch mode não paga por lookups de IP público ou pelo
    sampling de CPU/processos cujos dados seriam descartados. ``None`` coleta
    tudo. A seção ``host`` é sempre incluída (é barata e identifica o dossiê).
    """
    want = set(ALL_SECTIONS if sections is None else sections)
    data: dict = {}

    # --- Identidade / SO --------------------------------------------------- #
    boot_ts = psutil.boot_time() if _HAS_PSUTIL else None
    data["host"] = {
        "user": getpass.getuser(),
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
        "os": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or platform.machine(),
        "python": platform.python_version(),
        "pid": os.getpid(),
        "boot_time": (
            _dt.datetime.fromtimestamp(boot_ts).strftime("%Y-%m-%d %H:%M:%S")
            if boot_ts else "N/A"
        ),
        "uptime": _uptime_string(boot_ts) if boot_ts else "N/A",
    }

    # --- CPU --------------------------------------------------------------- #
    cpu: dict = {}
    if "cpu" in want and _HAS_PSUTIL:
        freq = psutil.cpu_freq()
        try:
            load = os.getloadavg()
        except (OSError, AttributeError):
            load = None
        cpu = {
            "usage_total": psutil.cpu_percent(interval=0.4),
            "per_core": psutil.cpu_percent(interval=0.4, percpu=True),
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
            "freq_current": getattr(freq, "current", None),
            "freq_max": getattr(freq, "max", None),
            "load_avg": list(load) if load else None,
        }
    data["cpu"] = cpu

    # --- Memória ----------------------------------------------------------- #
    mem: dict = {}
    if "memory" in want and _HAS_PSUTIL:
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        mem = {
            "total": vm.total, "available": vm.available,
            "used": vm.used, "percent": vm.percent,
            "swap_total": sm.total, "swap_used": sm.used,
            "swap_percent": sm.percent,
        }
    data["memory"] = mem

    # --- Discos ------------------------------------------------------------ #
    disks = []
    if "disks" in want and _HAS_PSUTIL:
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                continue
            disks.append({
                "device": part.device,
                "mount": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "used": usage.used,
                "percent": usage.percent,
            })
    data["disks"] = disks

    # --- Rede -------------------------------------------------------------- #
    net: dict = {"local_ip": "(pulado)", "public_ip": "(pulado)",
                 "interfaces": [], "connections": None}
    if "network" in want:
        net["local_ip"] = get_real_ip()
        net["public_ip"] = get_public_ip() if probe_public_ip else "(pulado)"
    if "network" in want and _HAS_PSUTIL:
        stats = psutil.net_if_stats()
        for name, addrs in psutil.net_if_addrs().items():
            iface = {"name": name, "up": False, "ipv4": [], "ipv6": [], "mac": None}
            st = stats.get(name)
            if st:
                iface["up"] = st.isup
                iface["speed"] = st.speed
            for a in addrs:
                if a.family == socket.AF_INET:
                    iface["ipv4"].append(a.address)
                elif a.family == socket.AF_INET6:
                    iface["ipv6"].append(a.address.split("%")[0])
                elif getattr(psutil, "AF_LINK", None) and a.family == psutil.AF_LINK:
                    iface["mac"] = a.address
            net["interfaces"].append(iface)
        try:
            conns = psutil.net_connections(kind="inet")
            net["connections"] = {
                "total": len(conns),
                "established": sum(1 for c in conns if c.status == "ESTABLISHED"),
                "listening": sum(1 for c in conns if c.status == "LISTEN"),
            }
        except (psutil.AccessDenied, PermissionError):
            net["connections"] = None
    data["network"] = net

    # --- Bateria / sensores ------------------------------------------------ #
    sensors: dict = {"battery": None, "temps": None}
    if "sensors" in want and _HAS_PSUTIL:
        try:
            bat = psutil.sensors_battery()
            if bat is not None:
                sensors["battery"] = {
                    "percent": round(bat.percent, 1),
                    "plugged": bat.power_plugged,
                    "secsleft": bat.secsleft,
                }
        except Exception:
            pass
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                flat = {}
                for chip, entries in temps.items():
                    for e in entries:
                        if e.current:
                            flat[f"{chip}/{e.label or 'core'}"] = e.current
                sensors["temps"] = flat or None
        except Exception:
            pass
    data["sensors"] = sensors

    # --- Top processos ----------------------------------------------------- #
    procs = []
    if "processes" in want and _HAS_PSUTIL:
        snapshot = []
        for p in psutil.process_iter(["pid", "name", "username"]):
            try:
                p.cpu_percent(None)
                snapshot.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        time.sleep(0.4)
        scored = []
        for p in snapshot:
            try:
                scored.append((
                    p.cpu_percent(None),
                    p.memory_percent(),
                    p.info["pid"],
                    (p.info["name"] or "?")[:22],
                    p.info.get("username") or "?",
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        scored.sort(key=lambda r: r[0], reverse=True)
        for cpu_p, mem_p, pid, name, user in scored[:6]:
            procs.append({
                "pid": pid, "name": name, "user": user,
                "cpu": round(cpu_p, 1), "mem": round(mem_p, 1),
            })
    data["processes"] = procs

    data["meta"] = {
        "tool_version": __version__,
        "captured_at": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "psutil": _HAS_PSUTIL,
    }
    return data


# --------------------------------------------------------------------------- #
#  Renderização                                                               #
# --------------------------------------------------------------------------- #

def _secs_to_hm(secs) -> str:
    if secs is None or secs < 0:
        return "—"
    h, rem = divmod(int(secs), 3600)
    m, _ = divmod(rem, 60)
    return f"{h}h{m:02d}m"


def render(data: dict, sections=ALL_SECTIONS) -> str:
    w = _term_width()
    out = [_banner()]
    meta = data["meta"]
    sub = (
        f"  v{meta['tool_version']}  ·  {meta['captured_at']}  ·  "
        f"engine: {'psutil' if meta['psutil'] else 'stdlib-only'}"
    )
    out.append(C.paint(sub, C.DIM + C.DGREEN))
    if not meta["psutil"]:
        out.append(C.paint("  [!] psutil ausente — instale com `pip install psutil` "
                           "para inteligência completa.", C.AMBER))
    out.append("")

    if "host" in sections:
        h = data["host"]
        out.append(_section("HOST / SISTEMA", w))
        out.append(_row("Operador", f"{h['user']}@{h['hostname']}", w))
        out.append(_row("SO", f"{h['os']} {h['release']}", w))
        out.append(_row("Kernel", h["version"], w))
        out.append(_row("Arquitetura", f"{h['machine']} ({h['processor']})", w))
        out.append(_row("FQDN", h["fqdn"], w))
        out.append(_row("Boot", h["boot_time"], w))
        out.append(_row("Uptime", h["uptime"], w))
        out.append(_row("Python/PID", f"{h['python']}  ·  pid {h['pid']}", w))
        out.append("")

    if "cpu" in sections and data["cpu"]:
        c = data["cpu"]
        out.append(_section("CPU", w))
        bar_w = max(10, w - 30)
        out.append(_row("Uso global",
                        f"{_gauge(c['usage_total'], bar_w)} {c['usage_total']:5.1f}%", w))
        out.append(_row("Núcleos",
                        f"{c['cores_physical']} físicos / {c['cores_logical']} lógicos", w))
        if c.get("freq_current"):
            fr = f"{c['freq_current']:.0f} MHz"
            if c.get("freq_max"):
                fr += f"  (max {c['freq_max']:.0f} MHz)"
            out.append(_row("Frequência", fr, w))
        if c.get("load_avg"):
            la = "  ".join(f"{x:.2f}" for x in c["load_avg"])
            out.append(_row("Load (1/5/15)", la, w))
        per = c.get("per_core") or []
        if per:
            mini_w = max(6, (w - 20) // max(1, len(per)) - 8)
            for i, usage in enumerate(per):
                out.append(_row(f"  core {i}",
                                f"{_gauge(usage, mini_w)} {usage:5.1f}%", w, key_w=16))
        out.append("")

    if "memory" in sections and data["memory"]:
        m = data["memory"]
        out.append(_section("MEMÓRIA", w))
        bar_w = max(10, w - 30)
        out.append(_row("RAM",
                        f"{_gauge(m['percent'], bar_w)} {m['percent']:5.1f}%", w))
        out.append(_row("Total",
                        f"{_human_bytes(m['used'])} / {_human_bytes(m['total'])} usados", w))
        out.append(_row("Disponível", _human_bytes(m["available"]), w))
        if m["swap_total"]:
            out.append(_row("Swap",
                            f"{_gauge(m['swap_percent'], bar_w)} {m['swap_percent']:5.1f}%", w))
            out.append(_row("Swap uso",
                            f"{_human_bytes(m['swap_used'])} / {_human_bytes(m['swap_total'])}", w))
        out.append("")

    if "disks" in sections and data["disks"]:
        out.append(_section("ARMAZENAMENTO", w))
        bar_w = max(8, w - 40)
        for d in data["disks"]:
            out.append(_row(d["mount"] or d["device"],
                            f"{_gauge(d['percent'], bar_w)} {d['percent']:5.1f}%", w))
            out.append(_row("",
                            f"{_human_bytes(d['used'])} / {_human_bytes(d['total'])}  "
                            f"[{d['fstype']}]", w))
        out.append("")

    if "network" in sections:
        n = data["network"]
        out.append(_section("REDE", w))
        out.append(_row("IP local", n["local_ip"], w))
        out.append(_row("IP público", n["public_ip"], w))
        if n.get("connections"):
            cc = n["connections"]
            out.append(_row("Conexões",
                            f"{cc['total']} totais · {cc['established']} ESTAB · "
                            f"{cc['listening']} LISTEN", w))
        for iface in n["interfaces"]:
            if iface["name"] == "lo" or iface["name"].startswith("lo"):
                continue
            ips = ", ".join(iface["ipv4"]) or "—"
            state = C.paint("UP", C.GREEN) if iface["up"] else C.paint("DOWN", C.RED)
            label = f"{iface['name']} [{state}]"
            out.append(_row(label, ips, w))
            if iface.get("mac"):
                out.append(_row("", f"MAC {iface['mac']}", w))
        out.append("")

    if "sensors" in sections:
        s = data["sensors"]
        if s.get("battery") or s.get("temps"):
            out.append(_section("SENSORES", w))
            if s.get("battery"):
                b = s["battery"]
                plug = "AC ligado" if b["plugged"] else "bateria"
                eta = "" if b["plugged"] else f"  ·  ~{_secs_to_hm(b['secsleft'])} restantes"
                bar_w = max(10, w - 34)
                out.append(_row("Bateria",
                                f"{_gauge(b['percent'], bar_w)} {b['percent']:5.1f}%", w))
                out.append(_row("Status", f"{plug}{eta}", w))
            if s.get("temps"):
                for label, val in list(s["temps"].items())[:6]:
                    out.append(_row(label[:16], f"{val:.1f} °C", w))
            out.append("")

    if "processes" in sections and data["processes"]:
        out.append(_section("TOP PROCESSOS  (cpu%)", w))
        header = f"  {'PID':>7}  {'CPU%':>6} {'MEM%':>6}  {'USER':<10} NAME"
        out.append(C.paint(header, C.DGREEN))
        for p in data["processes"]:
            line = (f"  {p['pid']:>7}  {p['cpu']:>6.1f} {p['mem']:>6.1f}  "
                    f"{p['user'][:10]:<10} {p['name']}")
            out.append(C.paint(line, C.WHITE))
        out.append("")

    out.append(C.paint("─" * w, C.DGREEN))
    out.append(C.paint("  [ end of transmission ]", C.DIM + C.DGREEN))
    return "\n".join(out)


# --------------------------------------------------------------------------- #
#  CLI                                                                         #
# --------------------------------------------------------------------------- #

def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="system_info.py",
        description="Recon-grade host profiler — inteligência de sistema estilo hacker.",
    )
    p.add_argument("--no-color", action="store_true", help="desliga cores ANSI")
    p.add_argument("--json", action="store_true", help="emite o dossiê em JSON")
    p.add_argument("--no-net", action="store_true",
                   help="não consulta o IP público (modo offline/rápido)")
    p.add_argument("-w", "--watch", action="store_true",
                   help="refresh contínuo da tela")
    p.add_argument("-i", "--interval", type=float, default=2.0,
                   metavar="SEG", help="intervalo do watch em segundos (padrão 2)")
    p.add_argument("-s", "--sections", type=str, default=None,
                   metavar="LISTA",
                   help="seções separadas por vírgula: " + ",".join(ALL_SECTIONS))
    p.add_argument("--version", action="version",
                   version=f"system-intel {__version__}")
    return p.parse_args(argv)


def _resolve_sections(spec):
    if not spec:
        return ALL_SECTIONS
    chosen = [s.strip().lower() for s in spec.split(",") if s.strip()]
    valid = [s for s in chosen if s in ALL_SECTIONS]
    return tuple(valid) if valid else ALL_SECTIONS


def main(argv=None) -> int:
    args = _parse_args(argv)

    if args.no_color or not sys.stdout.isatty():
        C.disable()

    sections = _resolve_sections(args.sections)
    probe_pub = not args.no_net

    if args.json:
        data = collect(probe_public_ip=probe_pub, sections=sections)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    if args.watch:
        try:
            while True:
                data = collect(probe_public_ip=probe_pub, sections=sections)
                sys.stdout.write("\033[2J\033[H")  # limpa tela
                print(render(data, sections))
                print(C.paint(f"\n  ↻ atualizando a cada {args.interval}s "
                             f"— Ctrl-C para sair", C.DIM + C.CYAN))
                time.sleep(max(0.5, args.interval))
        except KeyboardInterrupt:
            print(C.paint("\n  [✓] sessão encerrada.", C.GREEN))
            return 0

    data = collect(probe_public_ip=probe_pub, sections=sections)
    print(render(data, sections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
