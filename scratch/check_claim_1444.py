import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import Claim, ClaimDocument, FraudRiskScore, PipelineTrace

def check_1444():
    db = next(get_db())
    try:
        claim = db.query(Claim).filter(Claim.claim_number == "CLM-2026-1444").first()
        if not claim:
            print("Claim CLM-2026-1444 not found!")
            return
            
        print(f"--- Claim details ---")
        print(f"ID: {claim.id} | Number: {claim.claim_number} | Status: {claim.status} | Policy ID: {claim.policy_id}")
        
        fraud = db.query(FraudRiskScore).filter(FraudRiskScore.claim_id == claim.id).first()
        if fraud:
            print(f"--- Fraud Risk details ---")
            print(f"Score: {fraud.fraud_score} | Risk Level: {fraud.risk_level} | Red Flags: {fraud.red_flags}")
            
        trace = db.query(PipelineTrace).filter(PipelineTrace.claim_id == claim.id).first()
        if trace:
            print(f"--- Pipeline Trace details ---")
            print(f"Outcome: {trace.outcome} | Outcome Message: {trace.outcome_msg}")
            
        docs = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()
        print(f"\n--- Documents for Claim ({len(docs)}) ---")
        for d in docs:
            print(f"ID: {d.id} | Filename: {d.filename} | Category: {d.category} | Extracted: {d.extracted_data}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_1444()
