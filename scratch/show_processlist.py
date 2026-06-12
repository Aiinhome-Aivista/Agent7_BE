import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import engine
from sqlalchemy import text

print("Connecting to DB...")
with engine.connect() as conn:
    print("Fetching processlist...")
    try:
        res = conn.execute(text("SHOW PROCESSLIST")).fetchall()
        print("PROCESSLIST:")
        for r in res:
            print(r)
            
        print("\nFetching InnoDB Locks/Transactions...")
        trx = conn.execute(text("SELECT * FROM information_schema.innodb_trx")).fetchall()
        print("INNODB TRANSACTIONS:")
        for t in trx:
            print(t)
    except Exception as e:
        print(f"Error fetching info: {e}")
