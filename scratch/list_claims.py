import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import Claim, Policy, ClaimDocument

def list_claims():
    db = next(get_db())
    try:
        policies = db.query(Policy).all()
        print(f"--- Policies ({len(policies)}) ---")
        for p in policies:
            print(f"ID: {p.id} | Number: {p.policy_number} | Holder: {p.policyholder_name} | Type: {p.policy_type}")
            
        claims = db.query(Claim).all()
        print(f"\n--- Claims ({len(claims)}) ---")
        for c in claims:
            print(f"ID: {c.id} | Number: {c.claim_number} | Policy ID: {c.policy_id} | Status: {c.status} | Type: {c.claim_type}")
            
        docs = db.query(ClaimDocument).all()
        print(f"\n--- Documents ({len(docs)}) ---")
        for d in docs:
            print(f"ID: {d.id} | Claim ID: {d.claim_id} | Name: {d.filename} | Category: {d.category} | Extracted: {d.extracted_data}")
    except Exception as e:
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    list_claims()
