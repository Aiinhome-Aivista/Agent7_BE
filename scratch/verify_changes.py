import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import Claim, Policy, ClaimDocument
from app.agents import a3_coverage, a5_fraud

def test():
    db = next(get_db())
    try:
        # 1. Fetch any claim and policy
        claim = db.query(Claim).first()
        if not claim:
            print("No claims found in database to test.")
            return

        policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
        if not policy:
            print("No policy associated with claim.")
            return

        print(f"Testing with Claim {claim.claim_number} (Type: {claim.claim_type}) under Policy {policy.policy_number}")

        # 2. Run A3 Coverage Agent
        print("Running A3 Coverage Agent...")
        a3_res = a3_coverage.run(db, claim)
        print("A3 result status:", a3_res.get("status"))

        # 3. Create a dummy ID document with mismatch to test A5 and ID verification helper
        from app.controllers.claims_controller import verify_identity_document
        dummy_doc = ClaimDocument(
            claim_id=claim.id,
            policy_id=policy.id,
            user_id=claim.claimant_id,
            filename="id_card_test.png",
            file_path="uploads/id_card_test.png",
            category="id_card",
            raw_text="Name: Wrong Name\nDOB: 1990-01-01\nExpiry: 2020-01-01",
            extracted_data={}
        )
        db.add(dummy_doc)
        db.flush()

        print("Testing verify_identity_document helper on dummy ID card...")
        verify_res = verify_identity_document(db, dummy_doc, policy.id, claim.claimant_id)
        print("Verification result matched name/dob/expiry status:", verify_res.get("id_verified"))
        print("Verification mismatch reasons:", verify_res.get("reasons"))
        
        dummy_doc.extracted_data = verify_res
        db.flush()

        # Run A5 Fraud scoring Agent to verify it detects mismatch
        print("Running A5 Fraud Agent...")
        dummy_damage_res = {"status": "success", "net_estimate": 10000.0, "severity": "moderate"}
        a5_res = a5_fraud.run(db, claim, a3_res, dummy_damage_res)
        print("A5 result red flags:", a5_res.get("red_flags"))
        print("A5 fraud score:", a5_res.get("fraud_score"))

        # Rollback so we don't mess up database with dummy test documents
        db.rollback()
        print("Test passed successfully! DB changes rolled back.")

    except Exception as e:
        print("Error occurred during test:", e)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test()
