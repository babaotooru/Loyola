-- Supabase / PostgreSQL schema for Loyola Admissions System
-- Run this in Supabase SQL editor or psql to create required tables and indexes

CREATE TABLE IF NOT EXISTS accounts (
  id SERIAL PRIMARY KEY,
  full_name VARCHAR(255) NOT NULL,
  username VARCHAR(255) UNIQUE,
  email VARCHAR(255) UNIQUE,
  phone VARCHAR(20) UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'student',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash VARCHAR(64) PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account_id);
CREATE INDEX IF NOT EXISTS idx_sessions_role ON sessions(role);

CREATE TABLE IF NOT EXISTS admissions (
  id SERIAL PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  course VARCHAR(255) NOT NULL,
  submitted_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create an initial admin entry if not exists (useful for manual runs)
INSERT INTO accounts (full_name, username, email, phone, password_hash, role)
SELECT '%s', '%s', NULL, NULL, '%s', 'admin'
WHERE NOT EXISTS (
  SELECT 1 FROM accounts WHERE role = 'admin' AND username = '%s'
);

-- Replace the placeholders above when running manually.
-- Example run (psql):
-- \set admin_name 'Loyola admin'
-- \set admin_username 'Loyola admin'
-- \set admin_password_hash 'pbkdf2_sha256$120000$...'
-- Then run the INSERT statement with the variables substituted.
