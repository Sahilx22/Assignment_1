#!/usr/bin/env python
"""
Startup script: Run migrations then start the app.
This replaces the shell command to ensure migrations run properly.
"""
import subprocess
import sys
import os

# Set working directory to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

def run_migrations():
    """Run alembic migrations."""
    print("=" * 60)
    print("Running database migrations...")
    print(f"Working directory: {os.getcwd()}")
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'NOT SET')[:50]}...")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            check=False,  # Don't raise on non-zero exit, we'll handle it
            capture_output=True,
            text=True,
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
        
        if result.returncode == 0:
            print("✅ Migrations completed successfully!")
            return True
        else:
            print(f"❌ Migration failed with exit code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error during migrations: {e}", file=sys.stderr)
        return False


def start_app():
    """Start the uvicorn application."""
    print("=" * 60)
    print("Starting FastAPI application...")
    print("=" * 60)
    
    port = os.environ.get("PORT", "8000")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "app.main:app", 
             "--host", "0.0.0.0", "--port", port],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Application failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n🚀 FastAPI Auth Service Startup\n")
    
    # Step 1: Run migrations
    if not run_migrations():
        print("\n⚠️  Migrations failed!")
        print("Check DATABASE_URL is set in environment variables.")
        print("Application will not start without successful migrations.\n")
        sys.exit(1)
    
    # Step 2: Start the app
    print()
    start_app()
