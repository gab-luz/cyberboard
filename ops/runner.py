import os
import socket
import struct
import json
import subprocess
import logging
import signal
import sys
from pathlib import Path

# Configuration
SOCKET_PATH = "/srv/gridops/ops/runner.sock"
APPS_DIR = "/srv/gridops/apps"
CADDY_FILE = "/etc/caddy/Caddyfile"
LOG_FILE = "/var/log/gridops/runner.log"
RCLONE_CONFIG_DIR = "/srv/gridops/rclone"
RCLONE_MOUNT_DIR = "/srv/gridops/rclone_mounts"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s %(message)s')

def run_command(command, cwd=None, env=None):
    try:
        logging.info(f"Running command: {command} in {cwd}")
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            shell=False # Security: no shell
        )
        return {"status": "success", "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e.stderr}")
        return {"status": "error", "stdout": e.stdout, "stderr": e.stderr}
    except Exception as e:
        logging.error(f"Exception: {str(e)}")
        return {"status": "error", "message": str(e)}

def handle_install(data):
    # data: { app_slug: str, compose_content: str, env_content: str }
    app_slug = data.get('app_slug')
    compose_content = data.get('compose_content')
    env_content = data.get('env_content')

    if not app_slug or not compose_content:
        return {"status": "error", "message": "Missing app_slug or compose_content"}

    # Path traversal check
    if ".." in app_slug or "/" in app_slug:
        return {"status": "error", "message": "Invalid app_slug"}

    app_dir = os.path.join(APPS_DIR, app_slug)
    os.makedirs(app_dir, exist_ok=True)

    with open(os.path.join(app_dir, "docker-compose.yml"), "w") as f:
        f.write(compose_content)

    if env_content:
        with open(os.path.join(app_dir, ".env"), "w") as f:
            f.write(env_content)

    # Pull and Up
    return run_command(["docker", "compose", "up", "-d"], cwd=app_dir)

def handle_control(data, action):
    app_slug = data.get('app_slug')
    if not app_slug or ".." in app_slug:
         return {"status": "error", "message": "Invalid app_slug"}

    app_dir = os.path.join(APPS_DIR, app_slug)
    if not os.path.exists(app_dir):
        return {"status": "error", "message": "App not found"}

    cmd = ["docker", "compose", action]
    if action == "restart":
        cmd = ["docker", "compose", "restart"]
    elif action == "stop":
         cmd = ["docker", "compose", "stop"]
    elif action == "start":
         cmd = ["docker", "compose", "start"]
    elif action == "pull":
         cmd = ["docker", "compose", "pull"]

    return run_command(cmd, cwd=app_dir)

def handle_backup(data):
    app_slug = data.get('app_slug')
    if not app_slug or ".." in app_slug:
         return {"status": "error", "message": "Invalid app_slug"}

    app_dir = os.path.join(APPS_DIR, app_slug)
    if not os.path.exists(app_dir):
        return {"status": "error", "message": "App not found"}

    # Simple volume backup: tar the app dir (naive)
    # Better: Inspect docker-compose, find volumes, backup them.
    # For MVP: We assume volumes are bound in ./

    backup_path = f"/srv/gridops/backups/{app_slug}_backup.tar.gz"
    res = run_command(["tar", "-czf", backup_path, "-C", APPS_DIR, app_slug])

    if res['status'] == 'success':
        # Optional: Sync to Rclone remote if configured
        # Naive check: if 'backup' remote exists in config, sync there
        config_path = os.path.join(RCLONE_CONFIG_DIR, "rclone.conf")
        if os.path.exists(config_path):
             # We assume a remote named 'backup' is preferred, or we just keep local
             # For this task, we can't easily guess the remote without UI input.
             # So we'll leave it as local-only unless we add a 'remote' param to handle_backup.
             pass

    return res

def handle_self_update(data):
    # 1. Backup System
    backup_file = f"/srv/gridops/backups/system_pre_update.tar.gz"
    # Backup code + db + env
    run_command(["tar", "-czf", backup_file, "-C", "/srv", "gridops"], cwd="/srv")

    # 2. Git Pull
    # Assume /srv/gridops is a git repo
    # If not, this will fail. The installer should have cloned it.
    res = run_command(["git", "pull"], cwd="/srv/gridops")
    if res['status'] == 'error':
        return res

    # 3. Update Deps (simplified)
    # In reality, check for requirements.txt changes

    # 4. Restart Services
    # We can't restart ourselves synchronously easily without breaking connection
    # So we schedule a restart
    subprocess.Popen("sleep 2 && systemctl restart gridops-web gridops-runner", shell=True)

    return {"status": "success", "message": "Update started. System restarting..."}

