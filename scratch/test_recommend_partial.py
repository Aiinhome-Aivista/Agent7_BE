import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import Claim, User as DBUser, ClaimDocument
from app.controllers.claims_controller import get_partial_recommendation

def run_test():
    db = next(get_db())
    temp_doc = None
    try:
        # Find a claim
        claim = db.query(Claim).first()
        if not claim:
            print("No claims found in the database!")
            return
            
        print(f"=== TEST 1: Normal Partial Recommendation for Claim ID {claim.id} ===")
        # Mock adjuster user
        mock_user = DBUser(role="adjuster", full_name="Test Adjuster")
        
        # Run standard recommendation
        res = get_partial_recommendation(claim_id=claim.id, current_user=mock_user, db=db)
        print("Standard Response:")
        print(f"Recommended Percentage: {res.recommended_percentage}%")
        print(f"Recommended Amount: ₹{res.recommended_amount:,.2f}")
        print(f"Explanation: {res.explanation}\n")

        print("=== TEST 2: Identity Verification Failed early return ===")
        # Insert temporary verification-failed document
        temp_doc = ClaimDocument(
            claim_id=claim.id,
            policy_id=claim.policy_id,
            user_id=claim.claimant_id,
            filename="temp_fail_id.jpg",
            file_path="/uploads/temp_fail_id.jpg",
            category="id_card",
            extracted_data={"id_verified": False}
        )
        db.add(temp_doc)
        db.commit()

        # Run recommendation again
        res_fail = get_partial_recommendation(claim_id=claim.id, current_user=mock_user, db=db)
        print("Failure Response:")
        print(f"Recommended Percentage: {res_fail.recommended_percentage}%")
        print(f"Recommended Amount: ₹{res_fail.recommended_amount:,.2f}")
        print(f"Explanation: {res_fail.explanation}\n")
        
        if res_fail.recommended_amount == 0.0 and res_fail.recommended_percentage == 0.0:
            print("SUCCESS: Identity verification failure correctly returned 0.0 amount and percentage!")
        else:
            print("FAILED: Identity verification failure did not return 0.0 amount and percentage!")

    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if temp_doc:
            db.delete(temp_doc)
            db.commit()
        db.close()

if __name__ == "__main__":
    run_test()
