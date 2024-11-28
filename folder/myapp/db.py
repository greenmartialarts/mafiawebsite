from django.db import connection
from django.conf import settings
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def initialize_database():
    """Initialize database connection and create required extensions."""
    try:
        # Connect with default postgres database
        conn = psycopg2.connect(
            dbname='postgres',
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            host=settings.DATABASES['default']['HOST'],
            port=settings.DATABASES['default']['PORT']
        )
        
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Create extensions if they don't exist
        cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        cur.execute('CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";')
        
        cur.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

def test_connection():
    """Test the database connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            return True
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False 