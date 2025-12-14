from django.core.management.base import BaseCommand
import yaml
from dashboard_app.models import CatalogItem

class Command(BaseCommand):
    help = 'Import apps from catalog yaml'

    def handle(self, *args, **options):
        import os
        # 1. Try relative to manage.py (standard dev/prod structure)
        # manage.py is in dashboard/
        # apps_catalog is in apps_catalog/ (sibling of dashboard/)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        # If installed via installer, base_dir should be /srv/gridops/dashboard/.. -> /srv/gridops

        path = os.path.join(base_dir, 'apps_catalog', 'initial_apps.yaml')

        if not os.path.exists(path):
            # Fallback for some dev environments
            path = os.path.abspath(os.path.join(os.getcwd(), '..', 'apps_catalog', 'initial_apps.yaml'))

        if not os.path.exists(path):
             # Hard fallback to expected install location
             path = '/srv/gridops/apps_catalog/initial_apps.yaml'

        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f'Catalog file not found at {path}'))
            return

        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        for entry in data:
            CatalogItem.objects.update_or_create(
                slug=entry['slug'],
                defaults={
                    'name': entry['name'],
                    'description': entry['description'],
                    'category': entry.get('category', 'General'),
                    'icon': entry.get('icon', '📦'),
                    'docker_compose_template': entry['docker_compose_template'],
                    'form_schema': entry.get('form_schema', [])
                }
            )
        self.stdout.write(self.style.SUCCESS('Successfully imported catalog'))
