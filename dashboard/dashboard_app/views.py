from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from .models import App, CatalogItem, SystemSettings, AuditLog
# from ops.client import OpsClient  # TODO: Implement ops client

class OpsClient:
    def reload_proxy(self, caddyfile):
        return {"status": "success"}
    
    def install_app(self, slug, compose_content, env_str):
        return {"status": "success"}
    
    def control_app(self, slug, action):
        return {"status": "success"}
from .caddy_utils import generate_caddyfile
from .forms import OnboardingForm
from django.contrib.auth.models import User
from django.contrib.auth import login
import json
import psutil
import datetime

ops = OpsClient()

def onboarding(request):
    if SystemSettings.objects.exists():
        return redirect('overview')

    if request.method == "POST":
        form = OnboardingForm(request.POST)
        if form.is_valid():
            # Create Settings
            settings = form.save()

            # Create Admin
            user = User.objects.create_superuser(
                username=form.cleaned_data['admin_username'],
                email=settings.email,
                password=form.cleaned_data['admin_password']
            )

            # Login
            login(request, user)

            # Initial Proxy Config
            caddyfile = generate_caddyfile()
            ops.reload_proxy(caddyfile)

            messages.success(request, "Welcome to GridOps!")
            return redirect('overview')
    else:
        form = OnboardingForm()

    return render(request, 'dashboard/onboarding.html', {'form': form})

@login_required
def dashboard_overview(request):
    apps = App.objects.all()
    # Mock system stats for now, real implementation would polling or websocket
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent

    return render(request, 'dashboard/overview.html', {
        'apps': apps,
        'cpu': cpu_usage,
        'ram': ram_usage,
        'disk': disk_usage,
    })

@login_required
def app_catalog(request):
    catalog = CatalogItem.objects.all()
    return render(request, 'dashboard/catalog.html', {'catalog': catalog})

@login_required
def install_app(request, slug):
    item = get_object_or_404(CatalogItem, slug=slug)

    if request.method == "POST":
        # Process installation
        env_vars = {}
        for key in request.POST:
            if key.startswith("env_"):
                env_vars[key[4:]] = request.POST[key]

        # Determine exposure
        exposure = request.POST.get("exposure", "internal")
        domain_prefix = request.POST.get("domain_prefix", slug)

        # Generate Compose
        compose_content = item.docker_compose_template # Simple for now, needs templating engine

        # In a real scenario, we would replace ${VAR} in compose with env_vars

        # Create App record
        app = App.objects.create(
            name=item.name,
            slug=slug,
            icon=item.icon,
            version="latest",
            image="unknown", # parse from compose
            env_vars=env_vars,
            expose_public=(exposure == 'public'),
            expose_vpn=(exposure == 'vpn'),
            domain_prefix=domain_prefix,
            status="installing"
        )

        # Trigger Install via Ops
        env_str = "\n".join([f"{k}={v}" for k,v in env_vars.items()])
        result = ops.install_app(slug, compose_content, env_str)

        if result.get("status") == "success":
            app.status = "running"
            app.save()

            # Update Proxy
            caddyfile = generate_caddyfile()
            ops.reload_proxy(caddyfile)

            messages.success(request, f"{app.name} installed successfully!")

            # Audit log
            AuditLog.objects.create(
                user=request.user,
                action="install_app",
                details=f"Installed {slug}",
                ip_address=request.META.get('REMOTE_ADDR')
            )

            return redirect('app_details', slug=slug)
        else:
            app.status = "error"
            app.save()
            messages.error(request, f"Installation failed: {result.get('message')}")

    return render(request, 'dashboard/install.html', {'item': item})

@login_required
def app_details(request, slug):
    app = get_object_or_404(App, slug=slug)
    return render(request, 'dashboard/app_details.html', {'app': app})

@login_required
def app_control(request, slug, action):
    app = get_object_or_404(App, slug=slug)
    if action in ['start', 'stop', 'restart', 'pull']:
        result = ops.control_app(slug, action)
        if result.get("status") == "success":
            messages.success(request, f"{action.capitalize()} command sent.")
            AuditLog.objects.create(
                user=request.user,
                action=f"{action}_app",
                details=f"{action} {slug}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
        else:
             messages.error(request, f"Command failed: {result.get('message')}")
    return redirect('app_details', slug=slug)

@login_required
def system_stats(request):
    # HTMX endpoint
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    return render(request, 'dashboard/partials/stats.html', {
        'cpu': cpu, 'ram': ram, 'disk': disk
    })
