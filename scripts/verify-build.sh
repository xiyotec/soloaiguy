#!/usr/bin/env bash
set -euo pipefail

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

cd "$HOME/builds/soloaiguy"
echo "node: $(which node) ($(node -v))"
echo "npm:  $(which npm) ($(npm -v))"
npm run build 2>&1 | tail -80
