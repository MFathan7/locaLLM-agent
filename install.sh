#!/usr/bin/env bash
# ==============================================================================
#  ✦  locaLLM Installer for Linux & macOS  ✦
#  Autonomous Local AI Platform powered by Ollama and OpenAI-compatible engines
# ==============================================================================

set -e

# --- Visual Styling & ANSI Colors ---
if [ -t 1 ]; then
    CYAN="\033[38;2;0;215;255m"
    GREEN="\033[38;2;0;255;135m"
    YELLOW="\033[38;2;255;215;0m"
    RED="\033[38;2;255;95;95m"
    DIM="\033[38;2;170;170;170m"
    BOLD="\033[1m"
    RESET="\033[0m"
else
    CYAN=""
    GREEN=""
    YELLOW=""
    RED=""
    DIM=""
    BOLD=""
    RESET=""
fi

log_step() {
    echo -e "${CYAN}==>${RESET} ${BOLD}$1${RESET}"
}

log_sub() {
    echo -e "  ${DIM}•${RESET} $1"
}

log_success() {
    echo -e "  ${GREEN}✔${RESET} $1"
}

log_warning() {
    echo -e "  ${YELLOW}▲${RESET} ${YELLOW}$1${RESET}"
}

log_error() {
    echo -e "  ${RED}✖${RESET} ${RED}$1${RESET}" >&2
}

# --- Resolve Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
LOCAL_BIN="$HOME/.local/bin"

# --- Header Banner ---
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                      ✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ   ɪ ɴ s ᴛ ᴀ ʟ ʟ ᴇ ʀ  ✦                 ║"
echo "║                  Autonomous Local AI Platform Setup                         ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# --- Flags & Arguments ---
REINSTALL_VENV=0
SKIP_GLOBAL_BIN=0

for arg in "$@"; do
    case "$arg" in
        --reinstall|-r)
            REINSTALL_VENV=1
            ;;
        --skip-global|-s)
            SKIP_GLOBAL_BIN=1
            ;;
        --help|-h)
            echo "Usage: ./install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --reinstall, -r    Recreate .venv virtual environment from scratch"
            echo "  --skip-global, -s  Skip creating ~/.local/bin/locallm symlink/wrapper"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            log_warning "Unrecognized argument: $arg (ignoring)"
            ;;
    esac
done

# --- 1. Detect Operating System & Architecture ---
log_step "Detecting Operating System & Architecture..."

OS_TYPE="$(uname -s)"
ARCH_TYPE="$(uname -m)"
DISTRO_NAME="Unknown"

if [ "$OS_TYPE" = "Linux" ]; then
    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        DISTRO_NAME="${NAME:-Linux}"
    fi
    log_success "Operating System: Linux ($DISTRO_NAME) [$ARCH_TYPE]"
elif [ "$OS_TYPE" = "Darwin" ]; then
    DISTRO_NAME="macOS $(sw_vers -productVersion 2>/dev/null || echo '')"
    log_success "Operating System: $DISTRO_NAME [$ARCH_TYPE]"
else
    log_warning "Operating System: $OS_TYPE (untested, proceeding anyway)"
fi

# --- 2. Find and Validate Python (>= 3.9) ---
log_step "Checking Python 3 environment..."

