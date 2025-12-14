"""
Backend startup script with better error handling
"""
import sys
import traceback

try:
    print("Starting backend server...")
    print("=" * 50)
    
    # Check database connection first
    try:
        from app.core.database import engine
        print("Testing database connection...")
        with engine.connect() as conn:
            print("✓ Database connection successful!")
    except Exception as db_error:
        print("✗ Database connection failed!")
        print(f"Error: {db_error}")
        print("\nPlease make sure:")
        print("1. MySQL is running in XAMPP")
        print("2. Database 'marketplace' exists")
        print("3. Database credentials are correct in app/core/config.py")
        print("\nYou can still start the server, but database operations will fail.")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Start the server
    import uvicorn
    print("\nStarting FastAPI server on http://0.0.0.0:8000")
    print("API docs available at http://localhost:8000/docs")
    print("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
    
except KeyboardInterrupt:
    print("\n\nServer stopped by user")
except Exception as e:
    print("\n" + "=" * 50)
    print("FATAL ERROR starting server:")
    print("=" * 50)
    traceback.print_exc()
    sys.exit(1)



