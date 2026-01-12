"""
📊 E-commerce Data Processor Service
Automated data processing for price comparison dashboard
"""

import json
import os
import time
import schedule
import logging
import psutil
from datetime import datetime
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/data/processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EcommerceDataProcessor:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        self.data_path = os.getenv('DATA_SOURCE_PATH', '/app/data')
        self.processing_interval = int(os.getenv('PROCESSING_INTERVAL', 3600))
        self.engine = create_engine(self.db_url)
        
        # Connection pool
        self.pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=self.db_url
        )
        
        logger.info(f"Data processor initialized with interval: {self.processing_interval}s")
    
    def get_connection(self):
        """Get database connection from pool"""
        return self.pool.getconn()
    
    def release_connection(self, conn):
        """Release connection back to pool"""
        self.pool.putconn(conn)
    
    def log_processing(self, process_type: str, status: str, records: int = 0, 
                      error: Optional[str] = None, duration: int = 0):
        """Log processing activity"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO processing_logs 
                    (process_type, status, records_processed, error_message, processing_time_seconds, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (process_type, status, records, error, duration, datetime.now()))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log processing: {e}")
        finally:
            self.release_connection(conn)
    
    def load_json_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load and validate JSON data"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.warning(f"Expected list in {file_path}, got {type(data)}")
                return []
            
            logger.info(f"Loaded {len(data)} records from {file_path}")
            return data
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []
    
    def process_standardized_products(self, file_path: str) -> List[Dict[str, Any]]:
        """Process and validate standardized products"""
        products = self.load_json_data(file_path)
        processed = []
        
        for i, product in enumerate(products):
            try:
                processed_product = {
                    'primary_key': str(product.get('primary_key', ''))[:16],
                    'source': str(product.get('source', '')),
                    'original_title': str(product.get('original_title', ''))[:1000],
                    'price': float(product.get('price', 0)),
                    'currency': str(product.get('currency', 'KES'))[:10],
                    'url': str(product.get('url', ''))[:2000],
                    'scraped_at': product.get('scraped_at'),
                    'brand': str(product.get('brand', 'UNKNOWN'))[:50],
                    'model': str(product.get('model', 'UNKNOWN'))[:100],
                    'cpu_type': str(product.get('cpu_type', 'UNKNOWN'))[:50],
                    'ram_gb': int(product.get('ram_gb', 0)),
                    'storage': str(product.get('storage', 'UNKNOWN'))[:50],
                    'screen_size': str(product.get('screen_size', 'UNKNOWN'))[:20],
                    'spec_summary': str(product.get('spec_summary', ''))[:1000]
                }
                processed.append(processed_product)
            except Exception as e:
                logger.warning(f"Error processing product {i} from {file_path}: {e}")
        
        return processed
    
    def upsert_products(self, products: List[Dict[str, Any]]) -> int:
        """Upsert products into database"""
        if not products:
            return 0
        
        start_time = time.time()
        conn = self.get_connection()
        
        try:
            with conn.cursor() as cursor:
                # Create upsert query
                upsert_query = """
                INSERT INTO products (
                    primary_key, source, original_title, price, currency, url, 
                    scraped_at, brand, model, cpu_type, ram_gb, storage, 
                    screen_size, spec_summary
                ) VALUES %s
                ON CONFLICT (primary_key, source) 
                DO UPDATE SET 
                    original_title = EXCLUDED.original_title,
                    price = EXCLUDED.price,
                    url = EXCLUDED.url,
                    scraped_at = EXCLUDED.scraped_at,
                    brand = EXCLUDED.brand,
                    model = EXCLUDED.model,
                    cpu_type = EXCLUDED.cpu_type,
                    ram_gb = EXCLUDED.ram_gb,
                    storage = EXCLUDED.storage,
                    screen_size = EXCLUDED.screen_size,
                    spec_summary = EXCLUDED.spec_summary,
                    updated_at = CURRENT_TIMESTAMP
                """
                
                # Prepare data for insertion
                values = [
                    (
                        p['primary_key'], p['source'], p['original_title'], 
                        p['price'], p['currency'], p['url'], p['scraped_at'],
                        p['brand'], p['model'], p['cpu_type'], p['ram_gb'],
                        p['storage'], p['screen_size'], p['spec_summary']
                    )
                    for p in products
                ]
                
                execute_values(cursor, upsert_query, values)
                conn.commit()
                
                duration = int(time.time() - start_time)
                logger.info(f"Upserted {len(products)} products in {duration}s")
                
                return len(products)
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error upserting products: {e}")
            raise
        finally:
            self.release_connection(conn)
    
    def update_price_history(self) -> int:
        """Update price history for recent products"""
        start_time = time.time()
        conn = self.get_connection()
        
        try:
            with conn.cursor() as cursor:
                query = """
                INSERT INTO price_history (product_id, price, source, recorded_at)
                SELECT p.id, p.price, p.source, CURRENT_TIMESTAMP
                FROM products p
                WHERE p.scraped_at >= CURRENT_DATE - INTERVAL '7 days'
                AND NOT EXISTS (
                    SELECT 1 FROM price_history ph 
                    WHERE ph.product_id = p.id 
                    AND ph.price = p.price 
                    AND ph.recorded_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                )
                """
                cursor.execute(query)
                conn.commit()
                
                count = cursor.rowcount
                duration = int(time.time() - start_time)
                logger.info(f"Updated price history with {count} records in {duration}s")
                
                return count
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating price history: {e}")
            raise
        finally:
            self.release_connection(conn)
    
    def update_comparison_opportunities(self) -> int:
        """Update comparison opportunities table"""
        start_time = time.time()
        conn = self.get_connection()
        
        try:
            with conn.cursor() as cursor:
                # Clear existing opportunities
                cursor.execute("DELETE FROM comparison_opportunities")
                
                # Insert new opportunities
                query = """
                INSERT INTO comparison_opportunities (
                    primary_key, brand, model, min_price, max_price, 
                    savings, sources, product_count, last_updated
                )
                SELECT 
                    primary_key,
                    brand,
                    model,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    MAX(price) - MIN(price) as savings,
                    ARRAY_AGG(DISTINCT source) as sources,
                    COUNT(*) as product_count,
                    CURRENT_TIMESTAMP as last_updated
                FROM products
                WHERE primary_key != '' AND brand != 'UNKNOWN'
                GROUP BY primary_key, brand, model
                HAVING COUNT(DISTINCT source) > 1
                """
                cursor.execute(query)
                conn.commit()
                
                count = cursor.rowcount
                duration = int(time.time() - start_time)
                logger.info(f"Updated {count} comparison opportunities in {duration}s")
                
                return count
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating comparison opportunities: {e}")
            raise
        finally:
            self.release_connection(conn)
    
    def refresh_materialized_views(self):
        """Refresh materialized views for better performance"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT refresh_product_stats()")
                conn.commit()
                logger.info("Refreshed materialized views")
        except Exception as e:
            logger.error(f"Error refreshing materialized views: {e}")
        finally:
            self.release_connection(conn)
    
    def process_all_files(self):
        """Main processing function"""
        logger.info("Starting data processing cycle...")
        
        # Files to process
        files = [
            'standardized_jumia.json',
            'standardized_masoko.json',
            'standardized_phoneplacekenya.json',
            'standardized_laptopclinic.json'
        ]
        
        total_processed = 0
        start_time = time.time()
        
        try:
            # Process each file
            for filename in files:
                file_path = os.path.join(self.data_path, 'output', filename)
                if os.path.exists(file_path):
                    logger.info(f"Processing {filename}...")
                    products = self.process_standardized_products(file_path)
                    count = self.upsert_products(products)
                    total_processed += count
                    self.log_processing('file_processing', 'success', count)
                else:
                    logger.warning(f"File not found: {file_path}")
            
            # Update derived tables
            logger.info("Updating price history...")
            history_count = self.update_price_history()
            
            logger.info("Updating comparison opportunities...")
            opportunities_count = self.update_comparison_opportunities()
            
            # Refresh materialized views
            self.refresh_materialized_views()
            
            total_duration = int(time.time() - start_time)
            logger.info(f"Data processing complete in {total_duration}s")
            logger.info(f"Total products processed: {total_processed}")
            logger.info(f"Price history records: {history_count}")
            logger.info(f"Comparison opportunities: {opportunities_count}")
            
            self.log_processing('full_cycle', 'success', total_processed, duration=total_duration)
            
        except Exception as e:
            logger.error(f"Error in data processing: {e}")
            self.log_processing('full_cycle', 'error', total_processed, str(e), int(time.time() - start_time))
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics for monitoring"""
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'timestamp': datetime.now().isoformat()
        }
    
    def run_health_check(self):
        """Run health check and log results"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.release_connection(conn)
                
                if result:
                    logger.info("Health check passed")
                    return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
        
        return False


def main():
    """Main function"""
    logger.info("Starting E-commerce Data Processor Service...")
    
    processor = EcommerceDataProcessor()
    
    # Run initial processing
    processor.process_all_files()
    
    # Schedule regular updates
    schedule.every(processor.processing_interval).seconds.do(processor.process_all_files)
    schedule.every(5).minutes.do(processor.run_health_check)
    
    logger.info(f"Data processor started. Processing every {processor.processing_interval} seconds")
    
    # Keep the service running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Shutting down data processor...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
