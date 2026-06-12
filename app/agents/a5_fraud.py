"""
A5 — Fraud & Risk Scoring Agent
Rule-based scoring driven by dynamic database configurations.
Red flags accumulate based on active weights to produce a 0-1 fraud score.
"""

from sqlalchemy.orm import Session
from app.models.models import FraudRiskScore, Claim, Policy, InsuranceConfiguration, PolicyTypeMaster, LOBMaster
from datetime import datetime, date


def run(db: Session, claim: Claim, coverage_result: dict, damage_result: dict) -> dict:
    red_flags = []
    score = 0.0

    desc = (claim.incident_description or "").lower()
    net_estimate = damage_result.get("net_estimate", 0)
    coverage_limit = coverage_result.get("coverage_limit", 999_999)

    # 1. Fetch dynamic LOB and Policy Type configuration from DB
    policy = db.query(Policy).filter(Policy.id == claim.policy_id).first()
    lob_code = (policy.policy_type or "health").upper() if policy else "HEALTH"
    
    plan_code = "PREMIUM_GROUP"
    if policy and policy.plan_name:
        plan_code = policy.plan_name.strip().upper().replace(" ", "_")

    config = None
    if policy:
        config = db.query(InsuranceConfiguration).join(
            PolicyTypeMaster, PolicyTypeMaster.id == InsuranceConfiguration.policy_type_id
        ).join(
            LOBMaster, LOBMaster.id == InsuranceConfiguration.lob_id
        ).filter(
            LOBMaster.lob_code == lob_code,
            PolicyTypeMaster.policy_code == plan_code,
            InsuranceConfiguration.is_active == True
        ).first()

    # Fallback to HEALTH PREMIUM_GROUP if no specific config is found
    if not config:
        config = db.query(InsuranceConfiguration).join(
            PolicyTypeMaster, PolicyTypeMaster.id == InsuranceConfiguration.policy_type_id
        ).filter(
            PolicyTypeMaster.policy_code == "PREMIUM_GROUP",
            InsuranceConfiguration.is_active == True
        ).first()

    # 2. Build rules map from the active configuration
    rule_map = {}
    if config and config.fraud_rules and "rules" in config.fraud_rules:
        for r in config.fraud_rules["rules"]:
            if r.get("enabled", True):
                rule_map[r["code"]] = float(r.get("weightage", 0.0))
    else:
        # Hardcoded fallback if no config is available in database
        rule_map = {
            "identity_verification_failed": 0.30,
            "claims_frequency_high_30d": 0.25,
            "claims_frequency_high_1yr": 0.15,
            "high_value_claim": 0.20,
            "suspicious_circumstances": 0.15,
            "vague_description": 0.10,
            "total_loss_claim": 0.15,
            "theft_claim": 0.10
        }

    # 3. Evaluate active rules

    # Rule: High value claim (> 60% of coverage limit)
    if "high_value_claim" in rule_map:
        if net_estimate > coverage_limit * 0.6:
            red_flags.append("high_value_claim")
            score += rule_map["high_value_claim"]

    # Rule: Night / suspicious keywords
    if "suspicious_circumstances" in rule_map:
        if any(w in desc for w in ["night", "midnight", "abandoned", "stolen", "nobody"]):
            red_flags.append("suspicious_circumstances")
            score += rule_map["suspicious_circumstances"]

    # Rule: Vague description
    if "vague_description" in rule_map:
        if len(desc.split()) < 10:
            red_flags.append("vague_description")
            score += rule_map["vague_description"]

    # Rule: Total loss
    if "total_loss_claim" in rule_map:
        if damage_result.get("severity") == "total":
            red_flags.append("total_loss_claim")
            score += rule_map["total_loss_claim"]

    # Rule: Theft type
    if "theft_claim" in rule_map:
        if claim.claim_type == "theft":
            red_flags.append("theft_claim")
            score += rule_map["theft_claim"]

    # Rule: Repeated/High-frequency claim pattern check
    from app.models.models import Claim as DBClaim
    from datetime import timedelta
    
    one_year_ago = datetime.utcnow() - timedelta(days=365)
    past_claims_1yr = db.query(DBClaim).filter(
        DBClaim.claimant_id == claim.claimant_id,
        DBClaim.created_at >= one_year_ago,
        DBClaim.id != claim.id
    ).count()

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    past_claims_30d = db.query(DBClaim).filter(
        DBClaim.claimant_id == claim.claimant_id,
        DBClaim.created_at >= thirty_days_ago,
        DBClaim.id != claim.id
    ).count()

    if past_claims_30d >= 1 and "claims_frequency_high_30d" in rule_map:
        red_flags.append("claims_frequency_high_30d")
        score += rule_map["claims_frequency_high_30d"]
    elif past_claims_1yr >= 3 and "claims_frequency_high_1yr" in rule_map:
        red_flags.append("claims_frequency_high_1yr")
        score += rule_map["claims_frequency_high_1yr"]

    # Rule: Identity proof mismatch/verification failed check
    from app.models.models import ClaimDocument
    id_docs = db.query(ClaimDocument).filter(
        ClaimDocument.claim_id == claim.id,
        ClaimDocument.category == "id_card"
    ).order_by(ClaimDocument.id.desc()).all()
    
    id_verified_flag = True
    has_id_doc = False

    if id_docs:
        has_id_doc = True
        latest_doc = id_docs[0]
        ext_data = latest_doc.extracted_data or {}
        if ext_data and not ext_data.get("id_verified", True):
            id_verified_flag = False

    if has_id_doc and not id_verified_flag and "identity_verification_failed" in rule_map:
        red_flags.append("identity_verification_failed")
        score += rule_map["identity_verification_failed"]

    score = min(score, 1.0)

    siu_referral_threshold = 0.70
    adjuster_flag_threshold = 0.45

    if score >= siu_referral_threshold:
        risk_level = "critical"
        siu_referred = True
    elif score >= adjuster_flag_threshold:
        risk_level = "high"
        siu_referred = False
    elif score >= 0.20:
        risk_level = "medium"
        siu_referred = False
    else:
        risk_level = "low"
        siu_referred = False

    # Calculate dynamic payout ratio (maximum 85%) and deduct based on issues
    base_ratio = 0.85
    if config and config.llm_rules:
        base_ratio = float(config.llm_rules.get("base_ratio", 0.85))

    ratio_reduction = (score * 0.5) + (len(red_flags) * 0.05)
    final_ratio = max(0.10, base_ratio - ratio_reduction)
    recommended_payout = round(net_estimate * final_ratio, 2)

    # If identity proof is invalid, suggested payout is 0.0
    if has_id_doc and not id_verified_flag:
        final_ratio = 0.0
        recommended_payout = 0.0

    result = {
        "agent": "A5_Fraud_Risk_Scoring",
        "status": "success",
        "fraud_score": round(score, 4),
        "risk_level": risk_level,
        "red_flags": red_flags,
        "siu_referred": siu_referred,
        "auto_settle": False,
        "recommended_payout": recommended_payout,
        "payout_ratio": round(final_ratio, 4),
        "message": f"Fraud score: {score:.2f} ({risk_level} risk). Recommended payout: ₹{recommended_payout:,.2f} ({final_ratio*100:.1f}% of estimate). {'⚠ SIU referral triggered.' if siu_referred else 'Adjuster review recommended.'}",
    }

    # Persist
    try:
        frs = (
            db.query(FraudRiskScore).filter(FraudRiskScore.claim_id == claim.id).first()
        )
        if not frs:
            frs = FraudRiskScore(claim_id=claim.id)
            db.add(frs)
        frs.fraud_score = round(score, 4)
        frs.risk_level = risk_level
        frs.red_flags = red_flags
        frs.siu_referred = siu_referred
        frs.agent_reasoning = str(red_flags)
        frs.scored_at = datetime.utcnow()
        if siu_referred:
            frs.siu_referred_at = datetime.utcnow()
        db.flush()
    except Exception:
        pass

    return result
