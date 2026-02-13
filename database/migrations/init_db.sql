-- ============================================================
-- SkillHive – Initial Database Schema for PostgreSQL
-- Run this ONLY if you need manual DB setup.
-- The app uses SQLAlchemy create_all() for automatic setup.
-- ============================================================

-- Users (synced from Azure AD)
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    azure_ad_id VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    enterprise_id VARCHAR(50),
    role VARCHAR(20) DEFAULT 'resource' CHECK (role IN ('admin', 'pmo', 'evaluator', 'resource')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Skills taxonomy
CREATE TABLE IF NOT EXISTS skill (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Demands
CREATE TABLE IF NOT EXISTS demand (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    project_code VARCHAR(50),
    rrd VARCHAR(255) NOT NULL,
    career_level VARCHAR(10) NOT NULL,
    num_positions INTEGER DEFAULT 1,
    start_date DATE,
    end_date DATE,
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'filled', 'cancelled')),
    evaluator_name VARCHAR(255),
    evaluator_email VARCHAR(255),
    evaluator_contact VARCHAR(50),
    description TEXT,
    additional_notes TEXT,
    created_by INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Demand ↔ Skill many-to-many
CREATE TABLE IF NOT EXISTS demand_skills (
    demand_id INTEGER REFERENCES demand(id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skill(id) ON DELETE CASCADE,
    PRIMARY KEY (demand_id, skill_id)
);

-- Applications
CREATE TABLE IF NOT EXISTS application (
    id SERIAL PRIMARY KEY,
    demand_id INTEGER REFERENCES demand(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES "user"(id),
    applicant_name VARCHAR(255) NOT NULL,
    enterprise_id VARCHAR(50),
    current_project VARCHAR(255),
    years_of_experience REAL,
    skills_text TEXT,
    resume_filename VARCHAR(255),
    resume_blob_url VARCHAR(500),
    status VARCHAR(30) DEFAULT 'applied' CHECK (status IN ('applied', 'under_evaluation', 'selected', 'rejected')),
    remarks TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Application status audit trail
CREATE TABLE IF NOT EXISTS application_history (
    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES application(id) ON DELETE CASCADE,
    old_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    changed_by INTEGER REFERENCES "user"(id),
    remarks TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_demand_status ON demand(status);
CREATE INDEX IF NOT EXISTS idx_demand_priority ON demand(priority);
CREATE INDEX IF NOT EXISTS idx_demand_created_by ON demand(created_by);
CREATE INDEX IF NOT EXISTS idx_application_demand ON application(demand_id);
CREATE INDEX IF NOT EXISTS idx_application_user ON application(user_id);
CREATE INDEX IF NOT EXISTS idx_application_status ON application(status);
CREATE INDEX IF NOT EXISTS idx_skill_name ON skill(name);
