#!/bin/bash

get_active_player() {
  playerctl -l 2>&1 | head -n 1
}

main() {
  while true; do
    player=$(get_active_player)
    if [[ "$player" == "No players found" ]]; then
      windows_open=$(eww active-windows | grep player_status)
      if [[ $? -ne 0 ]]; then
        :
      else
        eww close player_status
      fi
    else
      windows_open=$(eww active-windows | grep player_status)
      if [[ $? -eq 0 ]]; then
        :
      else
        eww open player_status
      fi
    fi
    sleep 1
  done
}

while true; do
  main
  sleep 1
done