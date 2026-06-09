import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import ClaimDocument

def find_docs():
    db = next(get_db())
    try:
        docs = db.query(ClaimDocument).filter(ClaimDocument.filename.like("%kabir%")).all()
        print(f"Found {len(docs)} documents containing 'kabir' in name:")
        for d in docs:
            print(f"ID: {d.id} | Claim ID: {d.claim_id} | Name: {d.filename} | Category: {d.category} | Extracted: {d.extracted_data}")
            print("-" * 50)
            
        docs_policy = db.query(ClaimDocument).filter(ClaimDocument.policy_id == 3).all()
        print(f"\nFound {len(docs_policy)} documents for policy ID 3:")
        for d in docs_policy:
            print(f"ID: {d.id} | Claim ID: {d.claim_id} | Name: {d.filename} | Category: {d.category} | Extracted: {d.extracted_data}")
            
    finally:
        db.close()

if __name__ == "__main__":
    find_docs()
