-- =====================================================
-- Migration: 004_otp_auth_columns.sql
-- Description: Add OTP authentication and user approval
--              columns to the users table.
--   - is_approved: Admin must approve new signups
--   - otp_code / otp_expires_at: Passwordless OTP login
--   - last_login_at: Track last login time
-- Run on: Azure PostgreSQL (skillhive database)
-- =====================================================

-- Add is_approved column (default FALSE for new users)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;

-- Add OTP columns
ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_code VARCHAR(6);
ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMP;

-- Add last_login_at column
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;

-- Approve all existing active users so they aren't locked out
UPDATE users SET is_approved = TRUE WHERE is_active = TRUE;

-- Ensure super admin exists and is fully active
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
