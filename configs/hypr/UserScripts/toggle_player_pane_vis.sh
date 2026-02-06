#!/bin/bash

script_pid=$(pgrep -f /home/talent/.config/hypr/UserScripts/eww_player_status_auto.sh)

widget_service_started=$?

windows_open=$(eww active-windows | grep player_status)

has_window=$?

if [[ $widget_service_started -ne 0 ]]; then
  nohup "/home/talent/.config/hypr/UserScripts/eww_player_status_auto.sh" >/dev/null 2>&1 &
else
  kill "$script_pid"
  if [[ $has_window -eq 0 ]]; then
    eww close player_status >/dev/null
  fi
fi

