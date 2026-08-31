from rest_framework.test import APITestCase

from apps.users.models import User


class AuthAndUserAdminTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone_number="+998901000001",
            password="adminpass",
            role_type="ADMIN",
            first_name="Admin",
        )
        self.agent = User.objects.create_user(
            phone_number="+998901000002",
            password="agentpass",
            role_type="AGENT",
            first_name="Agent",
        )
        self.customer = User.objects.create_user(
            phone_number="+998901000003",
            password=None,
            role_type="CUSTOMER",
            first_name="Mijoz",
        )

    def test_worker_needs_password(self):
        response = self.client.post(
            "/api/users/login/",
            {"phone_number": "+998901000002"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

        ok = self.client.post(
            "/api/users/login/",
            {"phone_number": "901000002", "password": "agentpass"},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertIn("refresh", ok.data)
        self.assertEqual(ok.data["user"]["role_type"], "AGENT")

    def test_customer_logs_in_without_password(self):
        response = self.client.post(
            "/api/users/login/",
            {"phone_number": "+998901000003"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role_type"], "CUSTOMER")

    def test_unknown_phone_rejected(self):
        response = self.client.post(
            "/api/users/login/",
            {"phone_number": "+998909999999"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_agent_cannot_list_users(self):
        self.client.force_authenticate(self.agent)
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_worker_and_cannot_delete_self(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/users/",
            {
                "phone_number": "+998901000009",
                "first_name": "Yetkazuvchi",
                "role_type": "DELIVERER",
                "password": "secret1",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        listing = self.client.get("/api/users/?role_type=DELIVERER")
        self.assertEqual(listing.status_code, 200)
        self.assertTrue(len(listing.data) >= 1 or listing.data.get("results"))

        doomed = self.client.delete(f"/api/users/{self.admin.id}/")
        self.assertEqual(doomed.status_code, 400)
