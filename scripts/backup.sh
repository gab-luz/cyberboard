#!/bin/bash
# Backup script for GridOps
# Usage: ./backup.sh

BACKUP_DIR="/srv/gridops/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARGET_DIR="$BACKUP_DIR/$TIMESTAMP"

mkdir -p "$TARGET_DIR"

log() {
    echo "[$(date)] $1"
}

log "Starting backup..."

# 1. Database
log "Backing up database..."
pg_dump -U gridops gridops > "$TARGET_DIR/db.sql"

# 2. Configs
log "Backing up configs..."
cp /srv/gridops/.env "$TARGET_DIR/"
cp /etc/caddy/Caddyfile "$TARGET_DIR/"

# 3. Compress
log "Compressing..."
tar -czf "$BACKUP_DIR/gridops_backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" "$TIMESTAMP"

# 4. Cleanup
rm -rf "$TARGET_DIR"
find "$BACKUP_DIR" -name "gridops_backup_*.tar.gz" -mtime +7 -delete

log "Backup complete: $BACKUP_DIR/gridops_backup_$TIMESTAMP.tar.gz"
