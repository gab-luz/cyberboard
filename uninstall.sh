#!/bin/bash
set -e

LOG_FILE="/var/log/gridops-uninstall.log"
mkdir -p /var/log
touch "$LOG_FILE"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting GridOps Uninstallation..."

# Check Root
if [ "$EUID" -ne 0 ]; then
    log "Please run as root."
    exit 1
fi

INSTALL_DIR="/srv/gridops"

# Stop and remove Docker containers
if [ -f "$INSTALL_DIR/docker-compose.yml" ]; then
    log "Stopping Docker containers..."
    cd "$INSTALL_DIR"
    docker-compose down -v --remove-orphans || true
    docker-compose rm -f || true
fi

# Stop systemd services (if any)
log "Stopping systemd services..."
systemctl stop gridops-web gridops-worker gridops-runner 2>/dev/null || true
systemctl disable gridops-web gridops-worker gridops-runner 2>/dev/null || true

# Remove systemd service files
log "Removing systemd service files..."
rm -f /etc/systemd/system/gridops-*.service
systemctl daemon-reload

# Remove user and group
log "Removing gridops user..."
userdel -r gridops 2>/dev/null || true

# Remove installation directory
log "Removing installation directory..."
rm -rf "$INSTALL_DIR"

# Remove PostgreSQL database and user (if installed locally)
if command -v psql &> /dev/null; then
    log "Removing PostgreSQL database and user..."
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS gridops;" 2>/dev/null || true
    sudo -u postgres psql -c "DROP USER IF EXISTS gridops;" 2>/dev/null || true
fi

# Remove logs
log "Removing log files..."
rm -rf /var/log/gridops*

# Clean Docker images (optional)
read -p "Remove GridOps Docker images? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "Removing Docker images..."
    docker images | grep gridops | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
fi

log "GridOps uninstallation complete!"
log "Note: Docker, Caddy, PostgreSQL, and Redis were not removed as they may be used by other applications."