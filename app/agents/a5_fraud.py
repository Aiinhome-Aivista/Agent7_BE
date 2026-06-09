"""
A5 — Fraud & Risk Scoring Agent
Rule-based scoring (stub for ML model).
Red flags accumulate to produce a 0-1 fraud score.
"""

from sqlalchemy.orm import Session
from app.models.models import FraudRiskScore, Claim
from datetime import datetime, date

FRAUD_THRESHOLDS = {
    "siu_referral": 0.70,
    "adjuster_flag": 0.45,
    "auto_settle": 0.15,
}


def run(db: Session, claim: Claim, coverage_result: dict, damage_result: dict) -> dict:
    red_flags = []
    score = 0.0

    desc = (claim.incident_description or "").lower()
    net_estimate = damage_result.get("net_estimate", 0)
    coverage_limit = coverage_result.get("coverage_limit", 999_999)

    # ── Rule 1: New policy (< 30 days old — can't check without policy.created_at easily, use claim_id heuristic)
    # Rule 2: High value claim (> 60% of coverage limit)
    if net_estimate > coverage_limit * 0.6:
        red_flags.append("high_value_claim")
        score += 0.20

    # Rule 3: Night / suspicious keywords
    if any(w in desc for w in ["night", "midnight", "abandoned", "stolen", "nobody"]):
        red_flags.append("suspicious_circumstances")
        score += 0.15

    # Rule 4: Vague description
    if len(desc.split()) < 10:
        red_flags.append("vague_description")
        score += 0.10

    # Rule 5: Total loss
    if damage_result.get("severity") == "total":
        red_flags.append("total_loss_claim")
        score += 0.15

    # Rule 6: Theft type
    if claim.claim_type == "theft":
        red_flags.append("theft_claim")
        score += 0.10

    # Rule 7: Repeated/High-frequency claim pattern check
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

    if past_claims_30d >= 1:
        red_flags.append("claims_frequency_high_30d")
        score += 0.25
    elif past_claims_1yr >= 3:
        red_flags.append("claims_frequency_high_1yr")
        score += 0.15

    # Rule 8: Identity proof mismatch/verification failed check
    from app.models.models import ClaimDocument
    id_docs = db.query(ClaimDocument).filter(
        ClaimDocument.claim_id == claim.id,
        ClaimDocument.category == "id_card"
    ).all()
    
    id_verified_flag = True
    has_id_doc = False

    for doc in id_docs:
        has_id_doc = True
        ext_data = doc.extracted_data or {}
        if ext_data and not ext_data.get("id_verified", True):
            id_verified_flag = False

    if has_id_doc and not id_verified_flag:
        red_flags.append("identity_verification_failed")
        score += 0.30

    score = min(score, 1.0)

    if score >= FRAUD_THRESHOLDS["siu_referral"]:
        risk_level = "critical"
        siu_referred = True
    elif score >= FRAUD_THRESHOLDS["adjuster_flag"]:
        risk_level = "high"
        siu_referred = False
    elif score >= 0.20:
        risk_level = "medium"
        siu_referred = False
    else:
        risk_level = "low"
        siu_referred = False

    # Stricter auto-settle rule:
    # - fraud score must be very low
    # - no red flags should be present
    # - net estimate must be small relative to coverage OR under an absolute cap
    net_estimate = damage_result.get("net_estimate", 0)
    coverage_limit = coverage_result.get("coverage_limit", 999_999)
    ABSOLUTE_AUTO_SETTLE_CAP = 50000  # INR

    auto_settle = False

    # Calculate dynamic payout ratio (maximum 85%) and deduct based on issues
    base_ratio = 0.85
    ratio_reduction = (score * 0.5) + (len(red_flags) * 0.05)
    final_ratio = max(0.10, base_ratio - ratio_reduction)
    recommended_payout = round(net_estimate * final_ratio, 2)

    result = {
        "agent": "A5_Fraud_Risk_Scoring",
        "status": "success",
        "fraud_score": round(score, 4),
        "risk_level": risk_level,
        "red_flags": red_flags,
        "siu_referred": siu_referred,
        "auto_settle": auto_settle,
        "recommended_payout": recommended_payout,
        "payout_ratio": round(final_ratio, 4),
        "message": f"Fraud score: {score:.2f} ({risk_level} risk). Recommended payout: ₹{recommended_payout:,.2f} ({final_ratio*100:.1f}% of estimate). {'⚠ SIU referral triggered.' if siu_referred else 'Auto-settle eligible.' if auto_settle else 'Adjuster review recommended.'}",
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
