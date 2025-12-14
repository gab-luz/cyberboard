# Changelog

All notable changes to GridOps will be documented in this file.

## [Unreleased]

### Added
- Docker-based installation system (`docker-install.sh`)
- Uninstaller script (`uninstall.sh`) to remove all traces
- Containerized architecture with Caddy, Dashboard, PostgreSQL, Redis
- Onboarding system for optional app installation
- Management command for setup (`setup_onboarding.py`)
- Proper error handling and logging in installer

### Changed
- **BREAKING**: Moved from systemd services to Docker containers
- **BREAKING**: Moved installer from `/install/` to root directory
- Installation now uses ports 80/443 via Caddy container only
- Anubis and WG Easy are now optional during onboarding

### Fixed
- Git clone authentication issues during installation
- Path resolution errors in installer script
- Missing requirements.txt path in Python environment setup
- Systemd service failures and debugging visibility

### Removed
- Direct system package installation (PostgreSQL, Redis, Python venv)
- Systemd service files for web, worker, runner
- Git repository cloning requirement during installation