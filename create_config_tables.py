import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import engine, get_db
from app.models.models import Base, LOBMaster, ProductMaster, PolicyTypeMaster, DocumentMaster, FraudRuleMaster, InsuranceConfiguration

def create_and_seed():
    # 1. Create tables
    print("Creating tables in database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

    db = next(get_db())
    try:
        # 2. Seed LOB Master
        print("Seeding LOB Master...")
        health_lob = db.query(LOBMaster).filter(LOBMaster.lob_code == "HEALTH").first()
        if not health_lob:
            health_lob = LOBMaster(lob_code="HEALTH", lob_name="Health Insurance")
            db.add(health_lob)
            
        auto_lob = db.query(LOBMaster).filter(LOBMaster.lob_code == "AUTO").first()
        if not auto_lob:
            auto_lob = LOBMaster(lob_code="AUTO", lob_name="Motor Insurance")
            db.add(auto_lob)
            
        property_lob = db.query(LOBMaster).filter(LOBMaster.lob_code == "PROPERTY").first()
        if not property_lob:
            property_lob = LOBMaster(lob_code="PROPERTY", lob_name="Property Insurance")
            db.add(property_lob)
            
        db.commit()
        health_lob_id = health_lob.id

        # 3. Seed Product Master
        print("Seeding Product Master...")
        group_health = db.query(ProductMaster).filter(ProductMaster.product_code == "GROUP_HEALTH").first()
        if not group_health:
            group_health = ProductMaster(lob_id=health_lob_id, product_code="GROUP_HEALTH", product_name="Group Health Insurance")
            db.add(group_health)
            
        ind_health = db.query(ProductMaster).filter(ProductMaster.product_code == "INDIVIDUAL_HEALTH").first()
        if not ind_health:
            ind_health = ProductMaster(lob_id=health_lob_id, product_code="INDIVIDUAL_HEALTH", product_name="Individual Health Insurance")
            db.add(ind_health)
            
        fam_health = db.query(ProductMaster).filter(ProductMaster.product_code == "FAMILY_FLOATER").first()
        if not fam_health:
            fam_health = ProductMaster(lob_id=health_lob_id, product_code="FAMILY_FLOATER", product_name="Family Floater Health Insurance")
            db.add(fam_health)
            
        db.commit()
        group_health_id = group_health.id
        ind_health_id = ind_health.id
        fam_health_id = fam_health.id

        # 4. Seed Policy Type Master
        print("Seeding Policy Type Master...")
        policy_types = [
            (group_health_id, "PREMIUM_GROUP", "Premium Group"),
            (group_health_id, "CORPORATE_GROUP", "Corporate Group"),
            (group_health_id, "SME_GROUP", "SME Group"),
            
            (ind_health_id, "GOLD_PLAN", "Gold Plan"),
            (ind_health_id, "SILVER_PLAN", "Silver Plan"),
            (ind_health_id, "PLATINUM_PLAN", "Platinum Plan"),
            
            (fam_health_id, "BASIC", "Basic Family"),
            (fam_health_id, "PREMIUM", "Premium Family")
        ]
        policy_type_ids = {}
        for product_id, code, name in policy_types:
            pt = db.query(PolicyTypeMaster).filter(PolicyTypeMaster.policy_code == code).first()
            if not pt:
                pt = PolicyTypeMaster(product_id=product_id, policy_code=code, policy_name=name)
                db.add(pt)
                db.flush()
            policy_type_ids[code] = pt.id
        db.commit()

        # 5. Seed Document Master
        print("Seeding Document Master...")
        docs = [
            ("claim_form", "📝 Claim Form", "Standard claim submission form"),
            ("medical_report", "🏥 Medical Report", "Hospital diagnosis report"),
            ("test_report", "🔬 Test Report", "Lab test results and reports"),
            ("id_card", "🆔 ID Card", "Identity proof card"),
            ("fir_copy", "📄 FIR Copy", "First Information Report from Police (primarily Auto/Theft)"),
            ("other", "📄 Other Document", "Other auxiliary documents")
        ]
        for code, name, desc in docs:
            d = db.query(DocumentMaster).filter(DocumentMaster.document_code == code).first()
            if not d:
                d = DocumentMaster(document_code=code, document_name=name, description=desc)
                db.add(d)
        db.commit()

        # 6. Seed Fraud Rules
        print("Seeding Fraud Rules...")
        rules = [
            ("identity_verification_failed", "Identity Verification Failed", 0.30),
            ("claims_frequency_high_30d", "High Claims Frequency (30 Days)", 0.25),
            ("claims_frequency_high_1yr", "High Claims Frequency (1 Year)", 0.15),
            ("high_value_claim", "High Value Claim (> 60% of cover)", 0.20),
            ("suspicious_circumstances", "Suspicious Keywords in Description", 0.15),
            ("vague_description", "Vague Incident Description", 0.10),
            ("total_loss_claim", "Total Loss Severity", 0.15),
            ("theft_claim", "Theft Claim Type", 0.10)
        ]
        for code, name, weight in rules:
            r = db.query(FraudRuleMaster).filter(FraudRuleMaster.rule_code == code).first()
            if not r:
                r = FraudRuleMaster(rule_code=code, rule_name=name, default_weightage=weight)
                db.add(r)
        db.commit()

        # 7. Seed Main Configuration for PREMIUM_GROUP Health Policy
        print("Seeding Insurance Configurations...")
        prem_group_id = policy_type_ids["PREMIUM_GROUP"]
        
        config = db.query(InsuranceConfiguration).filter(
            InsuranceConfiguration.policy_type_id == prem_group_id
        ).first()
        
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

        if not config:
            config = InsuranceConfiguration(
                lob_id=health_lob_id,
                product_id=group_health_id,
                policy_type_id=prem_group_id,
                document_rules=doc_rules,
                fraud_rules=fraud_rules,
                eligibility_rules=eligibility_rules,
                llm_rules=llm_rules,
                is_active=True
            )
            db.add(config)
            print("Successfully added configuration for HEALTH -> GROUP_HEALTH -> PREMIUM_GROUP.")
        else:
            config.document_rules = doc_rules
            config.fraud_rules = fraud_rules
            config.eligibility_rules = eligibility_rules
            config.llm_rules = llm_rules
            print("Updated existing configuration for HEALTH -> GROUP_HEALTH -> PREMIUM_GROUP.")
            
        db.commit()
        print("Configuration seeded completely.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding config: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_and_seed()
