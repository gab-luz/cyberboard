#!/bin/bash
set -e

# GridOps Installer for Debian 13
# Usage: ./gridops-install.sh [options]

LOG_FILE="/var/log/gridops/install.log"
mkdir -p /var/log/gridops
touch "$LOG_FILE"
chmod 600 "$LOG_FILE"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting GridOps Installer..."

# Check Root
if [ "$EUID" -ne 0 ]; then
  log "Please run as root."
  exit 1
fi

# Variables with defaults
DOMAIN=""
EMAIL=""
DB_PASS=$(openssl rand -base64 12)
SECRET_KEY=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 16)
INSTALL_DIR="/srv/gridops"

# Parse args (simple implementation)
while [ "$1" != "" ]; do
    case $1 in
        --domain ) shift; DOMAIN=$1 ;;
        --email ) shift; EMAIL=$1 ;;
    esac
    shift
done

# 1. System Dependencies
log "Installing system dependencies..."
apt-get update -q
apt-get install -y -q curl wget git build-essential python3-venv python3-dev libpq-dev acl ufw fail2ban rclone fuse3

# 2. Install Docker & Compose
if ! command -v docker &> /dev/null; then
    log "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
else
    log "Docker already installed."
fi

# 3. Install Caddy
if ! command -v caddy &> /dev/null; then
    log "Installing Caddy..."
    apt-get install -y -q debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg --yes
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -q
    apt-get install -y -q caddy
else
    log "Caddy already installed."
fi

# 4. Install Postgres & Redis
log "Installing Postgres and Redis..."
apt-get install -y -q postgresql redis-server
systemctl enable --now postgresql
systemctl enable --now redis-server

# Configure Postgres
sudo -u postgres psql -c "CREATE USER gridops WITH PASSWORD '$POSTGRES_PASSWORD';" || true
sudo -u postgres psql -c "CREATE DATABASE gridops OWNER gridops;" || true
sudo -u postgres psql -c "ALTER USER gridops CREATEDB;" || true

# 5. Create GridOps User
log "Creating gridops user..."
if ! id -u gridops > /dev/null 2>&1; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" -m gridops
    usermod -aG docker gridops
fi

# 6. Setup Directory Structure
log "Setting up directory structure..."
if [ -d ".git" ]; then
    log "Deploying from local git repository..."
    cp -r . "$INSTALL_DIR/"
else
    log "Copying files to install directory..."
    cp -r . "$INSTALL_DIR/"
fi

mkdir -p "$INSTALL_DIR"/{apps,backups,static,media}
chown -R gridops:gridops "$INSTALL_DIR"

# 7. Setup Python Environment
log "Setting up Python environment..."
cd "$INSTALL_DIR"
if [ ! -d "venv" ]; then
    sudo -u gridops python3 -m venv "venv"
fi

# Install requirements
sudo -u gridops "venv/bin/pip" install -r dashboard/requirements.txt

# 8. Setup Ops Runner
# (Already copied via git clone/cp)

# 9. Setup Django
# (Already copied via git clone/cp)

# Create .env
cat > "$INSTALL_DIR/.env" <<EOF
DEBUG=False
SECRET_KEY='$SECRET_KEY'
ALLOWED_HOSTS='localhost,127.0.0.1,$DOMAIN'
DATABASE_URL='postgres://gridops:$POSTGRES_PASSWORD@localhost:5432/gridops'
REDIS_URL='redis://localhost:6379/0'
GRIDOPS_DOMAIN='$DOMAIN'
GRIDOPS_EMAIL='$EMAIL'
EOF
chown gridops:gridops "$INSTALL_DIR/.env"
chmod 600 "$INSTALL_DIR/.env"

# 10. Systemd Services
log "Installing systemd services..."
# We will generate these files in the next step
cp install/*.service /etc/systemd/system/ || true
systemctl daemon-reload

# 11. Firewall
log "Configuring Firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80
ufw allow 443
# Wireguard port if needed (default 51820)
ufw allow 51820/udp
ufw --force enable

log "Installation Complete!"
log "Please run 'systemctl start gridops-web' to start the dashboard."
