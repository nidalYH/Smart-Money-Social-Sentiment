-- Smart Money Social Sentiment Analyzer Database Initialization

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database indexes for performance
-- (Tables will be created by SQLAlchemy migrations)

-- Performance optimization settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Create read-only user for analytics
CREATE USER smartmoney_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE smartmoney TO smartmoney_readonly;
GRANT USAGE ON SCHEMA public TO smartmoney_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO smartmoney_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO smartmoney_readonly;

-- Create backup user
CREATE USER smartmoney_backup WITH PASSWORD 'backup_password';
GRANT CONNECT ON DATABASE smartmoney TO smartmoney_backup;
GRANT USAGE ON SCHEMA public TO smartmoney_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO smartmoney_backup;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO smartmoney_backup;


