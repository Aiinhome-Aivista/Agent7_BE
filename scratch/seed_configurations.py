import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import LOBMaster, ProductMaster, PolicyTypeMaster, InsuranceConfiguration

def run_migration():
    db = next(get_db())
    try:
        # 1. Fetch Health LOB
        health_lob = db.query(LOBMaster).filter(LOBMaster.lob_code == "HEALTH").first()
        if not health_lob:
            print("Error: HEALTH Line of Business not found in database.")
            return
        
        # 2. Fetch Products
        group_health = db.query(ProductMaster).filter(ProductMaster.product_code == "GROUP_HEALTH").first()
        ind_health = db.query(ProductMaster).filter(ProductMaster.product_code == "INDIVIDUAL_HEALTH").first()
        
        if not group_health or not ind_health:
            print("Error: Health products not found in database.")
            return

        # 3. Rules to apply
        doc_rules = {
            "mandatory": ["claim_form", "medical_report", "id_card"],
            "optional": ["test_report", "other"]
        }
        
        fraud_rules = {
            "rules": [
                {"code": "identity_verification_failed", "weightage": 0.30, "enabled": True},
                {"code": "claims_frequency_high_30d", "weightage": 0.25, "enabled": True},
                {"code": "claims_frequency_high_1yr", "weightage": 0.15, "enabled": True},
                {"code": "high_value_claim", "weightage": 0.20, "enabled": True},
                {"code": "suspicious_circumstances", "weightage": 0.15, "enabled": True},
                {"code": "vague_description", "weightage": 0.10, "enabled": True},
                {"code": "total_loss_claim", "weightage": 0.15, "enabled": True},
                {"code": "theft_claim", "weightage": 0.10, "enabled": True}
            ]
        }
        
        eligibility_rules = {
            "hospitalization_required": True,
            "minimum_hospitalization_hours": 24,
            "cashless_allowed": True,
            "reimbursement_allowed": True,
            "max_submission_days": 90
        }
        
        llm_rules = {
            "base_ratio": 0.85,
            "min_payout_pct": 10.0,
            "max_payout_pct": 95.0
        }

        # 4. Target Policy Types
        target_plans = [
            ("PREMIUM_GROUP", group_health.id),
            ("GOLD_PLAN", ind_health.id),
            ("SILVER_PLAN", ind_health.id),
            ("PLATINUM_PLAN", ind_health.id),
        ]

        print("Updating/Inserting configurations...")
        for plan_code, product_id in target_plans:
            pt = db.query(PolicyTypeMaster).filter(PolicyTypeMaster.policy_code == plan_code).first()
            if not pt:
                print(f"Warning: Policy type '{plan_code}' not found in policy_type_master. Skipping.")
                continue

            config = db.query(InsuranceConfiguration).filter(
                InsuranceConfiguration.policy_type_id == pt.id
            ).first()

            if not config:
                config = InsuranceConfiguration(
                    lob_id=health_lob.id,
                    product_id=product_id,
                    policy_type_id=pt.id,
                    document_rules=doc_rules,
                    fraud_rules=fraud_rules,
                    eligibility_rules=eligibility_rules,
                    llm_rules=llm_rules,
                    is_active=True
                )
                db.add(config)
                print(f"-> Added configuration for {plan_code}")
            else:
                config.document_rules = doc_rules
                config.fraud_rules = fraud_rules
                config.eligibility_rules = eligibility_rules
                config.llm_rules = llm_rules
                print(f"-> Updated existing configuration for {plan_code}")
        
        db.commit()
        print("Done! Configurations updated successfully in database.")
    except Exception as e:
        db.rollback()
        print(f"Error executing migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
