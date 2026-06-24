from sqlalchemy import text
from valuation.db.session import engine_write

def grant_permissions():
    with engine_write.connect() as conn:
        print("Granting SELECT privilege on consensus_history to readonly_user...")
        try:
            conn.execute(text("GRANT SELECT ON TABLE consensus_history TO readonly_user;"))
            conn.commit()
            print("Successfully granted SELECT privilege on consensus_history!")
        except Exception as e:
            print(f"Failed to grant permissions: {e}")

if __name__ == "__main__":
    grant_permissions()
