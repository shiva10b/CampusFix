from django.test import SimpleTestCase, override_settings
from django.urls import reverse


class PublicPageTests(SimpleTestCase):
    def test_landing_page_loads_and_uses_branding(self):
        response = self.client.get(reverse("core:landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CampusFix")
        self.assertTemplateUsed(response, "core/landing.html")

    def test_health_endpoint_returns_service_status(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"status": "ok", "service": "CampusFix"},
        )

    @override_settings(DEBUG=False)
    def test_custom_404_page(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)
        self.assertTemplateUsed(response, "404.html")

