#!/usr/bin/env python3
"""
Database migration runner for SaaS platform
Runs SQL migration files in order and tracks applied migrations
"""

import os
import sys
import psycopg2
import boto3
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection using AWS Secrets Manager and SSM"""
    try:
        # AWS clients
        ssm = boto3.client('ssm', region_name='eu-west-2')
        secrets = boto3.client('secretsmanager', region_name='eu-west-2')
        
        # Get DB credentials from Secrets Manager
        secret_response = secrets.get_secret_value(SecretId='saas-platform/database/password')
        secret = json.loads(secret_response['SecretString'])
        
        # Get DB endpoint from SSM (RDS Proxy endpoint)
        db_endpoint = ssm.get_parameter(Name='/saas-platform/database/endpoint')['Parameter']['Value']
        db_name = ssm.get_parameter(Name='/saas-platform/database/name')['Parameter']['Value']
        
        return psycopg2.connect(
            host=db_endpoint.split(':')[0],
            database=db_name,
            user=secret['username'],
            password=secret['password'],
            connect_timeout=30
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def create_migrations_table(conn):
    """Create migrations tracking table if it doesn't exist"""
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        logger.info("Migrations table created/verified")
    except Exception as e:
        logger.error(f"Failed to create migrations table: {e}")
        raise

def get_applied_migrations(conn):
    """Get list of already applied migrations"""
    try:
        cur = conn.cursor()
        cur.execute("SELECT migration_name FROM schema_migrations ORDER BY id")
        applied = [row[0] for row in cur.fetchall()]
        cur.close()
        return applied
    except Exception as e:
        logger.error(f"Failed to get applied migrations: {e}")
        return []

def apply_migration(conn, migration_file):
    """Apply a single migration file"""
    try:
        migration_name = migration_file.name
        logger.info(f"Applying migration: {migration_name}")
        
        # Read migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        cur = conn.cursor()
        
        # Execute migration
        cur.execute(migration_sql)
        
        # Record migration as applied
        cur.execute(
            "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
            (migration_name,)
        )
        
        conn.commit()
        cur.close()
        logger.info(f"Successfully applied migration: {migration_name}")
        
    except Exception as e:
        logger.error(f"Failed to apply migration {migration_file.name}: {e}")
        conn.rollback()
        raise

def run_migrations():
    """Run all pending migrations"""
    try:
        # Get migrations directory
        migrations_dir = Path(__file__).parent
        
        # Get all SQL migration files (prevent path traversal)
        migration_files = sorted([
            f for f in migrations_dir.glob('*.sql')
            if (f.name.startswith(('001_', '002_', '003_', '004_', '005_', '006_', '007_', '008_', '009_')) 
                and '..' not in str(f) and f.is_file())
        ])
        
        if not migration_files:
            logger.info("No migration files found")
            return
        
        # Connect to database
        conn = get_db_connection()
        
        # Create migrations table
        create_migrations_table(conn)
        
        # Get applied migrations
        applied_migrations = get_applied_migrations(conn)
        
        # Apply pending migrations
        pending_count = 0
        for migration_file in migration_files:
            if migration_file.name not in applied_migrations:
                apply_migration(conn, migration_file)
                pending_count += 1
            else:
                logger.info(f"Migration already applied: {migration_file.name}")
        
        conn.close()
        
        if pending_count > 0:
            logger.info(f"Applied {pending_count} migrations successfully")
        else:
            logger.info("No pending migrations to apply")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()