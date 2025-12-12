#!/usr/bin/env python3
"""
Test database connection
"""
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    try:
        # Parse DATABASE_URL
        db_url = os.getenv('DATABASE_URL', 'mysql://root:@localhost:3306/marketplace')
        # Extract connection details
        if db_url.startswith('mysql://'):
            db_url = db_url[8:]  # Remove 'mysql://'
            if '@' in db_url:
                user_pass, host_port_db = db_url.split('@')
                if ':' in user_pass:
                    user, password = user_pass.split(':')
                else:
                    user, password = user_pass, ''
                if ':' in host_port_db:
                    host_port, database = host_port_db.split('/')
                    if ':' in host_port:
                        host, port = host_port.split(':')
                        port = int(port)
                    else:
                        host, port = host_port, 3306
                else:
                    host_port, database = host_port_db, 'marketplace'
                    host, port = host_port, 3306
            else:
                # No authentication
                user, password = 'root', ''
                if ':' in db_url:
                    host_port, database = db_url.split('/')
                    if ':' in host_port:
                        host, port = host_port.split(':')
                        port = int(port)
                    else:
                        host, port = host_port, 3306
                else:
                    host, port, database = db_url, 3306, 'marketplace'
        else:
            # Default values
            host, port, user, password, database = 'localhost', 3306, 'root', '', 'marketplace'
        
        print(f"Connecting to MySQL:")
        print(f"  Host: {host}")
        print(f"  Port: {port}")
        print(f"  User: {user}")
        print(f"  Database: {database}")
        
        # Test connection
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        
        print("Database connection successful!")
        
        # Test query
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"MySQL version: {version[0]}")
            
            # Check if tables exist
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"Tables found: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
