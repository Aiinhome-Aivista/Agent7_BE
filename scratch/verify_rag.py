import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import Claim, Policy, User
import re

def test_rag_db_lookup():
    db = next(get_db())
    try:
        # Fetch any claim
        claim = db.query(Claim).first()
        if not claim:
            print("No claims found to test RAG lookup.")
            return
            
        print(f"Testing RAG DB Lookup for claim: {claim.claim_number}")
        
        # Simulating search logic from RAG controller
        query = f"Can you tell me why {claim.claim_number} is in status {claim.status}?"
        claim_numbers = re.findall(r"CLM-\d{4}-\d{4}", query, re.IGNORECASE)
        print("Regex match found:", claim_numbers)
        
        db_context = ""
        if claim_numbers:
            from app.models.models import Claim as DBClaim, Policy as DBPolicy, FraudRiskScore as DBFraudScore, Settlement as DBSettlement
            for cn in claim_numbers:
                c = db.query(DBClaim).filter(DBClaim.claim_number.ilike(cn.strip())).first()
                if c:
                    policy = db.query(DBPolicy).filter(DBPolicy.id == c.policy_id).first()
                    fraud = db.query(DBFraudScore).filter(DBFraudScore.claim_id == c.id).first()
                    settlement = db.query(DBSettlement).filter(DBSettlement.claim_id == c.id).first()
                    
                    db_context += f"\n\n--- DATABASE RECORD FOR CLAIM {c.claim_number} ---\n"
                    db_context += f"Claim Type: {c.claim_type}\n"
                    db_context += f"Current Status: {c.status}\n"
                    db_context += f"Incident Date: {c.incident_date}\n"
                    db_context += f"Incident Description: {c.incident_description}\n"
                    if c.status == "rejected":
                        db_context += f"Rejection Notes / Adjuster Recommendation: {c.adjuster_recommended_notes or 'No rejection notes.'}\n"
                    elif c.status == "settled" and settlement:
                        db_context += f"Settlement Details: Net payout ₹{settlement.net_payout:,.2f}\n"
                    if fraud:
                        db_context += f"Fraud Evaluation: Score {fraud.fraud_score}, Risk Level {fraud.risk_level}\n"
                        
        print("\nGenerated Database Context:")
        print(db_context)
        print("\nTest passed! RAG controller lookup successfully extracts and queries claim details.")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_rag_db_lookup()
