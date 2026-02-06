#!/bin/bash
# /* ---- 💫 https://github.com/JaKooLit 💫 ---- */  ##
# Wallust Colors for current wallpaper

# Define the path to the swww cache directory
cache_dir="$HOME/.cache/awww/0.11.2-master2/"

# Get a list of monitor outputs
monitor_outputs=($(ls "$cache_dir"))

# Initialize a flag to determine if the ln command was executed
ln_success=false

# Get current focused monitor
current_monitor=$(hyprctl monitors | awk '/^Monitor/{name=$2} /focused: yes/{print name}')
echo $current_monitor
# Construct the full path to the cache file
cache_file="$cache_dir$current_monitor"
echo $cache_file
# Check if the cache file exists for the current monitor output
if [ -f "$cache_file" ]; then
    # Get the wallpaper path from the cache file
    wallpaper_path=$(grep -a 'crop.Lanczos3' "$cache_file" | head -n 1 | sed 's/crop.Lanczos3//g')
    echo $wallpaper_path
    # symlink the wallpaper to the location Rofi can access
    if ln -sf "$wallpaper_path" "$HOME/.config/rofi/.current_wallpaper"; then
        ln_success=true  # Set the flag to true upon successful execution
    fi
    # copy the wallpaper for wallpaper effects
	cp -r "$wallpaper_path" "$HOME/.config/hypr/wallpaper_effects/.wallpaper_current"
fi

# Check the flag before executing further commands
if [ "$ln_success" = true ]; then
    # Add back pywal and pywal16 to get appropiate theming
    echo 'about to execute pywal'
    if ! wal --backend haishoku -i "$wallpaper_path" -n -s -t -q; then
        echo "Haishoku failed, falling back to colorz..."
        wal --backend colorthief -i "$wallpaper_path" -n -s -t -q
    fi
    # wal --backend haishoku --cols16 darken -i "$wallpaper_path" -n -s -t -q
    # Execute Themecord
    sleep 1
    echo 'about to execute Themecord'
    walcord
    # Apply Cava colorscheme
    for pid in $(pidof cava); 
    do
        kill -SIGUSR2 $pid
    done
    # Theme firefox
    pywalfox update
    # Theme Kitty
    for pid_kitty in $(pidof kitty); do
	    kill -SIGUSR1 "$pid_kitty"
	done
    touch "$HOME/.config/eww/eww.scss"
    ~/theme_sources/Colloid-gtk-theme/install.sh -t default -c dark --tweaks rimless
    gsettings set org.gnome.desktop.interface gtk-theme "Granite"
    sleep 1
    gsettings set org.gnome.desktop.interface gtk-theme "Colloid-Dark"
    cp "$wallpaper_path" /var/cache/sddm-assets/wall
fi
