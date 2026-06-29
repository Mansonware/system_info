```
   ___ ___  _____ _____ ___ __  __   ___ _  _ _____ ___ _
  / __/ _ \|_   _|_   _| __|  \/  | |_ _| \| |_   _| __| |
  \__ \ (_) | | |   | | | _|| |\/| |  | || .` | | | | _|| |__
  |___/\___/  |_|   |_| |___|_|  |_| |___|_|\_| |_| |___|____|
         r e c o n - g r a d e   h o s t   p r o f i l e r
```

# 🛰️ System Intelligence Tool

Perfilador de host **estilo terminal hacker** com profundidade real de
reconhecimento. Coleta e correlaciona inteligência do sistema — identidade,
kernel, CPU por núcleo, memória/swap, armazenamento, rede (interfaces + IP
público + conexões ativas), bateria e sensores térmicos — e renderiza tudo
num painel ANSI fosforado, **responsivo para desktop e mobile** (Termux no
Android, iSH no iOS).

![Python](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Deps](https://img.shields.io/badge/deps-psutil%20(opcional)-lightgrey)

---

## ✨ Capacidades de inteligência

| Módulo            | O que é extraído |
|-------------------|------------------|
| 🖥️ **Host / SO**   | operador, hostname, FQDN, kernel, arquitetura, boot time, **uptime** |
| 🧠 **CPU**         | uso global **e por núcleo**, frequência atual/máx, núcleos físicos/lógicos, **load average** |
| 💾 **Memória**     | RAM e **Swap** (total, usado, disponível) com barras de severidade |
| 💿 **Armazenamento** | todas as partições montadas: capacidade, uso, filesystem |
| 🌐 **Rede**        | IP local, **IP público**, interfaces (IPv4/IPv6/MAC, estado UP/DOWN), **contagem de conexões** (ESTABLISHED / LISTEN) |
| 🔋 **Sensores**    | bateria (%, status AC, tempo restante) e **temperaturas** térmicas |
| ⚙️ **Processos**   | top 6 por CPU, com PID, usuário, CPU% e MEM% |

Recursos da camada de apresentação:

- 🎨 **Cores ANSI** estilo fósforo-verde com **barras de severidade** (verde → âmbar → vermelho).
- 📱 **Layout responsivo** — adapta a largura à coluna do terminal (ideal p/ celular).
- ♻️ **Watch mode** — refresh contínuo da tela (`--watch`).
- 🧾 **Export JSON** — despeja o dossiê completo para pipelines/automação (`--json`).
- 🎯 **Seleção de seções** — colete só o que importa (`-s cpu,net`).
- 🛡️ **Degradação graciosa** — roda sem `psutil` (modo somente-stdlib) e sem cores quando a saída não é um TTY.

---

## 📦 Requisitos

- Python **3.7+**
- `psutil` (opcional, mas recomendado — habilita a inteligência completa)

## 🚀 Instalação

```bash
# Clone o repositório
git clone https://github.com/Mansonware/system_info.git
cd system_info

# Instale a dependência opcional
pip install -r requirements.txt
```

## ⚡ Uso

```bash
python3 system_info.py                 # snapshot completo, colorido
python3 system_info.py --no-color      # desliga cores ANSI
python3 system_info.py --json          # despeja o dossiê em JSON
python3 system_info.py --watch         # refresh contínuo (Ctrl-C p/ sair)
python3 system_info.py -i 1 --watch    # watch a cada 1 segundo
python3 system_info.py -s cpu,memory   # apenas seções escolhidas
python3 system_info.py --no-net        # pula a consulta de IP público (rápido/offline)
```

### Flags

| Flag                | Efeito |
|---------------------|--------|
| `--no-color`        | desativa as cores ANSI |
| `--json`            | emite a inteligência em JSON (machine-readable) |
| `--no-net`          | não consulta o IP público (modo offline/rápido) |
| `-w`, `--watch`     | refresh contínuo da tela |
| `-i`, `--interval`  | intervalo do watch em segundos (padrão: `2`) |
| `-s`, `--sections`  | lista separada por vírgula: `host,cpu,memory,disks,network,sensors,processes` |
| `--version`         | mostra a versão |

---

## 🧩 Arquitetura

A ferramenta separa **coleta** de **renderização**, o que mantém o código
testável e permite reuso:

- `collect()` → reúne todo o dossiê num `dict` serializável (alimenta `--json`).
- `render()` → transforma o `dict` no painel ANSI responsivo.
- `main()` → camada de CLI (`argparse`), watch loop e roteamento de saída.

Por isso o `--json` e o painel visual consomem **exatamente a mesma fonte de
verdade**.

## 📱 Notas para mobile (Termux / iSH)

- O layout detecta a largura do terminal e encolhe as barras automaticamente.
- Em sandboxes onde `psutil` não pode ser instalado, a ferramenta ainda roda
  em modo somente-stdlib (host + IP local/público).

## 📄 Licença

MIT.
```
  [ end of transmission ]
```
