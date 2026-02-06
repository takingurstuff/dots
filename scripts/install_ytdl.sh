#!/usr/bin/env bash
set -e

info "Installing yt-dlp"
install-system yt-dlp

info "Installing Proof Of Origin Token Provider, see https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide"

info "Cloning Server Software"
git clone --single-branch --branch 1.2.2 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git ~/services/bgutil-ytdlp-pot-provider
info "Installing Server Deps"
cd  ~/services/bgutil-ytdlp-pot-provider
npm install
npx tsc
cd "${REPO_DIR}"
info "Installing yt-dlp plugin"
debug "Copying yt-dlp config dir"
cp -r ./configs/yt-dlp "$XDG_CONFIG_HOME"
debug "Obtaining plugin"
curl -L "https://github.com/Brainicism/bgutil-ytdlp-pot-provider/releases/download/1.2.2/bgutil-ytdlp-pot-provider.zip" -o "${XDG_CONFIG_HOME}/yt-dlp/plugins/bgutil-ytdlp-pot-provider.zip"
info "yt-dlp Installed and configured"