def handle_config_rclone(data):
    config_content = data.get('config_content')
    if not config_content:
        return {"status": "error", "message": "No content"}

    os.makedirs(RCLONE_CONFIG_DIR, exist_ok=True)
    config_path = os.path.join(RCLONE_CONFIG_DIR, "rclone.conf")

    with open(config_path, "w") as f:
        f.write(config_content)

    return {"status": "success", "message": "Rclone config saved"}

def handle_mount_rclone(data):
    remote = data.get('remote')
    if not remote or "/" in remote or " " in remote:
        return {"status": "error", "message": "Invalid remote name"}

    os.makedirs(RCLONE_MOUNT_DIR, exist_ok=True)
    mount_point = os.path.join(RCLONE_MOUNT_DIR, remote)
    os.makedirs(mount_point, exist_ok=True)

    # Create Systemd Unit
    unit_content = f"""[Unit]
Description=RClone Mount for {remote}
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/bin/rclone mount {remote}: {mount_point} \\
   --config {RCLONE_CONFIG_DIR}/rclone.conf \\
   --allow-other \\
   --vfs-cache-mode writes \\
   --dir-cache-time 5m \\
   --log-level INFO \\
   --log-file /var/log/gridops/rclone-{remote}.log
ExecStop=/bin/fusermount -u {mount_point}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    unit_path = f"/etc/systemd/system/gridops-mount-{remote}.service"
    with open(unit_path, "w") as f:
        f.write(unit_content)

    run_command(["systemctl", "daemon-reload"])
    res = run_command(["systemctl", "enable", "--now", f"gridops-mount-{remote}.service"])

    if res['status'] == 'success':
         return {"status": "success", "message": f"Mounted {remote} at {mount_point}"}
    else:
         return res

def handle_reload_proxy(data):
    caddyfile_content = data.get('caddyfile')
    if not caddyfile_content:
        return {"status": "error", "message": "No content"}

    with open(CADDY_FILE, "w") as f:
        f.write(caddyfile_content)

    # Reload caddy
    return run_command(["caddy", "reload", "--config", CADDY_FILE])

def handle_request(data):
    command = data.get('command')
    if command == 'install_app':
        return handle_install(data)
    elif command in ['start_app', 'stop_app', 'restart_app', 'pull_app']:
        action = command.split('_')[0] # start, stop, etc
        return handle_control(data, action)
    elif command == 'backup_app':
        return handle_backup(data)
    elif command == 'reload_proxy':
        return handle_reload_proxy(data)
    elif command == 'self_update':
        return handle_self_update(data)
    elif command == 'config_rclone':
        return handle_config_rclone(data)
    elif command == 'mount_rclone':
        return handle_mount_rclone(data)
    else:
        return {"status": "error", "message": "Unknown command"}

def main():
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o660) # Allow group access (gridops group)

    # We need to set group ownership of the socket to 'gridops' so the web app can write to it
    import grp
    try:
        gid = grp.getgrnam("gridops").gr_gid
        os.chown(SOCKET_PATH, -1, gid)
    except Exception as e:
        logging.error(f"Failed to set socket group: {e}")

    server.listen(1)
    logging.info(f"Listening on {SOCKET_PATH}")

    def signal_handler(sig, frame):
        logging.info("Shutting down...")
        server.close()
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        try:
            conn, _ = server.accept()
            with conn:
                data = b""
                while True:
                    packet = conn.recv(4096)
                    if not packet: break
                    data += packet

                if data:
                    try:
                        req = json.loads(data.decode())
                        resp = handle_request(req)
                        conn.sendall(json.dumps(resp).encode())
                    except json.JSONDecodeError:
                        conn.sendall(json.dumps({"status": "error", "message": "Invalid JSON"}).encode())
                    except Exception as e:
                        conn.sendall(json.dumps({"status": "error", "message": str(e)}).encode())
        except Exception as e:
            logging.error(f"Connection error: {e}")

if __name__ == "__main__":
    main()
