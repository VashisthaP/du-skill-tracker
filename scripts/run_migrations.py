"""Run pending migrations against production PostgreSQL."""
import psycopg2
import sys

DB_URL = "postgresql://skillhiveadmin:Postgres1%402026@skillhive-accenture-pg.postgres.database.azure.com:5432/skillhive?sslmode=require"

MIGRATION_002 = """
-- Step 1: Add the new rrd column
ALTER TABLE demands ADD COLUMN IF NOT EXISTS rrd VARCHAR(255);

-- Step 2: Populate rrd from existing du_name (+ client_name if present)
UPDATE demands SET rrd = COALESCE(du_name, '') || CASE WHEN client_name IS NOT NULL AND client_name != '' THEN ' - ' || client_name ELSE '' END
WHERE rrd IS NULL;

-- Step 3: Make rrd NOT NULL (set default for any blanks first)
UPDATE demands SET rrd = 'Unknown' WHERE rrd IS NULL OR rrd = '';

ALTER TABLE demands ALTER COLUMN rrd SET NOT NULL;

-- Step 4: Drop old columns
ALTER TABLE demands DROP COLUMN IF EXISTS du_name;
ALTER TABLE demands DROP COLUMN IF EXISTS client_name;
"""

MIGRATION_003 = """
CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    demand_id INTEGER NOT NULL REFERENCES demands(id) ON DELETE CASCADE,
    personnel_no VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    primary_skill VARCHAR(255),
    management_level VARCHAR(50),
    home_location VARCHAR(255),
    lock_status VARCHAR(100),
    availability_status VARCHAR(100),
    email VARCHAR(255),
    contact_details VARCHAR(100),
    joining_date VARCHAR(100),
    evaluation_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    evaluation_remarks TEXT,
    evaluated_by INTEGER REFERENCES users(id),
    evaluated_at TIMESTAMP,
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS ix_resources_demand_id
    ON resources(demand_id);
CREATE INDEX IF NOT EXISTS ix_resources_evaluation_status
    ON resources(evaluation_status);
"""


MIGRATION_004 = """
-- Add OTP authentication and user approval columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_code VARCHAR(6);
ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;

-- Approve all existing active users
UPDATE users SET is_approved = TRUE WHERE is_active = TRUE;

-- Ensure super admin
INSERT INTO users (email, display_name, role, is_active, is_approved, created_at)
VALUES (
    'pratyush.vashistha@accenture.com',
    'Pratyush Vashistha',
    'admin',
    TRUE,
    TRUE,
    NOW() AT TIME ZONE 'utc'
)
ON CONFLICT (email) DO UPDATE SET
    role = 'admin',
    is_active = TRUE,
    is_approved = TRUE;
"""


def run_migration(conn, name, sql):
    """Execute a migration SQL block."""
    print(f"\n{'='*50}")
    print(f"Running {name}...")
    print(f"{'='*50}")
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print(f"  [OK] {name} completed successfully")
        cur.close()
    except Exception as e:
        conn.rollback()
        print(f"  [FAIL] {name} FAILED: {e}")
        raise


def check_schema(conn):
    """Show current demands columns and tables."""
    cur = conn.cursor()

    # Check demands columns
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'demands'
        ORDER BY ordinal_position;
    """)
    cols = cur.fetchall()
    print("\n--- demands table columns ---")
    for col in cols:
        print(f"  {col[0]:30s} {col[1]:20s} nullable={col[2]}")

    # Check if resources table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'resources'
        );
    """)
    exists = cur.fetchone()[0]
    print(f"\n--- resources table exists: {exists} ---")
    cur.close()


def main():
    print("Connecting to production PostgreSQL...")
    conn = psycopg2.connect(DB_URL)
    print("Connected!")

    # Show current state
    print("\n=== BEFORE MIGRATIONS ===")
    check_schema(conn)

    # Check if rrd column already exists
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'demands' AND column_name = 'rrd';
    """)
    has_rrd = cur.fetchone() is not None
    cur.close()

    if has_rrd:
        print("\n  >> rrd column already exists, skipping migration 002")
    else:
        run_migration(conn, "Migration 002 (du_client to rrd)", MIGRATION_002)

    # Check if resources table already exists
    cur = conn.cursor()
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'resources'
        );
    """)
    has_resources = cur.fetchone()[0]
    cur.close()

    if has_resources:
        print("\n  >> resources table already exists, skipping migration 003")
    else:
        run_migration(conn, "Migration 003 (resources table)", MIGRATION_003)

    # Check if is_approved column already exists on users
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'is_approved';
    """)
    has_is_approved = cur.fetchone() is not None
    cur.close()

    if has_is_approved:
        print("\n  >> is_approved column already exists, skipping migration 004")
    else:
        run_migration(conn, "Migration 004 (OTP auth columns)", MIGRATION_004)

    # Show final state
    print("\n=== AFTER MIGRATIONS ===")
    check_schema(conn)

    conn.close()
    print("\n[DONE] All migrations complete!")


if __name__ == "__main__":
    main()
