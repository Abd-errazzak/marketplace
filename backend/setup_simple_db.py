#!/usr/bin/env python3
"""
Setup simple database schema
"""
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
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
        
        print(f"Setting up database: {database}")
        
        # Connect to MySQL server (without database)
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            print(f"Database '{database}' created/verified")
            
            # Use the database
            cursor.execute(f"USE {database}")
            
            # Read and execute simple schema
            schema_path = os.path.join(os.path.dirname(__file__), 'simple_schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                # Split by semicolon and execute each statement
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                
                for i, statement in enumerate(statements):
                    if statement and not statement.startswith('--'):
                        try:
                            cursor.execute(statement)
                            print(f"Executed statement {i+1}/{len(statements)}")
                        except Exception as e:
                            print(f"Warning: Statement {i+1} failed: {e}")
                            # Continue with other statements
                
                print("Database schema setup completed!")
            else:
                print(f"Schema file not found: {schema_path}")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"Database setup failed: {e}")
        return False

if __name__ == "__main__":
    setup_database()






