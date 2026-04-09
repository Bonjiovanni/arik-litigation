import sqlite3

conn = sqlite3.connect(r"C:\Users\arika\OneDrive\Litigation\Pipeline\litigation_corpus.db")
cur = conn.cursor()

cur.execute("""
    SELECT from_name, from_addr, subject, date_time_sent, body_snippet
    FROM emails_master
    WHERE (from_name LIKE '%peterson%' OR from_addr LIKE '%peterson%')
    ORDER BY date_time_sent DESC
    LIMIT 10
""")
rows = cur.fetchall()
print("Latest {} Peterson emails (most recent first):".format(len(rows)))
print()

for i, r in enumerate(rows, 1):
    snippet = (r[4] or "")[:120]
    print("{}. Date: {}".format(i, r[3]))
    print("   From: {} <{}>".format(r[0], r[1]))
    print("   Subject: {}".format(r[2]))
    print("   Snippet: {}".format(snippet))
    print()

conn.close()
