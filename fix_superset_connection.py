"""
Fix Superset database connection by updating environment variables
"""

import os
import subprocess

def fix_superset_connection():
    """Update Superset to connect to main database"""
    
    # Stop external Superset
    print("🔄 Stopping external Superset...")
    subprocess.run(["docker", "compose", "-f", "superset/docker-compose-external.yml", "down"], 
                  capture_output=True, text=True)
    
    # Update environment file
    env_content = f"""SUPERSET_SECRET_KEY=this-is-a-very-long-and-secure-secret-key-for-development-only-change-in-production
SUPERSET_LOAD_EXAMPLES=no
SUPERSET_DATABASE_URI=postgresql+psycopg2://ecommerce_user:ecommerce_password@172.18.0.2:5432/ecommerce_price_comparison
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
SUPERSET_WEBSERVER_HOST=0.0.0.0
SUPERSET_WEBSERVER_PORT=8088
"""
    
    with open("superset/.env", "w") as f:
        f.write(env_content)
    
    print("✅ Updated Superset environment to connect to main database (172.18.0.2)")
    
    # Restart external Superset
    print("🚀 Restarting external Superset...")
    subprocess.run(["docker", "compose", "-f", "superset/docker-compose-external.yml", "up", "-d"], 
                  capture_output=True, text=True)
    
    # Wait for startup
    import time
    time.sleep(10)
    
    # Check status
    result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
    if "superset_app_external" in result.stdout:
        print("✅ Superset restarted successfully!")
        print("🔗 Dashboard: http://localhost:8088")
        print("👤 Username: interviewer")
        print("🔑 Password: interviewer123")
    else:
        print("❌ Superset failed to start")

if __name__ == "__main__":
    fix_superset_connection()
