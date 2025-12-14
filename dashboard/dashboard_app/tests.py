from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from dashboard_app.models import App, CatalogItem
from unittest.mock import patch, MagicMock

User = get_user_model()

class DashboardTests(TestCase):
    def setUp(self):
        # Create SystemSettings to bypass onboarding
        from dashboard_app.models import SystemSettings
        SystemSettings.objects.create(
            domain="example.com",
            email="admin@example.com",
            public_dashboard=True
        )

        self.user = User.objects.create_user(username='testadmin', password='password')
        self.client = Client()
        self.client.login(username='testadmin', password='password')

        self.catalog_item = CatalogItem.objects.create(
            name="Test App",
            slug="test-app",
            description="A test app",
            docker_compose_template="version: '3'\nservices:\n  web:\n    image: nginx",
            form_schema=[]
        )

    def test_overview_access(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/overview.html')

    def test_catalog_access(self):
        response = self.client.get('/catalog/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/catalog.html')
        self.assertContains(response, "Test App")

    @patch('dashboard_app.views.ops')
    def test_install_app(self, mock_ops):
        mock_ops.install_app.return_value = {"status": "success"}

        response = self.client.post(f'/install/{self.catalog_item.slug}/', {
            'exposure': 'internal',
            'domain_prefix': 'test-app'
        })

        # Should redirect to details
        self.assertRedirects(response, f'/app/{self.catalog_item.slug}/')

        # Check if app was created
        app = App.objects.get(slug=self.catalog_item.slug)
        self.assertEqual(app.name, "Test App")
        self.assertEqual(app.status, "running")

        # Check if ops was called
        mock_ops.install_app.assert_called_once()
