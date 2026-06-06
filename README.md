# 🔍 System Info Tool

Uma ferramenta de linha de comando para exibir informações detalhadas do sistema, otimizada para **desktop e dispositivos móveis** (Termux no Android, iSH no iOS).

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Funcionalidades

- 🖥️ **Sistema operacional** (usuário, hostname, kernel, arquitetura, tempo de inicialização)
- 🧠 **CPU** (uso percentual, frequência, número de núcleos)
- 💾 **Memória RAM e Swap** (total, disponível, uso em GB)
- 💿 **Discos e partições** (capacidade, uso, ponto de montagem)
- 🌐 **Rede** (IP local, IP público, interfaces ativas)
- 🔋 **Bateria** (percentual, tempo restante, status de carga)
- ⚙️ **Top processos** (5 mais intensivos em CPU)
- 📱 **Interface responsiva** – adapta automaticamente a largura do terminal para celular
- 🎨 **Cores ANSI** (opcionais, podem ser desligadas)
- ♻️ **Loop interativo** – atualize com Enter, saia com Q

## 📦 Requisitos

- Python 3.7 ou superior
- Pip (gerenciador de pacotes)

## 🚀 Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/system-info-tool.git
cd system-info-tool

# Instale a dependência
pip install -r requirements.txt