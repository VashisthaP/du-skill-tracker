"""Check production database schema."""
import psycopg2

conn = psycopg2.connect(
    'postgresql://skillhiveadmin:Postgres1%402026@skillhive-accenture-pg.postgres.database.azure.com:5432/skillhive?sslmode=require'
)
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'demands' ORDER BY ordinal_position")
print('Current demands columns:', [r[0] for r in cur.fetchall()])

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
print('Tables:', [r[0] for r in cur.fetchall()])

conn.close()
