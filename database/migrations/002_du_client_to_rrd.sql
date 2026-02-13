-- ============================================================
-- Migration: Replace du_name + client_name with single rrd column
-- Run this on existing PostgreSQL databases to update schema.
-- ============================================================

-- Step 1: Add the new rrd column
ALTER TABLE demands ADD COLUMN IF NOT EXISTS rrd VARCHAR(255);

-- Step 2: Populate rrd from existing du_name (+ client_name if present)
UPDATE demands SET rrd = COALESCE(du_name, '') || CASE WHEN client_name IS NOT NULL AND client_name != '' THEN ' - ' || client_name ELSE '' END
WHERE rrd IS NULL;

-- Step 3: Make rrd NOT NULL
ALTER TABLE demands ALTER COLUMN rrd SET NOT NULL;

-- Step 4: Drop old columns
ALTER TABLE demands DROP COLUMN IF EXISTS du_name;
ALTER TABLE demands DROP COLUMN IF EXISTS client_name;
