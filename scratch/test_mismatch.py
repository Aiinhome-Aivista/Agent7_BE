import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import Claim, ClaimDocument, Policy
from app.controllers.claims_controller import verify_identity_document
from app.agents import a3_coverage, a5_fraud

def run_test():
    db = next(get_db())
    try:
        # Find claim CLM-2026-8109
        claim = db.query(Claim).filter(Claim.claim_number == "CLM-2026-8109").first()
        if not claim:
            print("Claim not found!")
            return
            
        print(f"Claim found: {claim.claim_number} (ID: {claim.id})")
        
        # Find the uploaded JPG document (ID: 165)
        doc = db.query(ClaimDocument).filter(
            ClaimDocument.claim_id == claim.id,
            ClaimDocument.filename.like("%.jpg%")
        ).first()
        
        if not doc:
            print("Uploaded JPG document not found!")
            return
            
        print(f"Document found: {doc.filename} (ID: {doc.id}, Current Category: {doc.category})")
        
        # 1. Update category to id_card
        doc.category = "id_card"
        # Mock Kabir Dhar ID details in extracted_data (simulating what Pixtral/Mistral extracts from Kabir Dhar's card)
        doc.extracted_data = {
            "name": "Kabir Dhar",
            "date_of_birth": "1995-05-15",
            "expiry_date": "2030-12-31"
        }
        db.flush()
        print(f"Updated document category to 'id_card' and set extracted details for Kabir Dhar.")
        
        # 2. Run verification helper
        print("Running verify_identity_document...")
        verification = verify_identity_document(db, doc, claim.policy_id, claim.claimant_id)
        print("Verification Output:")
        print(verification)
        
        doc.extracted_data = verification
        db.flush()
        
        # 3. Run Fraud scoring
        print("Running A3 Coverage check...")
        a3_res = a3_coverage.run(db, claim)
        
        print("Running A5 Fraud Agent...")
        dummy_damage_res = {"status": "success", "net_estimate": 10000.0, "severity": "moderate"}
        a5_res = a5_fraud.run(db, claim, a3_res, dummy_damage_res)
        print("A5 Fraud Agent Output:")
        print(f"Fraud Score: {a5_res.get('fraud_score')}")
        print(f"Risk Level: {a5_res.get('risk_level')}")
        print(f"Red Flags: {a5_res.get('red_flags')}")
        
        db.commit()
        print("\nSuccessfully updated database and committed changes.")
        
    except Exception as e:
        db.rollback()
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    run_test();
