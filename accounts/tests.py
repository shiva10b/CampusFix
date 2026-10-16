from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .management.commands.create_demo_users import DEMO_USERS

User = get_user_model()
PASSWORD = "StrongPass123!"


def create_user(username, role, **overrides):
    defaults = {"email": f"{username}@example.com", "first_name": username.title(), "last_name": "Tester", "department": "Testing", "role": role, "password": PASSWORD}
    defaults.update(overrides)
    return User.objects.create_user(username=username, **defaults)


class CustomUserModelTests(TestCase):
    def test_student_is_default_role(self):
        user = User.objects.create_user(username="student", email="student@example.com", department="CSE", password=PASSWORD)
        self.assertEqual(user.role, User.Role.STUDENT)

    def test_all_required_roles_can_be_stored(self):
        for index, role in enumerate(User.Role.values):
            self.assertEqual(create_user(f"user-{index}", role).role, role)

    def test_custom_user_is_configured_as_active_user_model(self):
        self.assertEqual(User._meta.label, "accounts.User")

    def test_blank_identifiers_are_saved_as_null_and_do_not_conflict(self):
        first = create_user("blank-one", User.Role.STUDENT, student_id="", employee_id="")
        second = create_user("blank-two", User.Role.STAFF, student_id="", employee_id="")
        self.assertIsNone(first.student_id)
        self.assertIsNone(second.student_id)

    def test_superuser_is_always_campusfix_administrator(self):
        user = User.objects.create_superuser(username="root", email="root@example.com", department="Admin", password=PASSWORD, role=User.Role.STUDENT)
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)


class RegistrationTests(TestCase):
    url = reverse("accounts:register")

    def registration_data(self, **overrides):
        data = {"first_name": "  Riya ", "last_name": " Student ", "username": "riya", "email": "RIYA@example.com", "student_id": " cse-101 ", "department": " Computer Science ", "phone_number": " 9876543210 ", "password1": PASSWORD, "password2": PASSWORD, "role": User.Role.ADMIN}
        data.update(overrides)
        return data

    def test_successful_registration_always_creates_student(self):
        response = self.client.post(self.url, self.registration_data())
        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(username="riya")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertEqual(user.student_id, "CSE-101")
        self.assertEqual(user.first_name, "Riya")
        self.assertFalse(user.is_staff)

    def test_public_form_does_not_expose_role(self):
        self.assertNotIn("role", self.client.get(self.url).context["form"].fields)

    def test_duplicate_username_is_rejected(self):
        create_user("riya", User.Role.STUDENT)
        response = self.client.post(self.url, self.registration_data())
        self.assertFormError(response.context["form"], "username", "A user with that username already exists.")

    def test_duplicate_email_is_rejected_case_insensitively(self):
        create_user("existing", User.Role.STUDENT, email="riya@example.com")
        response = self.client.post(self.url, self.registration_data())
        self.assertIn("already exists", response.context["form"].errors["email"][0])

    def test_duplicate_student_id_is_rejected_case_insensitively(self):
        create_user("existing", User.Role.STUDENT, student_id="CSE-101")
        response = self.client.post(self.url, self.registration_data())
        self.assertIn("already exists", response.context["form"].errors["student_id"][0])

    def test_authenticated_user_is_redirected_from_registration(self):
        self.client.force_login(create_user("signed-in", User.Role.STUDENT))
        self.assertRedirects(self.client.get(self.url), reverse("accounts:dashboard"), fetch_redirect_response=False)


class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = create_user("student", User.Role.STUDENT)

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(reverse("accounts:login"), {"username": "student", "password": PASSWORD})
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_invalid_login_uses_generic_error(self):
        response = self.client.post(reverse("accounts:login"), {"username": "student", "password": "wrong"})
        self.assertContains(response, "username or password is incorrect")

    def test_external_next_url_is_rejected(self):
        response = self.client.post(reverse("accounts:login") + "?next=https://evil.example/", {"username": "student", "password": PASSWORD, "next": "https://evil.example/"})
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)

    def test_safe_next_url_is_used(self):
        response = self.client.post(reverse("accounts:login"), {"username": "student", "password": PASSWORD, "next": reverse("accounts:profile")})
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_post_logout_ends_session(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post(reverse("accounts:logout")), reverse("core:landing"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('accounts:profile')}")

    def test_authenticated_user_is_redirected_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:login"))
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)


class DashboardPermissionTests(TestCase):
    routes = {
        User.Role.STUDENT: "accounts:student_dashboard",
        User.Role.STAFF: "accounts:staff_dashboard",
        User.Role.COORDINATOR: "accounts:admin_dashboard",
        User.Role.DEAN: "accounts:admin_dashboard",
        User.Role.ADMIN: "accounts:admin_dashboard",
        User.Role.SUPERADMIN: "accounts:admin_dashboard",
    }

    def setUp(self):
        self.users = {role: create_user(role.lower(), role) for role in User.Role.values}

    def test_dashboard_router_sends_each_role_to_correct_dashboard(self):
        for role, user in self.users.items():
            self.client.force_login(user)
            self.assertRedirects(self.client.get(reverse("accounts:dashboard")), reverse(self.routes[role]))

    def test_each_role_can_open_only_its_own_dashboard(self):
        for role, user in self.users.items():
            self.client.force_login(user)
            for destination_role, route in self.routes.items():
                response = self.client.get(reverse(route))
                same_dashboard = (
                    role == destination_role
                    or route == self.routes.get(role)
                )
                expected = 200 if same_dashboard else 403
                self.assertEqual(response.status_code, expected, f"{role} -> {destination_role}")
                if expected == 403:
                    self.assertTemplateUsed(response, "403.html")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_admin_counts_use_real_database_records(self):
        create_user("second-student", User.Role.STUDENT)
        self.client.force_login(self.users[User.Role.ADMIN])
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.context["counts"], {"total": 7, "students": 2, "staff": 1, "administrators": 1})


class ProfileAndPasswordTests(TestCase):
    def setUp(self):
        self.user = create_user("profile-user", User.Role.STAFF, employee_id="EMP-100", phone_number="111")
        self.client.force_login(self.user)

    def test_profile_update_cannot_change_role_or_identifiers(self):
        response = self.client.post(reverse("accounts:profile"), {"first_name": " Updated ", "last_name": " Person ", "phone_number": " 222 ", "department": " Facilities ", "role": User.Role.ADMIN, "employee_id": "HACKED", "student_id": "HACKED"})
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.STAFF)
        self.assertEqual(self.user.employee_id, "EMP-100")
        self.assertIsNone(self.user.student_id)
        self.assertEqual(self.user.department, "Facilities")

    def test_password_change_keeps_user_authenticated(self):
        response = self.client.post(reverse("accounts:password_change"), {"old_password": PASSWORD, "new_password1": "NewSecurePass456!", "new_password2": "NewSecurePass456!"})
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertIn("_auth_user_id", self.client.session)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePass456!"))


class DemoUsersCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_command_is_idempotent_and_refreshes_all_accounts(self):
        output = StringIO()
        call_command("create_demo_users", stdout=output)
        call_command("create_demo_users", stdout=output)
        self.assertEqual(User.objects.count(), len(DEMO_USERS))
        for definition in DEMO_USERS:
            self.assertTrue(User.objects.get(username=definition["username"]).check_password(definition["password"]))
        self.assertTrue(User.objects.get(username="admin_demo").is_superuser)
        self.assertFalse(User.objects.get(username="staff_demo").is_staff)

    @override_settings(DEBUG=False)
    def test_command_refuses_to_run_outside_debug_mode(self):
        with self.assertRaises(CommandError):
            call_command("create_demo_users")
