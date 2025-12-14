#!/bin/bash
set -e

LOG_FILE="/var/log/gridops-docker-install.log"
mkdir -p /var/log
touch "$LOG_FILE"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

log "Starting GridOps Docker Installation..."

# Check Root
if [ "$EUID" -ne 0 ]; then
    error_exit "Please run as root."
fi

# Variables
DOMAIN=""
EMAIL=""
INSTALL_DIR="/srv/gridops"
MODE=""

# Parse args
while [ "$1" != "" ]; do
    case $1 in
        --domain ) shift; DOMAIN=$1 ;;
        --email ) shift; EMAIL=$1 ;;
        --mode ) shift; MODE=$1 ;;
    esac
    shift
done

# Interactive mode selection if not provided
if [ -z "$MODE" ]; then
    if command -v dialog &> /dev/null; then
        MODE=$(dialog --clear --backtitle "GridOps Installer" \
            --title "Installation Mode" \
            --menu "Choose installation mode:" 15 50 4 \
            "dev" "Development (localhost, no SSL)" \
            "prod" "Production (custom domain, SSL)" \
            2>&1 >/dev/tty)
        clear
    else
        echo "Dialog not found. Install for better UI? (y/n)"
        read -p "Install dialog? [y/N]: " install_dialog
        if [[ $install_dialog =~ ^[Yy]$ ]]; then
            apt-get update -q && apt-get install -y dialog
            MODE=$(dialog --clear --backtitle "GridOps Installer" \
                --title "Installation Mode" \
                --menu "Choose installation mode:" 15 50 4 \
                "dev" "Development (localhost, no SSL)" \
                "prod" "Production (custom domain, SSL)" \
                2>&1 >/dev/tty)
            clear
        else
            echo "GridOps Installation Mode:"
            echo "1) Development (localhost, no SSL)"
            echo "2) Production (custom domain, SSL)"
            read -p "Choose mode [1-2]: " choice
            case $choice in
                1) MODE="dev" ;;
                2) MODE="prod" ;;
                *) error_exit "Invalid choice" ;;
            esac
        fi
    fi
fi

# Set defaults based on mode
if [ "$MODE" = "dev" ]; then
    DOMAIN="localhost"
    EMAIL="dev@localhost"
fi

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    read -p "Enter domain: " DOMAIN
    read -p "Enter email: " EMAIL
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    log "Installing Docker..."
    curl -fsSL https://get.docker.com | sh || error_exit "Failed to install Docker"
    systemctl enable --now docker || error_exit "Failed to start Docker"
else
    log "Docker already installed"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    log "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose || error_exit "Failed to download Docker Compose"
    chmod +x /usr/local/bin/docker-compose || error_exit "Failed to make Docker Compose executable"
else
    log "Docker Compose already installed"
fi

# Setup directory
log "Setting up installation directory..."
mkdir -p "$INSTALL_DIR"
cp -r . "$INSTALL_DIR/" || error_exit "Failed to copy files"

# Generate consistent passwords
DB_PASSWORD=$(openssl rand -base64 16)
SECRET_KEY=$(openssl rand -base64 32)

# Create Docker Compose file
log "Creating Docker Compose configuration..."
cat > "$INSTALL_DIR/docker-compose.yml" <<EOF
version: '3.8'

services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

  dashboard:
    build: ./dashboard
    environment:
      - DEBUG=False
      - SECRET_KEY=$SECRET_KEY
      - ALLOWED_HOSTS=localhost,127.0.0.1,$DOMAIN
      - DATABASE_URL=postgres://gridops:$DB_PASSWORD@postgres:5432/gridops
      - REDIS_URL=redis://redis:6379/0
      - GRIDOPS_DOMAIN=$DOMAIN
      - GRIDOPS_EMAIL=$EMAIL
    depends_on:
      - postgres
      - redis
    command: sh -c "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3"
    restart: unless-stopped

  postgres:
    image: postgres:17-alpine
    environment:
      - POSTGRES_DB=gridops
      - POSTGRES_USER=gridops
      - POSTGRES_PASSWORD=$DB_PASSWORD
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
  postgres_data:
  redis_data:
EOF

# Create Caddyfile
log "Creating Caddy configuration for $MODE mode..."
if [ "$MODE" = "dev" ]; then
    cp Caddyfile.dev "$INSTALL_DIR/Caddyfile"
    log "Using development mode (HTTP only)"
else
    sed "s/isaio.in/$DOMAIN/g" Caddyfile.prod > "$INSTALL_DIR/Caddyfile"
    log "Using production mode with SSL for $DOMAIN"
fi

# Create dashboard Dockerfile
log "Creating dashboard Dockerfile..."
cat > "$INSTALL_DIR/dashboard/Dockerfile" <<EOF
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \\
    libpq-dev gcc && \\
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
EOF

# Setup firewall
log "Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80
ufw allow 443
ufw --force enable

# Start services
log "Starting GridOps services..."
cd "$INSTALL_DIR"
docker-compose up -d || error_exit "Failed to start services"

log "Installation complete!"
log "GridOps is now running at https://$DOMAIN"
log "Check status with: docker-compose -f $INSTALL_DIR/docker-compose.yml ps"