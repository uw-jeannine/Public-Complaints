from django.db import models
from django.contrib.auth.models import AbstractUser

class Province(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class District(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Sector(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='sectors')
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Village(models.Model):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='villages')
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class User(AbstractUser):
    """
    Custom User model. username, password, and email are inherited from AbstractUser.
    """
    
    CITIZEN = 'citizen'
    OFFICE = 'office'
    ADMINISTRATOR = 'administrator'

    # User type choices
    USER_TYPE_CHOICES = (
        (CITIZEN, 'Citizen'),
        (OFFICE, 'Office'),
        (ADMINISTRATOR, 'Administrator'),
    )

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    national_id = models.CharField(max_length=20, blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default=CITIZEN)
    # Location fields
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True)
    local_address = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    # For office-type users: which office they belong to
    office = models.ForeignKey(
        'administrator.Office',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='staff_users',
        help_text='Applicable for office-type users only'
    )

    REQUIRED_FIELDS = ['phone_number', 'full_name']

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"



    @property
    def is_citizen(self):
        return self.user_type == self.CITIZEN

    @property
    def is_office(self):
        return self.user_type == self.OFFICE

    @property
    def is_administrator(self):
        return self.user_type == self.ADMINISTRATOR