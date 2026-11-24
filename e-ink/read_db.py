﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿import sqlite3

conn = sqlite3.connect("photos.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type=\"table\"")
tables = cursor.fetchall()
print("Tables:", tables)

for table in tables:
    table_name = table[0]
    print("=== Table:", table_name, "===")
    cursor.execute("PRAGMA table_info(" + table_name + ")")
    columns = cursor.fetchall()
    print("Columns:", columns)
    
    cursor.execute("SELECT COUNT(*) FROM " + table_name)
    count = cursor.fetchone()[0]
    print("Rows:", count)
    
    if count > 0:
        cursor.execute("SELECT * FROM " + table_name + " LIMIT 3")
        rows = cursor.fetchall()
        print("Sample data:")
        for row in rows:
            print(row)

conn.close()
