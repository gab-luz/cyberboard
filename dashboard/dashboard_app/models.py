from django.db import models
from django.contrib.auth.models import AbstractUser

class App(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, help_text="Material Icon name or URL")
    version = models.CharField(max_length=50)
    maintainer = models.CharField(max_length=100, blank=True)

    # Configuration
    image = models.CharField(max_length=200) # Docker image
    env_vars = models.JSONField(default=dict) # {"VAR": "default"}
    ports = models.JSONField(default=list) # [8080]
    volumes = models.JSONField(default=list) # ["/data"]

    # Installation State
    installed_version = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, default="stopped") # running, stopped, error

    # Exposure
    expose_public = models.BooleanField(default=False)
    expose_vpn = models.BooleanField(default=False)
    domain_prefix = models.CharField(max_length=100, blank=True) # app.domain.tld

    # Security
    auth_protected = models.BooleanField(default=False, help_text="Enable Anubis protection")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class CatalogItem(models.Model):
    """
    Source of truth for available apps.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.CharField(max_length=50, default="General")
    icon = models.CharField(max_length=100)

    # Template
    docker_compose_template = models.TextField()
    form_schema = models.JSONField(default=dict) # JSON schema for installation form

    def __str__(self):
        return self.name

class SystemSettings(models.Model):
    domain = models.CharField(max_length=200)
    email = models.EmailField()
    vpn_enabled = models.BooleanField(default=False)
    ssh_port = models.IntegerField(default=22)
    public_dashboard = models.BooleanField(default=True)

class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True)
