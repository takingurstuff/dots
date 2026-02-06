#!/usr/bin/env bash
set -e

PACKAGES=("qt6-svg" "qt6-virtualkeyboard" "qt6-multimedia-ffmpeg") 

info "Setting Up SDDM and Theme"

info "Installing SDDM"
install-system sddm
info "Installing SDDM theme deps"
install_package_list 

info "Setting up SDDM theme (requires sudo)"
info "Cloning Theme Dir"
sudo true
sudo git clone -b master --depth 1 https://github.com/keyitdev/sddm-astronaut-theme.git /usr/share/sddm/themes/sddm-astronaut-theme
info "Writing SDDM configs"
debug "Copying Fonts"
sudo cp -r /usr/share/sddm/themes/sddm-astronaut-theme/Fonts/* /usr/share/fonts/
debug "Writing SDDM theme pointer"
echo "[Theme]
Current=sddm-astronaut-theme" | sudo tee /etc/sddm.conf
debug "Writing Virtual Keyboard Config"
echo "[General]
InputMethod=qtvirtualkeyboard" | sudo tee /etc/sddm.conf.d/virtualkbd.conf
debug "Creating Wallpaper Cache"
mkdir /var/cache/sddm-assets
chmod 755 /var/cache/sddm-assets
chown talent:root /var/cache/sddm-assets
debug "Setting Wallpaper In Config"
sudo sed -i 's|Background=".*"|Background="/var/cache/sddm-assets/wall"|' /usr/share/sddm/themes/sddm-astronaut-theme/Themes/astronaut.conf
info "SDDM has been set up"
