"""
First-time setup script for dashboard
"""

import subprocess
import time

def first_time_setup():
    """Complete first-time setup for dashboard"""
    
    print("🚀 First-time dashboard setup...")
    
    # Start services
    print("📦 Starting all services...")
    subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, text=True)
    subprocess.run(["docker", "compose", "-f", "superset/docker-compose-external.yml", "up", "-d"], 
                  capture_output=True, text=True)
    
    # Wait for startup
    print("⏳ Waiting for services to start (30 seconds)...")
    time.sleep(30)
    
    # Database setup
    print("🗄️ Setting up database...")
    result = subprocess.run(["docker", "exec", "superset_app_external", "superset", "db", "upgrade"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Database upgraded")
    else:
        print("⚠️ Database upgrade may have issues, continuing...")
    
    # Initialize Superset
    print("🔧 Initializing Superset...")
    subprocess.run(["docker", "exec", "superset_app_external", "superset", "init"], 
                  capture_output=True, text=True)
    
    # Create interviewer user
    print("👤 Creating interviewer user...")
    result = subprocess.run([
        "docker", "exec", "superset_app_external", "superset", "fab", "create-user",
        "--username", "interviewer",
        "--firstname", "Interview",
        "--lastname", "User", 
        "--email", "marketshadesoftwaresolutions@gmail.com",
        "--role", "Admin",
        "--password", "interviewer123"
    ], capture_output=True, text=True)
    
    if "already exists" in result.stdout:
        print("✅ Interviewer user already exists")
    elif result.returncode == 0:
        print("✅ Interviewer user created")
    else:
        print("⚠️ User creation may have issues")
    
    # Get database IP
    print("🔗 Getting database connection info...")
    result = subprocess.run(["docker", "inspect", "docker-project-db-1"], 
                          capture_output=True, text=True)
    
    import re
    match = re.search(r'"IPAddress":\s*"([^"]+)"', result.stdout)
    db_ip = match.group(1) if match else "172.18.0.2"
    
    print("\n🎉 Setup Complete!")
    print("=" * 50)
    print("🔗 Dashboard URL: http://localhost:8088")
    print("👤 Username: interviewer")
    print("🔑 Password: interviewer123")
    print("🗄️ Database IP:", db_ip)
    print("=" * 50)
    
    print("\n📋 Next Steps:")
    print("1. Go to http://localhost:8088")
    print("2. Login with interviewer / interviewer123")
    print("3. Settings → Database Connections → + DATABASE")
    print(f"4. Connection: postgresql+psycopg2://ecommerce_user:ecommerce_password@{db_ip}:5432/ecommerce_price_comparison")
    print("5. Test Connection → Connect")
    
    print("\n🌐 For external access:")
    print("1. Install ngrok from https://ngrok.com/download")
    print("2. ngrok config add-authtoken YOUR_TOKEN")
    print("3. ngrok http 8088")
    print("4. Share the HTTPS URL")

if __name__ == "__main__":
    first_time_setup()
