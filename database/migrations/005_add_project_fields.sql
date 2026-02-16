-- ============================================================
-- Migration 005: Add Project Fields to Demands Table
-- ============================================================
-- Adds du_name, client_name, and manager_name columns to support
-- simplified project creation workflow.
-- Run after: 004_otp_auth_columns.sql
-- ============================================================

-- Add DU Name column
ALTER TABLE demands ADD COLUMN IF NOT EXISTS du_name VARCHAR(255);

-- Add Client Name column
ALTER TABLE demands ADD COLUMN IF NOT EXISTS client_name VARCHAR(255);

-- Add Manager Name column  
ALTER TABLE demands ADD COLUMN IF NOT EXISTS manager_name VARCHAR(255);

-- ============================================================
-- End of Migration 005
-- ============================================================
