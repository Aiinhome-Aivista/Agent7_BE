import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import Claim, Policy, ClaimDocument, FraudRiskScore

def check_8109():
    db = next(get_db())
    try:
        claim = db.query(Claim).filter(Claim.claim_number == "CLM-2026-8109").first()
        if not claim:
            # Let's search using ilike
            claim = db.query(Claim).filter(Claim.claim_number.ilike("%8109%")).first()
            
        if not claim:
            print("Claim CLM-2026-8109 not found!")
            return
            
        print(f"--- Claim details ---")
        print(f"ID: {claim.id} | Number: {claim.claim_number} | Status: {claim.status} | Policy ID: {claim.policy_id}")
        
        policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
        if policy:
            print(f"--- Policy details ---")
            print(f"ID: {policy.id} | Number: {policy.policy_number} | Holder Name: {policy.policyholder_name} | DOB: {policy.date_of_birth}")
            
        fraud = db.query(FraudRiskScore).filter(FraudRiskScore.claim_id == claim.id).first()
        if fraud:
            print(f"--- Fraud Risk details ---")
            print(f"Score: {fraud.fraud_score} | Risk Level: {fraud.risk_level} | Red Flags: {fraud.red_flags}")
            
        docs = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()
        print(f"\n--- Documents for Claim ({len(docs)}) ---")
        for d in docs:
            print(f"ID: {d.id} | Filename: {d.filename} | Category: {d.category}")
            print(f"  Extracted Data: {d.extracted_data}")
            print(f"  Raw Text Snippet: {d.raw_text[:300] if d.raw_text else 'None'}")
            print("-" * 50)
            
    except Exception as e:
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    check_8109()
