#!/usr/bin/env python
"""
Startup script: Run migrations then start the app.
This ensures migrations run before any requests hit the app.
"""
import subprocess
import sys
import os
import time

# Set working directory to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

def check_env():
    """Verify required environment variables are set."""
    print("=" * 70)
    print("Environment Check")
    print("=" * 70)
    
    db_url = os.environ.get("DATABASE_URL", "")
    
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable is NOT SET!")
        print("\nThis is required for database migrations.")
        print("Make sure your Render PostgreSQL is connected and DATABASE_URL is set.")
        return False
    
    # Show partial URL (hide password)
    url_display = db_url.split("@")[1] if "@" in db_url else "***"
    print(f"✅ DATABASE_URL is set: postgresql://...@{url_display}")
    print(f"✅ Working directory: {os.getcwd()}")
    print(f"✅ Python: {sys.version.split()[0]}")
    print()
    return True


def run_migrations():
    """Run alembic migrations with detailed output."""
    print("=" * 70)
    print("Running Database Migrations")
    print("=" * 70)
    
    try:
        # Run migration with full output
        cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
        print(f"Running: {' '.join(cmd)}\n")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            universal_newlines=True,
        )
        
        # Stream output in real-time
        for line in process.stdout:
            print(line, end="")
        
        returncode = process.wait()
        
        if returncode == 0:
            print("\n✅ Migrations completed successfully!")
            return True
        else:
            print(f"\n❌ Migrations failed with exit code {returncode}")
            print("\nThis usually means:")
            print("  • DATABASE_URL is invalid or database is unreachable")
            print("  • PostgreSQL service is down")
            print("  • Network is blocked (firewall, etc.)")
            return False
            
    except FileNotFoundError as e:
        print(f"❌ Command not found: {e}")
        print("Make sure alembic is installed (pip install alembic)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def start_app():
    """Start the uvicorn application."""
    print("\n" + "=" * 70)
    print("Starting FastAPI Application")
    print("=" * 70 + "\n")
    
    port = os.environ.get("PORT", "8000")
    
    try:
        cmd = [sys.executable, "-m", "uvicorn", "app.main:app",
               "--host", "0.0.0.0", "--port", port]
        print(f"Running: {' '.join(cmd)}\n")
        
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Application exited with error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  🚀 FastAPI Auth Service - Startup Script".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print("\n")
    
    # Check environment
    if not check_env():
        print("\n⚠️  Cannot proceed without DATABASE_URL")
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        print("\n" + "=" * 70)
        print("❌ STARTUP FAILED: Migrations did not complete")
        print("=" * 70)
        print("\nThe application requires a working database connection.")
        print("Please check:")
        print("  1. DATABASE_URL is set correctly in Render Environment")
        print("  2. PostgreSQL instance is running and in the same region")
        print("  3. Network connectivity between services is working")
        print("\nCheck Render docs: https://render.com/docs/databases")
        sys.exit(1)
    
    # Start the application
    start_app()


if __name__ == "__main__":
    main()
