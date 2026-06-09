import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import Claim, FraudRiskScore

def check_fraud():
    db = next(get_db())
    try:
        claim = db.query(Claim).filter(Claim.claim_number == "CLM-2026-8109").first()
        if not claim:
            print("Claim not found!")
            return
        frs = db.query(FraudRiskScore).filter(FraudRiskScore.claim_id == claim.id).first()
        if frs:
            print(f"--- Fraud Risk Score for {claim.claim_number} (ID: {claim.id}) ---")
            print(f"Score: {frs.fraud_score}")
            print(f"Risk Level: {frs.risk_level}")
            print(f"Red Flags: {frs.red_flags}")
            print(f"Agent Reasoning: {frs.agent_reasoning}")
        else:
            print("No fraud risk score record found.")
            
        from app.models.models import PipelineTrace
        trace = db.query(PipelineTrace).filter(PipelineTrace.claim_id == claim.id).first()
        if trace:
            print(f"--- Pipeline Trace details ---")
            print(f"Outcome: {trace.outcome}")
            print(f"Outcome Msg: {trace.outcome_msg}")
            if trace.trace:
                for step in trace.trace:
                    if step.get("step") == "A5_Fraud_Risk_Scoring":
                        print(f"A5 Result: {step.get('result')}")
                    if step.get("step") == "A6_Settlement":
                        print(f"A6 Result: {step.get('result')}")
        else:
            print("No pipeline trace found.")
    finally:
        db.close()

if __name__ == "__main__":
    check_fraud()
