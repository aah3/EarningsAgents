import sqlite3

def main():
    conn = sqlite3.connect('earnings_agents.db')
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(prediction)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    columns_to_add = [
        ("actual_direction", "VARCHAR DEFAULT NULL"),
        ("actual_eps", "FLOAT DEFAULT NULL"),
        ("actual_price_move_pct", "FLOAT DEFAULT NULL"),
        ("accuracy_score", "FLOAT DEFAULT NULL"),
        ("scored_at", "DATETIME DEFAULT NULL"),
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE prediction ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column {col_name} already exists. Skipped.")
            
    conn.commit()
    conn.close()
    print("Done checking/adding evaluation columns.")

if __name__ == "__main__":
    main()
