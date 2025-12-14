from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Setup initial onboarding data'

    def handle(self, *args, **options):
        apps_config = {
            'anubis': {
                'name': 'Anubis',
                'description': 'Network monitoring and security scanner',
                'default_selected': True,
                'docker_image': 'anubis:latest'
            },
            'wgeasy': {
                'name': 'WG Easy', 
                'description': 'WireGuard VPN management interface',
                'default_selected': True,
                'docker_image': 'weejewel/wg-easy:latest'
            }
        }
        
        self.stdout.write(self.style.SUCCESS('Onboarding setup complete'))