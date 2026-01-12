"""
Quick restart script for dashboard after laptop shutdown
"""

import subprocess
import time
import re

def get_database_ip():
    """Get current database IP"""
    result = subprocess.run(["docker", "inspect", "docker-project-db-1"], 
                          capture_output=True, text=True)
    match = re.search(r'"IPAddress":\s*"([^"]+)"', result.stdout)
    return match.group(1) if match else None

def quick_restart():
    """Quick restart all services and fix connections"""
    
    print("🚀 Starting dashboard restart...")
    
    # Start main services
    print("📦 Starting main services...")
    subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, text=True)
    
    # Start external Superset
    print("🌐 Starting external Superset...")
    subprocess.run(["docker", "compose", "-f", "superset/docker-compose-external.yml", "up", "-d"], 
                  capture_output=True, text=True)
    
    # Wait for startup
    print("⏳ Waiting for services to start...")
    time.sleep(15)
    
    # Get database IP
    db_ip = get_database_ip()
    if db_ip:
        print(f"🔗 Database IP: {db_ip}")
        
        # Update connection if needed
        if db_ip != "172.18.0.2":
            print("🔄 Updating database connection...")
            subprocess.run(["python", "fix_superset_connection.py"], capture_output=True, text=True)
    
    # Upgrade database
    print("🗄️ Upgrading database...")
    subprocess.run(["docker", "exec", "superset_app_external", "superset", "db", "upgrade"], 
                  capture_output=True, text=True)
    
    print("✅ Dashboard ready!")
    print("🔗 URL: http://localhost:8088")
    print("👤 Username: interviewer")
    print("🔑 Password: interviewer123")
    
    # Check if ngrok is running for external access
    print("\n🌐 For external access, run: ngrok http 8088")

if __name__ == "__main__":
    quick_restart()
