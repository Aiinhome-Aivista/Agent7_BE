import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import engine
from sqlalchemy import text

print("Connecting to DB...")
with engine.connect() as conn:
    for cid in [3322, 2809, 2880]:
        try:
            print(f"Killing connection {cid}...")
            conn.execute(text(f"KILL {cid}"))
            print(f"Successfully killed connection {cid}")
        except Exception as e:
            print(f"Error killing {cid}: {e}")
