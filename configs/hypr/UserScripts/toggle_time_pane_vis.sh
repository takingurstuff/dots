#!/bin/bash

windows_open=$(eww active-windows | grep time_window)

has_window=$?

if [[ $has_window -ne 0 ]]; then
  eww open time_window >/dev/null
else
  eww close time_window >/dev/null
fi

