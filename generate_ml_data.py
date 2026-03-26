import os
import django
import random
import pandas as pd
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'complaint.settings')
django.setup()

from citizen.models import Complaint
from administrator.models import ComplaintCategory
from accounts.models import District, Province

def generate_synthetic_data(count=100):
    categories = list(ComplaintCategory.objects.all())
    districts = list(District.objects.all())
    
    if not categories or not districts:
        print("Please ensure categories and districts exist in DB.")
        return

    # Clear existing synthetic data if needed or just add more
    print(f"Generating {count} synthetic complaints...")
    
    for _ in range(count):
        cat = random.choice(categories)
        dist = random.choice(districts)
        
        # Some logic for "escalated" bias
        # Let's say category 'Boundary Dispute' (id usually small) is more likely to escalate
        is_high_risk_cat = "boundary" in cat.name.lower() or "expropriation" in cat.name.lower()
        
        # Logic for escalation
        is_escalated = False
        if is_high_risk_cat and random.random() > 0.4:
            is_escalated = True
        elif random.random() > 0.8:
            is_escalated = True
            
        # Logic for appeal
        is_appeal = random.random() > 0.8 # 20% chance of being an appeal
            
        # Create complaint
        c = Complaint.objects.create(
            full_name=f"Synthetic User {random.randint(1, 1000)}",
            gender=random.choice(['male', 'female']),
            phone_number=f"078{random.randint(1000000, 9999999)}",
            email=f"synthetic{random.randint(1, 1000)}@example.com",
            national_id=f"1199{random.randint(100000000000, 999999999999)}",
            land_district=dist,
            land_province=dist.province,
            category=cat,
            description=f"This is a synthetic complaint about {cat.name} in {dist.name}. " * random.randint(1, 5),
            upi=f"{random.randint(1, 5)}/{random.randint(100, 999)}/{random.randint(1000, 9999)}",
            is_escalated=is_escalated,
            is_appeal=is_appeal,
            status=random.choice(['pending', 'in_progress', 'resolved'])
        )
        
        # Random assignment if in progress or resolved
        if c.status in ['in_progress', 'resolved']:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(user_type='administrator')
            if admins.exists():
                c.assigned_to = random.choice(admins)
                c.assigned_at = c.created_at + timedelta(hours=random.randint(1, 24))
        
        # Random resolution if resolved
        if c.status == 'resolved':
            c.resolved_at = c.assigned_at + timedelta(days=random.randint(1, 7)) if c.assigned_at else c.created_at + timedelta(days=random.randint(1, 7))
            c.resolution_details = "The dispute was investigated and resolved in favor of the rightful owner based on land registry records."
        
        # Adjust created_at back in time
        c.created_at = timezone.now() - timedelta(days=random.randint(0, 30))
        c.save()

    print("Success. Now training model...")
    from complaint.ml_service import escalation_predictor
    if escalation_predictor.train():
        print("Model trained and saved successfully.")
    else:
        print("Model training failed.")

if __name__ == "__main__":
    generate_synthetic_data(100)
