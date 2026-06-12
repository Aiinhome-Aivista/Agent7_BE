import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal
from app.models.models import Claim

print("Connecting to DB...")
db = SessionLocal()
try:
    print("Executing query...")
    count = db.query(Claim).count()
    print(f"Connection successful! Claim count: {count}")
    
    first_claim = db.query(Claim).first()
    if first_claim:
        print(f"First claim ID: {first_claim.id}")
    else:
        print("No claims found.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
