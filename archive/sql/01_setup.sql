-- PostgreSQL setup script for bailiffs matching system
-- Run this script as PostgreSQL superuser

-- Create database
CREATE DATABASE bailiffs_matching;

-- Connect to the database
\c bailiffs_matching;

-- Install required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

-- Create application user (optional, for production)
-- CREATE USER bailiffs_app WITH PASSWORD 'your_secure_password';
-- GRANT CONNECT ON DATABASE bailiffs_matching TO bailiffs_app;

-- Create indexes for efficient text searching after tables are created
-- These will be added after running the Python migration
