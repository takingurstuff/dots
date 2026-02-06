#!/usr/bin/env bash
set -e

info "Setting Up User Services"
mkdir -p ~/.config/systemd/user
cp -r ./services/* ~/services
cp ./systemd-units/* ~/.config/systemd/user
systemctl --user daemon-reload
systemctl --user enable bgutil.service
systemctl --user enable eye-break.timer
systemctl --user enable l2drepo.service
systemctl --user enable mpris-daemon.service
systemctl --user start bgutil.service
systemctl --user start eye-break.timer
systemctl --user start l2drepo.service
systemctl --user start mpris-daemon.service
info "User Services Set Up"

