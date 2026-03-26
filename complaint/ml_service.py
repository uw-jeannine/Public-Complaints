import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import os
from django.conf import settings
from citizen.models import Complaint
from administrator.models import ComplaintCategory
from accounts.models import District

class ComplaintEscalationModel:
    MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'escalation_model.pkl')
    ENCODER_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'label_encoders.pkl')

    def __init__(self):
        self.model = None
        self.encoders = {}
        os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)

    def prepare_data(self, complaints_df):
        """Prepare features for training or prediction."""
        df = complaints_df.copy()
        
        # Categorical features
        cat_features = ['category', 'land_district']
        
        # For training, we need to fit the encoders
        for col in cat_features:
            if col not in self.encoders:
                self.encoders[col] = LabelEncoder()
                df[col] = self.encoders[col].fit_transform(df[col].astype(str))
            else:
                # Handle unknown categories during prediction
                df[col] = df[col].astype(str).map(lambda x: x if x in self.encoders[col].classes_ else self.encoders[col].classes_[0])
                df[col] = self.encoders[col].transform(df[col])
                
        # Numerical features
        # 1. Processing time (days since created)
        now = pd.Timestamp.now(tz='UTC')
        df['created_at_dt'] = pd.to_datetime(df['created_at'], utc=True)
        df['processing_days'] = (now - df['created_at_dt']).dt.days
        
        # 2. Description length
        df['desc_length'] = df['description'].str.len()
        
        return df[['category', 'land_district', 'processing_days', 'desc_length']]

    def train(self, complaints_qs=None):
        """Train the model using existing or synthetic data."""
        if complaints_qs is None:
            complaints_qs = Complaint.objects.all()
            
        if complaints_qs.count() < 10:
            print("Not enough data to train. Use synthetic data first.")
            return False

        data = []
        for c in complaints_qs:
            data.append({
                'category': str(c.category_id),
                'land_district': str(c.land_district_id),
                'created_at': c.created_at,
                'description': c.description,
                'target': 1 if c.is_escalated else 0
            })
            
        df = pd.DataFrame(data)
        X = self.prepare_data(df)
        y = df['target']
        
        self.model = LogisticRegression(random_state=42)
        self.model.fit(X, y)
        
        self.save_model()
        return True

    def save_model(self):
        joblib.dump(self.model, self.MODEL_PATH)
        joblib.dump(self.encoders, self.ENCODER_PATH)

    def load_model(self):
        if os.path.exists(self.MODEL_PATH) and os.path.exists(self.ENCODER_PATH):
            self.model = joblib.load(self.MODEL_PATH)
            self.encoders = joblib.load(self.ENCODER_PATH)
            return True
        return False

    def predict_risk(self, complaint):
        """Predict escalation probability for a single complaint."""
        if not self.model and not self.load_model():
            return 0.0
            
        df = pd.DataFrame([{
            'category': str(complaint.category_id),
            'land_district': str(complaint.land_district_id),
            'created_at': complaint.created_at,
            'description': complaint.description
        }])
        
        X = self.prepare_data(df)
        # Probabilities for class 0 and 1
        probs = self.model.predict_proba(X)[0]
        return float(probs[1]) # Return probability of escalation (class 1)

# Global instance
escalation_predictor = ComplaintEscalationModel()
