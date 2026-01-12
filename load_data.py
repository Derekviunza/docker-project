import json
import psycopg2
from pathlib import Path

def load_json_to_postgres():
    # Database connection
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='ecommerce_price_comparison',
        user='ecommerce_user',
        password='ecommerce_password'
    )
    cur = conn.cursor()
    
    # Files to load
    files = {
        'jumia': 'data/output/standardized_jumia.json',
        'laptopclinic': 'data/output/standardized_laptopclinic.json', 
        'masoko': 'data/output/standardized_masoko.json',
        'phoneplacekenya': 'data/output/standardized_phoneplacekenya.json'
    }
    
    for table_name, file_path in files.items():
        print(f"Loading {file_path} into {table_name} table...")
        
        # Drop table if exists
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create table
        cur.execute(f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                source TEXT,
                title TEXT,
                price FLOAT,
                currency TEXT,
                url TEXT,
                match_key TEXT,
                scraped_at TIMESTAMP,
                brand TEXT,
                model TEXT,
                cpu TEXT,
                ram_gb INTEGER,
                storage_gb INTEGER,
                product_id TEXT
            )
        """)
        
        # Load JSON data
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Insert data
        for item in data:
            # Handle timestamp - skip if invalid
            scraped_at = item.get('scraped_at')
            if scraped_at == '' or scraped_at is None:
                scraped_at = None
            
            cur.execute(f"""
                INSERT INTO {table_name} 
                (source, title, price, currency, url, match_key, scraped_at, 
                 brand, model, cpu, ram_gb, storage_gb, product_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                item.get('source'),
                item.get('title'),
                item.get('price'),
                item.get('currency'),
                item.get('url'),
                item.get('match_key'),
                scraped_at,
                item.get('brand'),
                item.get('model'),
                item.get('cpu'),
                item.get('ram_gb'),
                item.get('storage_gb'),
                item.get('product_id')
            ))
        
        print(f"Loaded {len(data)} records into {table_name}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("All data loaded successfully!")

if __name__ == "__main__":
    load_json_to_postgres()
