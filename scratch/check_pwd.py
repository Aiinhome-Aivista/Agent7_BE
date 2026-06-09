import sys
import os
import bcrypt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import User

def check():
    db = next(get_db())
    try:
        user = db.query(User).first()
        if not user:
            print("No users found.")
            return
        
        hashed = user.password_hash
        print(f"Testing for user {user.email} with hash: {hashed}")
        
        # Test candidate passwords
        candidates = ["password123", "password", "123456", "admin123", "demo123", "Priya123", "Arjun123", "Aiin@2026", "admin"]
        for cand in candidates:
            try:
                res = bcrypt.checkpw(cand.encode('utf-8'), hashed.encode('utf-8'))
                if res:
                    print(f"SUCCESS! Password is: {cand}")
                    return
            except Exception as e:
                print(f"Failed for {cand}: {e}")
                
        print("None of the common passwords matched.")
    finally:
        db.close()

if __name__ == "__main__":
    check()
