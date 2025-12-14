#!/bin/bash
set -e

INSTALL_DIR="/srv/gridops"

echo "Stopping containers..."
cd "$INSTALL_DIR"
docker-compose down

echo "Removing old images..."
docker images | grep gridops | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
docker system prune -f

echo "Copying updated files..."
cp -r /mnt/ia/DEV/cyberboard/* "$INSTALL_DIR/"
echo "Files copied, current directory contents:"
ls -la "$INSTALL_DIR/dashboard/dashboard_app/" | head -5

echo "Building and starting containers..."
docker-compose build --no-cache
docker-compose up -d

echo "Update complete!"
echo "Check status: docker-compose -f $INSTALL_DIR/docker-compose.yml ps"