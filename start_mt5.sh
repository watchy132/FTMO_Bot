#!/bin/zsh
set -euo pipefail
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine-mt5}"
MT5_PATH="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"
WINE64="$(command -v wine64 || true)"
if [ -z "$WINE64" ]; then
  ALT="/Applications/Wine Stable.app/Contents/Resources/wine/bin/wine64"
  if [ -x "$ALT" ]; then
    WINE64="$ALT"
  else
    echo "ERREUR: wine64 introuvable."
    exit 1
  fi
fi
if [ ! -f "$MT5_PATH" ]; then
  echo "ERREUR: MT5 introuvable: $MT5_PATH"
  exit 1
fi
exec "$WINE64" "$MT5_PATH"
