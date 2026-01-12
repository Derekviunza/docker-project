# 🔄 Complete Restart & Setup Guide

---

## 🚀 Quick Restart After Laptop Shutdown

### 1. Start Services
```bash
cd docker-project
docker compose up -d
docker compose -f superset/docker-compose-external.yml up -d
```

### 2. Check Database IP (Important!)
```bash
docker inspect docker-project-db-1 | findstr IPAddress
# Note the IP (e.g., 172.18.0.2)
```

### 3. Update Database Connection
```bash
# If IP changed, run:
python fix_superset_connection.py
```

### 4. Access Dashboard
- **URL:** http://localhost:8088
- **Username:** interviewer
- **Password:** interviewer123

---

## 🆕 First-Time Setup Guide

### 1. Start All Services
```bash
cd docker-project
docker compose up -d
docker compose -f superset/docker-compose-external.yml up -d
```

### 2. Database Setup
```bash
# Wait 30 seconds, then:
docker exec superset_app_external superset db upgrade
docker exec superset_app_external superset init
```

### 3. Create Interviewer User
```bash
docker exec superset_app_external superset fab create-user \
  --username interviewer \
  --firstname Interview \
  --lastname User \
  --email marketshadesoftwaresolutions@gmail.com \
  --role Admin \
  --password interviewer123
```

### 4. Connect Database in Superset UI
1. Go to http://localhost:8088
2. Login: interviewer / interviewer123
3. Settings → Database Connections → + DATABASE
4. Connection: `postgresql+psycopg2://ecommerce_user:ecommerce_password@[IP]:5432/ecommerce_price_comparison`
5. Test Connection → Connect

---

## 🌐 External Access Setup

### ngrok Setup
```bash
# 1. Install ngrok from https://ngrok.com/download
# 2. Configure: ngrok config add-authtoken YOUR_TOKEN
# 3. Create tunnel: ngrok http 8088
# 4. Share the HTTPS URL
```

---

## 🔧 Troubleshooting

### Database Connection Failed?
```bash
# Check current IP:
docker inspect docker-project-db-1 | findstr IPAddress

# Update connection:
python fix_superset_connection.py
```

### Superset Not Loading?
```bash
# Restart Superset:
docker compose -f superset/docker-compose-external.yml restart
```

### Services Not Running?
```bash
# Check status:
docker ps

# Restart all:
docker compose down
docker compose up -d
docker compose -f superset/docker-compose-external.yml up -d
```

---

## 📋 Complete Commands Summary

### Restart Commands
```bash
cd docker-project
docker compose up -d
docker compose -f superset/docker-compose-external.yml up -d
python fix_superset_connection.py  # If IP changed
```

### First-Time Setup
```bash
docker compose up -d
docker compose -f superset/docker-compose-external.yml up -d
docker exec superset_app_external superset db upgrade
docker exec superset_app_external superset init
docker exec superset_app_external superset fab create-user --username interviewer --firstname Interview --lastname User --email marketshadesoftwaresolutions@gmail.com --role Admin --password interviewer123
```

### External Access
```bash
ngrok http 8088
# Share the HTTPS URL
```

---

## 🎯 Key Points

- **IP Changes:** Database IP can change after restart - always check with `docker inspect`
- **User Creation:** Only needed once for first-time setup
- **Database Upgrade:** Run `superset db upgrade` after major changes
- **External Access:** Use ngrok for sharing with interviewers

---

**🎉 Your dashboard is ready at http://localhost:8088 (interviewer / interviewer123)!**
