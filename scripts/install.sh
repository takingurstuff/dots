#!/usr/bin/env bash
set -e

# Configuration
DEBUG_MODE=true # Set to false to hide debug messages

# Colors
BLACK="\e[0;30m"
BLUE="\e[1;34m"
CYAN="\e[36m"
GREEN="\e[1;32m"
YELLOW="\e[1;33m"
RED="\e[1;31m"
RESET="\e[0m"

# --- Logging Functions ---

debug() {
    if [[ "$DEBUG_MODE" == "true" ]]; then
        echo -e "${BLACK}[DEBUG] $1${RESET}"
    fi
}

info() {
    echo -e "${BLUE}[INFO] ${RESET}$1"
}

warning() {
    echo -e "${YELLOW}[WARN] $1${RESET}"
}

error() {
    echo -e "${RED}[ERROR] $1${RESET}" >&2
}

# --- Script Execution ---

echo -e "${BLACK}"
cat <<'EOF'
                        .__         .__   __
                  ____  |__|___  ___|__|_/  |_   ____
                 /    \ |  |\  \/  /|  |\   __\_/ __ \
                 |  |  \|  | >    < |  | |  |  \  ___/
                 |__|  /|__|/__/\_ \|__| |__|   \___  >
Function Stolen From \/           \/                \/ 
EOF
echo -e "${RESET}"

info "Checking system compatibility..."

if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    if [[ "$ID" != "arch" ]]; then
        error "Incompatible system detected: $ID"
        info "IDK how to deal with other distros"
        exit 1
    fi
    info "Arch Linux detected. Proceeding..."
else
    error "File not found: /etc/os-release"
    info "Are you running Linux?"
    exit 1
fi

install_system() {
    if ! command -v yay &> /dev/null; then
        info "yay not found. Attempting to install from AUR..."
        
        debug "Installing base-devel and git..."
        sudo pacman -S --needed --noconfirm git base-devel
        
        cd /tmp || { error "Failed to enter /tmp"; return 1; }
        
        debug "Cloning yay-bin..."
        git clone https://aur.archlinux.org/yay-bin.git
        
        cd yay-bin || { error "Failed to enter yay-bin directory"; return 1; }
        
        debug "Building and installing package..."
        makepkg -si --needed --noconfirm
        
        info "yay installed successfully."
    fi
    
    info "Installing requested packages: $*"
    yay -S --needed --noconfirm "$@"
}

# Define your package list here
PACKAGES=(
    # Basics
    "zsh" "fastfetch" "nvtop"
    "btop" "fzf" "wget" "curl" "aria2"
    "git" "git-lfs" "lazygit" "podman"
    "cmake" "openssh" "gnupg" "walcord" "awww"

    # Desktop
    "hyprland" "rofi" "waybar" "visual-studio-code-bin"
    "discord" "kitty" "gparted" "firefox"
    # Connectivity & System UIs
    "network-manager-applet" "blueman" "pavucontrol" "brightnessctl" 
    "thunar" "thunar-archive-plugin" "file-roller" "wl-clipboard" 
    "polkit-gnome"
    
    # Langs
    "cmake" "python" "uv" "go" "deno" "nvm" "bun" "rustup"

    # Multimedia
    "gst-libav" "gst-plugins-good" "gst-plugins-bad" "gst-plugins-ugly"
    "libdca" "libmad" "libvorbis" "opus" "libwebp" "libheif" "dav1d" "flac"
    "ffmpeg" "mpv" "mpd"

    # Vapoursynth stuff
    "ffms2" "vapoursynth-plugin-awarpsharp2-git" "vapoursynth-plugin-bilateral-git"
    "vapoursynth-plugin-bm3d-git" "vapoursynth-plugin-cas-git" "vapoursynth-plugin-ctmf-git"
    "vapoursynth-plugin-descale-git" "vapoursynth-plugin-dfttest-git" 
    "vapoursynth-plugin-eedi2-git" "vapoursynth-plugin-f3kdb-git" "vapoursynth-plugin-fmtconv"
    "vapoursynth-plugin-havsfunc" "vapoursynth-plugin-knlmeanscl-git" "vapoursynth-plugin-misc-git"
    "vapoursynth-plugin-muvsfunc-git" "vapoursynth-plugin-mvsfunc-git" "vapoursynth-plugin-mvtools" 
    "vapoursynth-plugin-neo_f3kdb-git" "vapoursynth-plugin-nnedi3-git" 
    "vapoursynth-plugin-nnedi3_resample-git" "vapoursynth-plugin-nnedi3_weights_bin" 
    "vapoursynth-plugin-removegrain-git" "vapoursynth-plugin-resize2-git" "vapoursynth-plugin-sangnom-git" 
    "vapoursynth-plugin-tcanny-git" "vapoursynth-plugin-temporalmedian-git" "vapoursynth-plugin-vsakarin-git" 
    "vapoursynth-plugin-vsbasicvsrpp-git" "vapoursynth-plugin-vsjetpack" "vapoursynth-plugin-vsutil-git" 
    "vapoursynth-plugin-vszip" "vapoursynth-plugin-zsmooth" "vapoursynth"

    # Python Data / ML Libs:
    "python-pytorch" "python-torchvision" "python-numpy" "python-pandas"
    "python-scipy" "python-numba" "python-cupy" "tensorrt" "python-nvmath"

    # Python General:
    "python-pywal16" "python-haishoku" "python-colorthief" "python-pywalfox"
    "python-rich" "python-mutagen" "python-av" "python-opencv" "python-pillow"
    "python-pipx" "python-dbus-next"

    # Printing:
    "cups" "system-config-printer" "avahi" "nss-mdns" "ghostscript" "cups-pdf"
)
# Function to process the installation loop
install_package_list() {
    if [[ ${#PACKAGES[@]} -eq 0 ]]; then
        warning "Package array is empty. Nothing to install."
        return
    fi

    info "Starting installation of ${#PACKAGES[@]} packages..."

    for PKG in "${PACKAGES[@]}"; do
        debug "Processing package: $PKG"
        
        # Calling your existing install_system function
        if [[ "$DEBUG_MODE" == "true" ]]; then
            if install_system "$PKG"; then
                info "Successfully processed: $PKG"
            else
                error "Failed to install: $PKG"
            fi
        else
            debug "Supposed to install: $PKG"
        fi

    done

    info "Installation process complete."
}

export -f install_system
export -f install_package_list
export -f debug
export -f info
export -f warning
export -f error
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:=$HOME/.config}"
export REPO_DIR="$(pwd)"

# Execute the loop
install_package_list

info "initalizing nvm"
nvm install node
info "nvm intialized"

info "preparing home dir for user services"
info "making services dir"
mkdir ~/services
info "home dir setup complete"

info "preparing home dir for themes"
info "creating theme sources dir"
mkdir ~/theme_sources
info "theme sources dir created"

info "Installing Components"
./install_cursors.sh
./install_ytdl.sh
./install_sddm.sh
./setup_services.sh
./setup_initrun.sh
info "Components Installed"

info "Setup Done"