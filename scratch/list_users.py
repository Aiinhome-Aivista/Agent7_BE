import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.models.models import User

def list_users():
    db = next(get_db())
    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f"- Email: {u.email} | Role: {u.role} | Name: {u.full_name} | Password Hash: {u.password_hash}")
    except Exception as e:
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    list_users()
