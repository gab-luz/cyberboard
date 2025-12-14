import socket
import json
import os

SOCKET_PATH = "/srv/gridops/ops/runner.sock"

class OpsClient:
    def _send(self, payload):
        if not os.path.exists(SOCKET_PATH):
             # Dev mode fallback or error
             if os.environ.get("DEBUG") == "True":
                 return {"status": "success", "message": "Dev mode: Ops command simulated"}
             return {"status": "error", "message": "Ops runner not available"}

        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.connect(SOCKET_PATH)
            client.sendall(json.dumps(payload).encode())
            client.shutdown(socket.SHUT_WR)

            response = b""
            while True:
                chunk = client.recv(4096)
                if not chunk: break
                response += chunk

            return json.loads(response.decode())
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            client.close()

    def install_app(self, slug, compose, env):
        return self._send({
            "command": "install_app",
            "app_slug": slug,
            "compose_content": compose,
            "env_content": env
        })

    def control_app(self, slug, action):
        # action: start, stop, restart, pull
        return self._send({
            "command": f"{action}_app",
            "app_slug": slug
        })

    def reload_proxy(self, caddyfile):
        return self._send({
            "command": "reload_proxy",
            "caddyfile": caddyfile
        })

    def backup_app(self, slug):
        return self._send({
            "command": "backup_app",
            "app_slug": slug
        })

    def self_update(self):
        return self._send({
            "command": "self_update"
        })

    def save_rclone_config(self, content):
        return self._send({
            "command": "config_rclone",
            "config_content": content
        })

    def mount_rclone(self, remote):
        return self._send({
            "command": "mount_rclone",
            "remote": remote
        })
