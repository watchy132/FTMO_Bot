#!/bin/bash
set -e
cd "$(dirname "$0")"
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p backup_$STAMP

# Copie uniquement les fichiers et dossiers sauf les backups existants
shopt -s extglob
cp -a !(backup_*) backup_$STAMP/

echo "Backup créé: backup_$STAMP"
