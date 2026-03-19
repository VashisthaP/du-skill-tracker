"""Check production database schema."""
import os
import psycopg2

# Get DB URL from environment or use placeholder
DB_URL = os.environ.get('DATABASE_URL', 'postgresql://user:password@your-server.postgres.database.azure.com:5432/skillhive?sslmode=require')

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'demands' ORDER BY ordinal_position")
print('Current demands columns:', [r[0] for r in cur.fetchall()])

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
print('Tables:', [r[0] for r in cur.fetchall()])

conn.close()
