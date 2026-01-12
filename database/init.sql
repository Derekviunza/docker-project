-- E-commerce Price Comparison Database Schema
-- PostgreSQL initialization script

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create main products table
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    primary_key VARCHAR(16) NOT NULL,
    source VARCHAR(50) NOT NULL,
    original_title TEXT,
    price DECIMAL(12,2),
    currency VARCHAR(10) DEFAULT 'KES',
    url TEXT,
    scraped_at TIMESTAMP WITH TIME ZONE,
    brand VARCHAR(50),
    model VARCHAR(100),
    cpu_type VARCHAR(50),
    ram_gb INTEGER,
    storage VARCHAR(50),
    screen_size VARCHAR(20),
    spec_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_product_source UNIQUE (primary_key, source),
    CONSTRAINT valid_price CHECK (price >= 0),
    CONSTRAINT valid_ram CHECK (ram_gb >= 0)
);

-- Create price history table for tracking changes
CREATE TABLE IF NOT EXISTS price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    price DECIMAL(12,2) NOT NULL,
    source VARCHAR(50) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_history_price CHECK (price >= 0)
);

-- Create comparison opportunities table
CREATE TABLE IF NOT EXISTS comparison_opportunities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    primary_key VARCHAR(16) NOT NULL,
    brand VARCHAR(50),
    model VARCHAR(100),
    min_price DECIMAL(12,2),
    max_price DECIMAL(12,2),
    savings DECIMAL(12,2),
    sources TEXT[],
    product_count INTEGER,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_min_price CHECK (min_price >= 0),
    CONSTRAINT valid_max_price CHECK (max_price >= 0),
    CONSTRAINT valid_savings CHECK (savings >= 0),
    CONSTRAINT valid_product_count CHECK (product_count >= 2)
);

-- Create processing logs table
CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    process_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    processing_time_seconds INTEGER,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_model ON products(model);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_source ON products(source);
CREATE INDEX IF NOT EXISTS idx_products_primary_key ON products(primary_key);
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at);
CREATE INDEX IF NOT EXISTS idx_products_brand_model ON products(brand, model);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_products_title_search ON products USING gin(to_tsvector('english', original_title));

-- Price history indexes
CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_recorded_at ON price_history(recorded_at);
CREATE INDEX IF NOT EXISTS idx_price_history_source ON price_history(source);

-- Comparison opportunities indexes
CREATE INDEX IF NOT EXISTS idx_comparison_savings ON comparison_opportunities(savings DESC);
CREATE INDEX IF NOT EXISTS idx_comparison_brand ON comparison_opportunities(brand);
CREATE INDEX IF NOT EXISTS idx_comparison_last_updated ON comparison_opportunities(last_updated);

-- Processing logs indexes
CREATE INDEX IF NOT EXISTS idx_processing_logs_started_at ON processing_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_processing_logs_status ON processing_logs(status);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_products_updated_at 
    BEFORE UPDATE ON products 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Views for dashboard
CREATE OR REPLACE VIEW price_comparison_view AS
SELECT 
    p.id,
    p.primary_key,
    p.brand,
    p.model,
    p.spec_summary,
    p.cpu_type,
    p.ram_gb,
    p.storage,
    p.screen_size,
    p.price,
    p.currency,
    p.source,
    p.url,
    p.scraped_at,
    p.created_at,
    p.updated_at,
    -- Competitor analysis
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM products p2 
            WHERE p2.primary_key = p.primary_key 
            AND p2.source != p.source
        ) THEN true
        ELSE false
    END as has_competitors,
    -- Price comparison metrics
    (SELECT MIN(p2.price) 
     FROM products p2 
     WHERE p2.primary_key = p.primary_key) as min_price_for_model,
    (SELECT MAX(p2.price) 
     FROM products p2 
     WHERE p2.primary_key = p.primary_key) as max_price_for_model,
    p.price - COALESCE((SELECT MIN(p2.price) 
                       FROM products p2 
                       WHERE p2.primary_key = p.primary_key), p.price) as potential_savings,
    -- Count of competitors
    (SELECT COUNT(DISTINCT p2.source) 
     FROM products p2 
     WHERE p2.primary_key = p.primary_key) as num_sources
FROM products p;

CREATE OR REPLACE VIEW savings_opportunities_view AS
SELECT 
    co.primary_key,
    co.brand,
    co.model,
    co.min_price,
    co.max_price,
    co.savings,
    co.sources,
    co.product_count,
    co.last_updated,
    -- Additional metrics
    ROUND((co.savings / co.min_price) * 100, 2) as savings_percentage,
    -- Sample product details
    (SELECT p.original_title 
     FROM products p 
     WHERE p.primary_key = co.primary_key 
     ORDER BY p.price ASC 
     LIMIT 1) as sample_title,
    (SELECT p.spec_summary 
     FROM products p 
     WHERE p.primary_key = co.primary_key 
     ORDER BY p.price ASC 
     LIMIT 1) as sample_specs
FROM comparison_opportunities co
WHERE co.product_count > 1
ORDER BY co.savings DESC;

-- Materialized view for better performance (refreshed periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS product_stats_mv AS
SELECT 
    brand,
    COUNT(*) as total_products,
    COUNT(DISTINCT primary_key) as unique_models,
    COUNT(DISTINCT source) as num_sources,
    ROUND(AVG(price), 2) as avg_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    ROUND(STDDEV(price), 2) as price_stddev,
    COUNT(CASE WHEN has_competitors THEN 1 END) as products_with_competitors
FROM price_comparison_view
WHERE brand != 'UNKNOWN'
GROUP BY brand;

-- Create unique index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_product_stats_mv_brand ON product_stats_mv(brand);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_product_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY product_stats_mv;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ecommerce_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ecommerce_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO ecommerce_user;

-- Create initial admin user for Superset (if needed)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'superset') THEN
        CREATE ROLE superset WITH LOGIN PASSWORD 'superset_password';
        GRANT CONNECT ON DATABASE ecommerce_price_comparison TO superset;
        GRANT USAGE ON SCHEMA public TO superset;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO superset;
    END IF;
END
$$;
