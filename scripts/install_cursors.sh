#!/usr/bin/env bash
set -e

info "Installing Cursor Themes"
debug "Setting Up Dirs"
mkdir -p ~/.local/share/icons/
ln -s ~/.local/share/icons/ ~/.icons
debug "Copying Cursor"
cp -r ./resources/miku-cursor-linux ~/.local/share/icons
debug "Setting Default Cursor Theme"
mkdir -p ~/.local/share/icons/default
echo "[Icon Theme]
Inherits=miku_theme" > ~/.local/share/icons/default/index.theme
info "Cursor Theme Set, enjoy the miku"