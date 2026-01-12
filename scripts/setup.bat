@echo off
REM 🐳 E-commerce Price Comparison Dashboard Setup (Windows)
REM Clean Docker-based deployment

echo 🚀 Starting E-commerce Price Comparison Dashboard Setup...

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed.
    pause
    exit /b 1
)

REM Get script directory
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

echo 📁 Project directory: %PROJECT_DIR%

REM Copy processed data to docker project
echo 📋 Copying processed data...
if not exist "%PROJECT_DIR%\docker-project\data\output" mkdir "%PROJECT_DIR%\docker-project\data\output"
copy "%PROJECT_DIR%\output\standardized_*.json" "%PROJECT_DIR%\docker-project\data\output\" >nul 2>&1
if %errorlevel% neq 0 echo ⚠️ No standardized files found

REM Navigate to docker project
cd /d "%PROJECT_DIR%\docker-project"

REM Create environment file
echo 🔧 Creating environment file...
(
echo # Database Configuration
echo POSTGRES_DB=ecommerce_price_comparison
echo POSTGRES_USER=ecommerce_user
echo POSTGRES_PASSWORD=ecommerce_password
echo.
echo # Superset Configuration
echo SUPERSET_SECRET_KEY=change-this-secret-key-in-production
echo SUPERSET_LOAD_EXAMPLES=no
echo.
echo # Data Processor
echo PROCESSING_INTERVAL=3600
echo DATA_SOURCE_PATH=/app/data
) > .env

REM Build and start services
echo 🏗️ Building and starting Docker services...
docker-compose down --remove-orphans >nul 2>&1
docker-compose build --no-cache
docker-compose up -d

REM Wait for services to be ready
echo ⏳ Waiting for services to start...
timeout /t 60 /nobreak >nul

REM Check service health
echo 🔍 Checking service status...
docker-compose ps

REM Wait for database to be ready
echo 🗄️ Waiting for database to be ready...
:wait_db
docker-compose exec -T postgres pg_isready -U ecommerce_user -d ecommerce_price_comparison >nul 2>&1
if %errorlevel% neq 0 (
    echo    Waiting for postgres...
    timeout /t 5 /nobreak >nul
    goto wait_db
)
echo ✅ Database is ready!

REM Wait for Superset to be ready
echo 📊 Waiting for Superset to be ready...
:wait_superset
curl -s http://localhost:8080/health/ >nul 2>&1
if %errorlevel% neq 0 (
    echo    Waiting for Superset...
    timeout /t 10 /nobreak >nul
    goto wait_superset
)
echo ✅ Superset is ready!

REM Display access information
echo.
echo 🎉 E-commerce Price Comparison Dashboard is ready!
echo.
echo 🌐 Access URLs:
echo    Superset Dashboard: http://localhost:8080
echo    Username: admin
echo    Password: admin123
echo.
echo 🗄️ Database Connection Info:
echo    Host: localhost
echo    Port: 5432
echo    Database: ecommerce_price_comparison
echo    Username: ecommerce_user
echo    Password: ecommerce_password
echo.
echo 📊 Available Database Views:
echo    - price_comparison_view: Main product data with competitor analysis
echo    - savings_opportunities_view: Top savings opportunities
echo    - product_stats_mv: Brand statistics ^(materialized view^)
echo.
echo 🔧 Management Commands:
echo    View logs: docker-compose logs -f [service_name]
echo    Stop services: docker-compose down
echo    Restart services: docker-compose restart
echo    Access database: docker-compose exec postgres psql -U ecommerce_user -d ecommerce_price_comparison
echo    Access data processor logs: docker-compose logs -f data_processor
echo.
echo 📈 Next Steps:
echo    1. Open http://localhost:8080 in your browser
echo    2. Login with admin/admin123
echo    3. Go to Data ^> Databases ^> + Add Database
echo    4. Use PostgreSQL connection with the credentials above
echo    5. Create charts and dashboards using the available views
echo.
echo 📊 Sample SQL Queries:
echo    SELECT * FROM savings_opportunities_view LIMIT 10;
echo    SELECT * FROM price_comparison_view WHERE brand = 'HP';
echo    SELECT * FROM product_stats_mv ORDER BY total_products DESC;
echo.

REM Show container status
echo 📦 Container Status:
docker-compose ps

echo.
echo ✅ Setup complete! Dashboard is running at http://localhost:8080
pause
