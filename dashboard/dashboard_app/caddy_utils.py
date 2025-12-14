from django.template.loader import render_to_string
from django.conf import settings
from .models import App, SystemSettings

def generate_caddyfile():
    apps = App.objects.all()
    system_settings = SystemSettings.objects.first()
    domain = system_settings.domain if system_settings else "localhost"

    # Base Caddyfile content
    caddy_content = f"""
{{
    email {getattr(system_settings, 'email', 'admin@localhost')}
}}

# Dashboard
{domain} {{
    reverse_proxy 127.0.0.1:8000
}}
"""

    # Append App routes
    for app in apps:
        if app.status != 'running':
            continue

        app_domain = f"{app.domain_prefix}.{domain}"

        if not app.ports:
            continue

        # Naive port selection: first port.
        # In production, we'd store "web_port" explicitly in App model.
        upstream_port = app.ports[0]
        if ":" in str(upstream_port):
             upstream_port = str(upstream_port).split(":")[0]

        route_block = f"""
{app_domain} {{
"""
        # Exposure Logic
        if app.expose_vpn and not app.expose_public:
            # VPN Only: Restrict to private ranges
            route_block += """
    @vpn {
        remote_ip 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 10.8.0.0/24
    }
    handle @vpn {
        reverse_proxy localhost:%s
    }
    respond 403
""" % upstream_port

        elif app.expose_public:
             # Public Internet
             route_block += f"""
    reverse_proxy localhost:{upstream_port}
"""
        else:
             # Internal only (no route exposed via Caddy, or explicit deny)
             route_block += """
    respond 403
"""

        route_block += "}\n"
        caddy_content += route_block

    return caddy_content
