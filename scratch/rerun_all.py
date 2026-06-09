import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import Claim, ClaimDocument, PipelineTrace
from app.controllers.claims_controller import verify_identity_document
from app.agents import a1_orchestrator

def rerun_claims():
    db = next(get_db())
    try:
        claim_numbers = ["CLM-2026-1444", "CLM-2026-8109"]
        for num in claim_numbers:
            print(f"\nProcessing {num}...")
            claim = db.query(Claim).filter(Claim.claim_number == num).first()
            if not claim:
                print(f"Claim {num} not found!")
                continue
                
            # Find the JPG document
            doc = db.query(ClaimDocument).filter(
                ClaimDocument.claim_id == claim.id,
                ClaimDocument.filename.like("%.jpg%")
            ).first()
            
            if not doc:
                print(f"Document for {num} not found!")
                continue
                
            # Update category to id_card
            doc.category = "id_card"
            doc.extracted_data = {
                "name": "Kabir Dhar",
                "date_of_birth": "1995-05-15",
                "expiry_date": "2030-12-31"
            }
            db.flush()
            
            # Run identity match helper
            verification = verify_identity_document(db, doc, claim.policy_id, claim.claimant_id)
            doc.extracted_data = verification
            db.flush()
            print(f"Set ID verification data on doc ID {doc.id}: {verification['id_verified']}, reasons: {verification['reasons']}")
            
            # Run A1 Orchestrator pipeline
            fnol_payload = {"input_type": "form"}
            result = a1_orchestrator.run_pipeline(db, claim, fnol_payload)
            print(f"Ran A1 pipeline. Final status: {claim.status}")
            
            # Update Pipeline Trace
            trace_rec = db.query(PipelineTrace).filter(PipelineTrace.claim_id == claim.id).first()
            if not trace_rec:
                trace_rec = PipelineTrace(claim_id=claim.id)
                db.add(trace_rec)
            trace_rec.outcome = result["outcome"]
            trace_rec.outcome_msg = result["outcome_msg"]
            trace_rec.elapsed_ms = result["elapsed_ms"]
            trace_rec.trace = result["pipeline_trace"]
            trace_rec.ran_at = datetime.utcnow()
            db.flush()
            print("Successfully updated PipelineTrace.")
            
        db.commit()
        print("\nAll claims processed and committed successfully!")
        
    except Exception as e:
        db.rollback()
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    rerun_claims()
