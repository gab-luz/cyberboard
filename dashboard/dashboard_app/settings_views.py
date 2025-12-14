from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ops.client import OpsClient

ops = OpsClient()

@login_required
def system_settings(request):
    if request.method == "POST":
        if 'rclone_config' in request.POST:
            content = request.POST['rclone_config']
            res = ops.save_rclone_config(content)
            if res.get('status') == 'success':
                messages.success(request, "Rclone configuration saved.")
            else:
                messages.error(request, f"Error saving config: {res.get('message')}")

        elif 'mount_remote' in request.POST:
            remote = request.POST['mount_remote']
            res = ops.mount_rclone(remote)
            if res.get('status') == 'success':
                 messages.success(request, f"Mounted remote {remote}.")
            else:
                 messages.error(request, f"Error mounting: {res.get('message')}")

    return render(request, 'dashboard/settings.html')

@login_required
def system_update(request):
    if request.method == "POST":
        res = ops.self_update()
        if res.get('status') == 'success':
            messages.info(request, "System update initiated. The service will restart shortly.")
        else:
            messages.error(request, f"Update failed: {res.get('message')}")
    return redirect('settings')
