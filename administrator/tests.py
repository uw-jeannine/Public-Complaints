from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Office, ComplaintCategory
from citizen.models import Complaint
from accounts.models import Province, District

User = get_user_model()

class AdminReportsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='password123',
            email='admin@example.com',
            phone_number='0780000000',
            user_type='administrator'
        )
        self.citizen_user = User.objects.create_user(
            username='citizen',
            password='password123',
            email='citizen@example.com',
            phone_number='0781111111',
            user_type='citizen'
        )
        
        self.province = Province.objects.create(name="Kigali")
        self.district = District.objects.create(name="Nyarugenge", province=self.province)
        self.category = ComplaintCategory.objects.create(name="Land Conflict", is_active=True)
        
        # Create some complaints
        Complaint.objects.create(
            full_name="John Doe",
            gender="male",
            phone_number="0781234567",
            email="john@example.com",
            national_id="1199000000000000",
            residence_province=self.province,
            residence_district=self.district,
            category=self.category,
            description="Test complaint",
            status="pending"
        )

    def test_admin_reports_access_denied_for_citizen(self):
        self.client.login(username='citizen', password='password123')
        response = self.client.get(reverse('admin_reports'))
        # Should redirect to login or show 403 depending on administrator_required implementation
        self.assertNotEqual(response.status_code, 200)

    def test_admin_reports_access_allowed_for_admin(self):
        self.client.login(username='admin', password='password123')
        response = self.client.get(reverse('admin_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/admin_reports.html')

    def test_admin_reports_contains_data(self):
        self.client.login(username='admin', password='password123')
        response = self.client.get(reverse('admin_reports'))
        self.assertIn('resilience_provinces', response.context)
        self.assertIn('resilience_districts', response.context)
        self.assertEqual(len(response.context['resilience_provinces']), 1)
        self.assertEqual(response.context['resilience_provinces'][0].total_complaints, 1)
