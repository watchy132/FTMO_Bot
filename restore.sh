#!/bin/bash
set -e
cd "$(dirname "$0")"

choose_latest(){ ls -1d backup_* 2>/dev/null | sort -r | head -1; }
SRC="${1:-$(choose_latest)}"
[ -z "$SRC" ] && { echo "Aucun dossier backup_ trouvé."; exit 1; }
[ ! -d "$SRC" ] && { echo "Backup inexistant: $SRC"; exit 1; }

echo "Restauration depuis: $SRC"
rsync -a --delete \
  --exclude='**/__pycache__/' --exclude='*.pyc' --exclude='*.pyo' \
  "$SRC"/ ./
echo "OK: restauration terminée."
