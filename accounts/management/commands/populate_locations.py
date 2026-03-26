import json
import urllib.request
import ssl
from django.core.management.base import BaseCommand
from accounts.models import Province, District, Sector, Village

class Command(BaseCommand):
    help = 'Populate Rwanda provinces, districts, sectors, and villages'

    def handle(self, *args, **options):
        url = "https://raw.githubusercontent.com/ngabovictor/Rwanda/master/data.json"
        self.stdout.write(f"Downloading data from {url}...")
        
        context = ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(url, context=context) as response:
                data = json.loads(response.read().decode())
        except Exception as e:
            self.stderr.write(f"Failed to download data: {e}")
            return

        self.stdout.write("Populating database...")
        
        # Province mapping for better names if needed, but JSON keys are fine
        province_names = {
            "East": "Eastern Province",
            "West": "Western Province",
            "North": "Northern Province",
            "South": "Southern Province",
            "Kigali": "Kigali City"
        }

        for p_key, districts in data.items():
            p_name = province_names.get(p_key, p_key)
            province, _ = Province.objects.get_or_create(name=p_name)
            self.stdout.write(f"  Province: {p_name}")

            for d_name, sectors in districts.items():
                district, _ = District.objects.get_or_create(province=province, name=d_name)
                
                for s_name, cells in sectors.items():
                    sector, _ = Sector.objects.get_or_create(district=district, name=s_name)
                    
                    # Flatten villages from cells
                    villages_list = []
                    for cell_name, villages in cells.items():
                        for v_name in villages:
                            villages_list.append(Village(sector=sector, name=v_name))
                    
                    if villages_list:
                        # Use bulk_create for efficiency but filter out existing ones manually or just clear before
                        # For simplicity in this script, let's just create if not exists
                        # But bulk_create is much faster for 14k villages.
                        # Let's check existing villages for this sector
                        existing_villages = set(Village.objects.filter(sector=sector).values_list('name', flat=True))
                        to_create = [v for v in villages_list if v.name not in existing_villages]
                        if to_create:
                            Village.objects.bulk_create(to_create)

        self.stdout.write(self.style.SUCCESS("Successfully populated Rwanda locations!"))
