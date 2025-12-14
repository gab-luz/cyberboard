# Threat Model

## Assets
*   User Data (Credentials, App Data)
*   Infrastructure (Host System, Docker Engine)
*   Network Access (Public IP, WireGuard)

## Threats & Mitigations

### 1. Unauthorized Access to Dashboard
*   **Risk**: Attacker gains control of GridOps.
*   **Mitigation**:
    *   Enforced 2FA (planned).
    *   Rate limiting (Fail2ban).
    *   Strong password policy.
    *   Session security (Secure cookies).

### 2. Remote Code Execution (RCE) via Web App
*   **Risk**: Attacker exploits Django vulnerability to run commands.
*   **Mitigation**:
    *   Django runs as unprivileged `gridops` user.
    *   Cannot run docker commands directly; must use Ops Runner socket.
    *   Input validation on app installation fields.

### 3. Malicious App Installation
*   **Risk**: User installs a malicious docker image.
*   **Mitigation**:
    *   Catalog is curated (Admin only adds apps).
    *   Ops Runner blocks `privileged: true` and host mounts unless explicitly allowed (not yet implemented fully, rely on template review).

### 4. Privilege Escalation
*   **Risk**: `gridops` user gains root.
*   **Mitigation**:
    *   `gridops` user has no sudo access (except specific commands if needed, currently none).
    *   Ops Runner socket permissions restricted to `gridops` group.

### 5. Network Exposure
*   **Risk**: Internal apps exposed to public.
*   **Mitigation**:
    *   Caddy manages routing.
    *   Apps default to "Internal" or "VPN-only".
    *   Firewall blocks all non-essential ports.
