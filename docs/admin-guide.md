# GridOps Admin Guide

## Installation

1.  Provision a Debian 13 VPS.
2.  SSH into the server as root.
3.  Clone the repository:
    ```bash
    git clone https://github.com/your/gridops.git
    cd gridops
    ```
4.  Run the installer:
    ```bash
    chmod +x install/gridops-install.sh
    ./install/gridops-install.sh --domain yourdomain.tld --email admin@yourdomain.tld
    ```
5.  Access the dashboard at `https://yourdomain.tld`.

## Architecture

*   **Django Dashboard**: Runs as `gridops` user.
*   **Ops Runner**: Privileged Python service listening on unix socket, runs as `root`.
*   **Caddy**: Reverse proxy handling TLS and routing.
*   **Postgres**: Database.
*   **Redis**: Cache and queue broker.

## Managing Apps

Apps are installed as Docker Compose projects in `/srv/gridops/apps/<slug>`.

To manually inspect:
```bash
cd /srv/gridops/apps/<slug>
docker compose ps
```

## Security

*   **Firewall**: UFW is enabled by default. Only ports 80, 443, and SSH (default 22) are open.
*   **Isolation**: The web dashboard cannot execute arbitrary commands; it speaks to the Ops Runner which validates commands.
*   **Audit**: All actions are logged in the database.

## Troubleshooting

Logs are located at:
*   `/var/log/gridops/install.log`
*   `/var/log/gridops/runner.log`
*   `journalctl -u gridops-web`
*   `journalctl -u gridops-runner`

## Recovery

To reset the admin password:
```bash
cd /srv/gridops/dashboard
source ../venv/bin/activate
python3 manage.py changepassword <username>
```
