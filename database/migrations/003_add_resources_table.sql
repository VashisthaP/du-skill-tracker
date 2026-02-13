-- =====================================================
-- Migration: 003_add_resources_table.sql
-- Description: Add resources table for PMO bulk-upload
--              of available supply against demands (RRDs).
-- Run on: Azure PostgreSQL (skillhive database)
-- =====================================================

-- Create resources table
CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    demand_id INTEGER NOT NULL REFERENCES demands(id) ON DELETE CASCADE,

    -- Resource details (from Excel upload)
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

    -- Evaluation workflow
    evaluation_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    evaluation_remarks TEXT,
    evaluated_by INTEGER REFERENCES users(id),
    evaluated_at TIMESTAMP,

    -- Metadata
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS ix_resources_demand_id
    ON resources(demand_id);
CREATE INDEX IF NOT EXISTS ix_resources_evaluation_status
    ON resources(evaluation_status);
