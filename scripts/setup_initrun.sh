#!/usr/bin/env bash
set -e

cp -rn ./configs/* "${XDG_CONFIG_HOME}"\
cp -r ~/wallpapers ~/.Pictures
awww img ~/Pictures/wallpapers/910141.jpg
~/.config/hypr/scripts/WallustSwww.sh ~/Pictures/wallpapers/910141.jpg
ln -s ~/.cache/wal/colors-hyprland.conf ~/.config/hypr/wallust/wallust-hyprland.conf
ln -s ~/.cache/wal/colors-kitty.conf ~/.config/kitty/kitty-themes/02-pywal_8.con
ln -s ~/.cache/wal/pywal.kvconfig ~/.config/Kvantum/Pywal/Pywal.kvconfig
ln -s ~/.cache/wal/pywal.svg ~/.config/kitty/Pywal/Pywal.svg
ln -s ~/Pictures/wallpapers/910141.jpg ~/.config/rofi/.current_wallpaper
ln -s ~/.cache/wal/colors-rofi.rasi  ~/.config/rofi/wallust/colors-rofi.rasi
ln -s ~/.cache/wal/colors-waybar.css ~/.config/waybar/wallust/colors-waybar.css