find_python() {
    for cmd in python3 python python3.14 python3.13 python3.12 python3.11 python3.10 python3.9; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD="$(find_python || true)"

if [ -z "$PYTHON_CMD" ]; then
    log_error "Python 3.9 or higher is required but was not found."
    echo ""
    echo -e "${BOLD}Recommended installation steps:${RESET}"
    if [[ "$DISTRO_NAME" =~ (Arch|Manjaro|Endeavour) ]]; then
        echo -e "  ${CYAN}sudo pacman -S python python-pip python-virtualenv${RESET}"
    elif [[ "$DISTRO_NAME" =~ (Ubuntu|Debian|Mint|Pop) ]]; then
        echo -e "  ${CYAN}sudo apt update && sudo apt install -y python3 python3-venv python3-pip${RESET}"
    elif [[ "$DISTRO_NAME" =~ (Fedora|CentOS|RHEL) ]]; then
        echo -e "  ${CYAN}sudo dnf install -y python3 python3-pip${RESET}"
    elif [ "$OS_TYPE" = "Darwin" ]; then
        echo -e "  ${CYAN}brew install python${RESET}"
    fi
    exit 1
fi

PYTHON_VERSION="$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
log_success "Found Python: $($PYTHON_CMD -c 'import sys; print(sys.executable)') (v$PYTHON_VERSION)"

# --- 3. Virtual Environment Setup ---
log_step "Setting up virtual environment in .venv..."

if [ "$REINSTALL_VENV" -eq 1 ] && [ -d "$VENV_DIR" ]; then
    log_sub "Removing existing virtual environment (--reinstall requested)..."
    rm -rf "$VENV_DIR"
fi

if [ ! -d "$VENV_DIR" ] || [ ! -x "$VENV_DIR/bin/python" ]; then
    log_sub "Creating virtual environment at $VENV_DIR..."
    if ! "$PYTHON_CMD" -m venv "$VENV_DIR"; then
        log_error "Failed to create virtual environment."
        if [[ "$DISTRO_NAME" =~ (Arch|Manjaro|Endeavour) ]]; then
            echo -e "  Try running: ${CYAN}sudo pacman -S python-virtualenv${RESET}"
        elif [[ "$DISTRO_NAME" =~ (Ubuntu|Debian|Mint|Pop) ]]; then
            echo -e "  Try running: ${CYAN}sudo apt install -y python3-venv${RESET}"
        fi
        exit 1
    fi
    log_success "Virtual environment created."
else
    log_success "Existing virtual environment found."
fi

VENV_PYTHON="$VENV_DIR/bin/python"

# Bootstrap pip if missing in venv (common in Arch Linux & minimal installations)
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
    log_sub "Bootstrapping pip via ensurepip..."
    "$VENV_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
fi

# Ensure pip is working
if ! "$VENV_PYTHON" -m pip --version >/dev/null 2>&1; then
    log_error "pip could not be initialized inside the virtual environment."
    if [[ "$DISTRO_NAME" =~ (Arch|Manjaro|Endeavour) ]]; then
        echo -e "  Try: ${CYAN}sudo pacman -S python-pip${RESET} then re-run ./install.sh"
    fi
    exit 1
fi

PIP_VER="$("$VENV_PYTHON" -m pip --version | awk '{print $2}')"
log_success "pip is ready (v$PIP_VER)"

# --- 4. Install Dependencies & locaLLM Package ---
log_step "Installing project dependencies & registering editable package..."

log_sub "Upgrading build tools (pip, setuptools, wheel)..."
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel --quiet

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    log_sub "Installing requirements from requirements.txt..."
    "$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
    log_success "Dependencies installed."
fi

log_sub "Installing locaLLM in editable mode ('pip install -e .')..."
"$VENV_PYTHON" -m pip install -e "$SCRIPT_DIR" --quiet
log_success "locaLLM package registered."

# --- 5. Setup Local Runner Script ---
log_step "Configuring executable runners..."

chmod +x "$SCRIPT_DIR/locallm.sh" 2>/dev/null || true
log_success "Local runner ready: ./locallm.sh"

# --- 6. Setup Global CLI Command in ~/.local/bin ---
if [ "$SKIP_GLOBAL_BIN" -eq 0 ]; then
    mkdir -p "$LOCAL_BIN"

    # Wrapper script that activates and executes directly from venv
    cat <<EOF > "$LOCAL_BIN/locallm"
#!/usr/bin/env bash
# locaLLM Global CLI Launcher
exec "$VENV_DIR/bin/locallm" "\$@"
EOF
    chmod +x "$LOCAL_BIN/locallm"

    # Also provide capital alias 'locaLLM'
    ln -sf "$LOCAL_BIN/locallm" "$LOCAL_BIN/locaLLM"

    log_success "Global CLI launcher installed to $LOCAL_BIN/locallm"

    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        log_warning "$LOCAL_BIN is not currently in your PATH environment variable."
        echo -e "  ${DIM}To use 'locallm' from any terminal directory, add this to your shell config:${RESET}"
        if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
            echo -e "    ${CYAN}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc${RESET}"
        elif [ -f "$HOME/.bashrc" ]; then
            echo -e "    ${CYAN}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc${RESET}"
        elif [ -f "$HOME/.config/fish/config.fish" ]; then
            echo -e "    ${CYAN}fish_add_path ~/.local/bin${RESET}"
        fi
    else
        log_success "$LOCAL_BIN is already in your PATH."
    fi
fi

# --- 7. Check Ollama & Backend Status ---
log_step "Checking local Ollama service status..."

if command -v ollama >/dev/null 2>&1; then
    OLLAMA_VER="$(ollama --version 2>/dev/null || echo 'installed')"
    log_success "Ollama binary found: $OLLAMA_VER"

    if curl -s --max-time 1.5 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        log_success "Ollama daemon is ONLINE and responding at http://127.0.0.1:11434"
    else
        log_warning "Ollama daemon is currently stopped."
        echo -e "  ${DIM}Start Ollama with:${RESET}"
        if [[ "$DISTRO_NAME" =~ (Arch|Manjaro|Endeavour) ]]; then
            echo -e "    ${CYAN}systemctl --user start ollama${RESET} (or ${CYAN}sudo systemctl start ollama${RESET})"
        elif [ "$OS_TYPE" = "Linux" ]; then
            echo -e "    ${CYAN}sudo systemctl start ollama${RESET} (or run: ${CYAN}locallm start${RESET})"
        else
            echo -e "    ${CYAN}ollama serve${RESET} (or launch Ollama application)"
        fi
    fi
else
    log_warning "Ollama was not detected on this system."
    echo -e "  ${DIM}To install Ollama:${RESET}"
    if [[ "$DISTRO_NAME" =~ (Arch|Manjaro|Endeavour) ]]; then
        echo -e "    ${CYAN}sudo pacman -S ollama${RESET} (or curl -fsSL https://ollama.com/install.sh | sh)"
    elif [ "$OS_TYPE" = "Linux" ]; then
        echo -e "    ${CYAN}curl -fsSL https://ollama.com/install.sh | sh${RESET}"
    else
        echo -e "    ${CYAN}brew install --cask ollama${RESET} (or download from https://ollama.com/download)"
    fi
fi

# --- 8. Complete & Quickstart Guide ---
echo ""
echo -e "${GREEN}==============================================================================${RESET}"
echo -e "${GREEN}✦  locaLLM installation completed successfully!  ✦${RESET}"
echo -e "${GREEN}==============================================================================${RESET}"
echo ""
echo -e "${BOLD}Quick Ways to Run locaLLM:${RESET}"
echo -e "  1. Global command:    ${CYAN}locallm${RESET}  or  ${CYAN}locaLLM${RESET}"
echo -e "  2. Repository runner: ${CYAN}./locallm.sh${RESET}"
echo -e "  3. Manual activation: ${CYAN}source .venv/bin/activate && locallm${RESET}"
echo ""
echo -e "${BOLD}Useful Commands:${RESET}"
echo -e "  ${CYAN}locallm${RESET}               Launch interactive menu with live telemetry banner"
echo -e "  ${CYAN}locallm top${RESET}           Open real-time GPU VRAM HUD & hardware monitor"
echo -e "  ${CYAN}locallm chat${RESET}          Interactive conversational chat with auto-routing"
echo -e "  ${CYAN}locallm status${RESET}        Check inference backend connectivity & VRAM fit"
echo -e "  ${CYAN}locallm --help${RESET}        Display full CLI guide and documentation"
echo ""
