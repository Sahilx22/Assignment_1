"""
Production startup script - runs migrations then starts the app.
This is the entry point used by Render.
"""
import subprocess
import sys
import os

def main():
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    print("\n" + "="*70)
    print("Starting FastAPI Production Server")
    print("="*70 + "\n")
    
    # Step 1: Run migrations
    print("Step 1: Running database migrations...\n")
    migration_cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
    
    try:
        result = subprocess.run(migration_cmd, check=True)
        print("\n✅ Migrations completed!\n")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Migration failed with exit code {e.returncode}")
        print("Database error - check DATABASE_URL and PostgreSQL connection\n")
        sys.exit(1)
    
    # Step 2: Start uvicorn
    print("Step 2: Starting Uvicorn server...\n")
    port = os.environ.get("PORT", "8000")
    
    uvicorn_cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        f"--port", port,
    ]
    
    # exec replaces this process with uvicorn
    os.execvp(uvicorn_cmd[0], uvicorn_cmd)

if __name__ == "__main__":
    main()
