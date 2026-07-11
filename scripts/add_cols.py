import sqlite3

def add_columns():
    db_path = "earnings_agents.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("PRAGMA table_info(prediction)")
        columns = [info[1] for info in cursor.fetchall()]
        
        new_cols = ['expected_price_move', 'move_vs_implied', 'guidance_expectation']
        for col in new_cols:
            if col not in columns:
                cursor.execute(f"ALTER TABLE prediction ADD COLUMN {col} VARCHAR DEFAULT ''")
                print(f"Added column {col}")
            else:
                print(f"Column {col} already exists")
                
        conn.commit()
        conn.close()
        print("Database update complete.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_columns()
