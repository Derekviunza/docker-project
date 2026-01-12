#!/bin/bash

# 🐳 E-commerce Price Comparison Dashboard Setup
# Clean Docker-based deployment

set -e

echo "🚀 Starting E-commerce Price Comparison Dashboard Setup..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed."
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "📁 Project directory: $PROJECT_DIR"

# Copy processed data to docker project
echo "📋 Copying processed data..."
mkdir -p "$PROJECT_DIR/docker-project/data/output"
cp "$PROJECT_DIR/output/standardized_"*.json "$PROJECT_DIR/docker-project/data/output/" 2>/dev/null || echo "⚠️ No standardized files found"

# Navigate to docker project
cd "$PROJECT_DIR/docker-project"

# Create environment file
echo "🔧 Creating environment file..."
cat > .env << EOF
# Database Configuration
POSTGRES_DB=ecommerce_price_comparison
POSTGRES_USER=ecommerce_user
POSTGRES_PASSWORD=ecommerce_password

# Superset Configuration
SUPERSET_SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || echo "change-this-secret-key-in-production")
SUPERSET_LOAD_EXAMPLES=no

# Data Processor
PROCESSING_INTERVAL=3600
DATA_SOURCE_PATH=/app/data
EOF

# Build and start services
echo "🏗️ Building and starting Docker services..."
docker-compose down --remove-orphans 2>/dev/null || true
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 60

# Check service health
echo "🔍 Checking service status..."
docker-compose ps

# Wait for database to be ready
echo "🗄️ Waiting for database to be ready..."
until docker-compose exec -T postgres pg_isready -U ecommerce_user -d ecommerce_price_comparison > /dev/null 2>&1; do
    echo "   Waiting for postgres..."
    sleep 5
done

echo "✅ Database is ready!"

# Wait for Superset to be ready
echo "📊 Waiting for Superset to be ready..."
until curl -s http://localhost:8080/health/ > /dev/null 2>&1; do
    echo "   Waiting for Superset..."
    sleep 10
done

echo "✅ Superset is ready!"

# Display access information
echo ""
echo "🎉 E-commerce Price Comparison Dashboard is ready!"
echo ""
echo "🌐 Access URLs:"
echo "   Superset Dashboard: http://localhost:8080"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "🗄️ Database Connection Info:"
echo "   Host: localhost"
echo "   Port: 5432"
echo "   Database: ecommerce_price_comparison"
echo "   Username: ecommerce_user"
echo "   Password: ecommerce_password"
echo ""
echo "📊 Available Database Views:"
echo "   - price_comparison_view: Main product data with competitor analysis"
echo "   - savings_opportunities_view: Top savings opportunities"
echo "   - product_stats_mv: Brand statistics (materialized view)"
echo ""
echo "🔧 Management Commands:"
echo "   View logs: docker-compose logs -f [service_name]"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo "   Access database: docker-compose exec postgres psql -U ecommerce_user -d ecommerce_price_comparison"
echo "   Access data processor logs: docker-compose logs -f data_processor"
echo ""
echo "📈 Next Steps:"
echo "   1. Open http://localhost:8080 in your browser"
echo "   2. Login with admin/admin123"
echo "   3. Go to Data > Databases > + Add Database"
echo "   4. Use PostgreSQL connection with the credentials above"
echo "   5. Create charts and dashboards using the available views"
echo ""
echo "📊 Sample SQL Queries:"
echo "   SELECT * FROM savings_opportunities_view LIMIT 10;"
echo "   SELECT * FROM price_comparison_view WHERE brand = 'HP';"
echo "   SELECT * FROM product_stats_mv ORDER BY total_products DESC;"
echo ""

# Show container status
echo "📦 Container Status:"
docker-compose ps

echo ""
echo "✅ Setup complete! Dashboard is running at http://localhost:8080"
