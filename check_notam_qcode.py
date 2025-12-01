import sqlite3

conn = sqlite3.connect('notam_realtime.db')
cursor = conn.cursor()

# First check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Available tables: {[t[0] for t in tables]}")

# Check schema of each table
for table in tables:
    table_name = table[0]
    print(f"\n{'='*60}")
    print(f"Schema for table '{table_name}':")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

    # Count records
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"  Total records: {count}")

conn.close()
