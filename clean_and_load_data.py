"""
Advanced Data Cleaning and Loading Script

This script:
1. Loads the working standardized data from the working_output directory
2. Creates intelligent product matching groups
3. Generates comparison tables with exact matches
4. Loads all data into PostgreSQL with proper relationships
"""

import json
import psycopg2
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import re

def load_standardized_data() -> List[Dict]:
    """Load all standardized data from working_output directory"""
    data = []
    working_dir = Path("working_output")
    
    # Load standardized files
    files = [
        "standardized_jumia.json",
        "standardized_laptopclinic.json", 
        "standardized_masoko.json",
        "standardized_phoneplacekenya.json"
    ]
    
    for file_name in files:
        file_path = working_dir / file_name
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                data.extend(file_data)
                print(f"Loaded {len(file_data)} records from {file_name}")
    
    return data

def create_product_groups(data: List[Dict]) -> Dict[str, List[Dict]]:
    """Create product groups based on primary_key and fuzzy matching"""
    groups = defaultdict(list)
    
    # Group by primary_key first (exact matches)
    for item in data:
        pk = item.get('primary_key', '')
        if pk:
            groups[pk].append(item)
    
    # Create fuzzy matching groups for items without primary_key or with UNKNOWN brands
    fuzzy_groups = defaultdict(list)
    
    for item in data:
        if not item.get('primary_key') or item.get('brand') == 'UNKNOWN':
            # Create fuzzy key based on model and specs
            model = item.get('model', '').upper()
            ram = item.get('ram_gb', 0)
            storage = item.get('storage', '').upper()
            cpu = item.get('cpu_type', '').upper()
            
            if model != 'UNKNOWN':
                fuzzy_key = f"{model}_{ram}GB_{storage}_{cpu}"
                fuzzy_groups[fuzzy_key].append(item)
    
    return dict(groups), dict(fuzzy_groups)

def extract_specifications(item: Dict) -> Dict:
    """Extract and normalize specifications"""
    return {
        'brand': item.get('brand', 'UNKNOWN'),
        'model': item.get('model', 'UNKNOWN'),
        'cpu_type': item.get('cpu_type', 'UNKNOWN'),
        'ram_gb': item.get('ram_gb', 0),
        'storage': item.get('storage', 'UNKNOWN'),
        'screen_size': item.get('screen_size_inches', 0)
    }

def create_database_and_tables(conn):
    """Create database tables"""
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS product_comparisons CASCADE")
    cursor.execute("DROP TABLE IF EXISTS product_listings CASCADE")
    cursor.execute("DROP TABLE IF EXISTS product_groups CASCADE")
    
    # Create product_listings table (all individual listings)
    cursor.execute("""
        CREATE TABLE product_listings (
            id SERIAL PRIMARY KEY,
            primary_key VARCHAR(20),
            source VARCHAR(50),
            original_title TEXT,
            price DECIMAL(10,3),
            currency VARCHAR(10),
            url TEXT,
            scraped_at TIMESTAMP,
            brand VARCHAR(50),
            model VARCHAR(100),
            cpu_type VARCHAR(50),
            ram_gb INTEGER,
            storage VARCHAR(50),
            screen_size DECIMAL(4,1),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create product_groups table (matched products)
    cursor.execute("""
        CREATE TABLE product_groups (
            id SERIAL PRIMARY KEY,
            group_key VARCHAR(100),
            group_type VARCHAR(20), -- 'exact' or 'fuzzy'
            brand VARCHAR(50),
            model VARCHAR(100),
            cpu_type VARCHAR(50),
            ram_gb INTEGER,
            storage VARCHAR(50),
            screen_size DECIMAL(4,1),
            sources TEXT,
            product_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create product_comparisons table (price comparisons)
    cursor.execute("""
        CREATE TABLE product_comparisons (
            id SERIAL PRIMARY KEY,
            group_key VARCHAR(100),
            brand VARCHAR(50),
            model VARCHAR(100),
            cpu_type VARCHAR(50),
            ram_gb INTEGER,
            storage VARCHAR(50),
            screen_size DECIMAL(4,1),
            laptopclinic_price DECIMAL(10,3),
            jumia_price DECIMAL(10,3),
            masoko_price DECIMAL(10,3),
            phoneplacekenya_price DECIMAL(10,3),
            cheapest_source VARCHAR(50),
            max_savings DECIMAL(10,3),
            comparison_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    print("Database tables created successfully")

def load_product_listings(conn, data: List[Dict]):
    """Load all product listings"""
    cursor = conn.cursor()
    
    for item in data:
        # Handle empty scraped_at
        scraped_at = item.get('scraped_at')
        if scraped_at == '' or scraped_at is None:
            scraped_at = None
        
        cursor.execute("""
            INSERT INTO product_listings 
            (primary_key, source, original_title, price, currency, url, scraped_at,
             brand, model, cpu_type, ram_gb, storage, screen_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            item.get('primary_key'),
            item.get('source'),
            item.get('original_title'),
            item.get('price'),
            item.get('currency'),
            item.get('url'),
            scraped_at,
            item.get('brand'),
            item.get('model'),
            item.get('cpu_type'),
            item.get('ram_gb'),
            item.get('storage'),
            item.get('screen_size_inches')
        ))
    
    conn.commit()
    print(f"Loaded {len(data)} product listings")

def load_product_groups(conn, exact_groups: Dict, fuzzy_groups: Dict):
    """Load product groups"""
    cursor = conn.cursor()
    
    # Load exact groups
    for group_key, items in exact_groups.items():
        if len(items) > 1:  # Only groups with multiple sources
            specs = extract_specifications(items[0])
            sources = ', '.join(set(item['source'] for item in items))
            
            cursor.execute("""
                INSERT INTO product_groups 
                (group_key, group_type, brand, model, cpu_type, ram_gb, storage, 
                 screen_size, sources, product_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                group_key, 'exact', specs['brand'], specs['model'], specs['cpu_type'],
                specs['ram_gb'], specs['storage'], specs['screen_size'], sources, len(items)
            ))
    
    # Load fuzzy groups
    for group_key, items in fuzzy_groups.items():
        if len(items) > 1:  # Only groups with multiple sources
            specs = extract_specifications(items[0])
            sources = ', '.join(set(item['source'] for item in items))
            
            cursor.execute("""
                INSERT INTO product_groups 
                (group_key, group_type, brand, model, cpu_type, ram_gb, storage, 
                 screen_size, sources, product_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                f"fuzzy_{group_key}", 'fuzzy', specs['brand'], specs['model'], specs['cpu_type'],
                specs['ram_gb'], specs['storage'], specs['screen_size'], sources, len(items)
            ))
    
    conn.commit()
    print(f"Loaded {len(exact_groups)} exact groups and {len(fuzzy_groups)} fuzzy groups")

def load_price_comparisons(conn, exact_groups: Dict, fuzzy_groups: Dict):
    """Load price comparisons with LaptopClinic as baseline"""
    cursor = conn.cursor()
    
    all_groups = {**exact_groups, **fuzzy_groups}
    
    for group_key, items in all_groups.items():
        if len(items) > 1:  # Only groups with multiple sources
            specs = extract_specifications(items[0])
            
            # Get prices by source
            prices = {}
            for item in items:
                source = item['source']
                prices[source] = item.get('price', 0)
            
            laptopclinic_price = prices.get('laptopclinic', 0)
            jumia_price = prices.get('jumia', 0)
            masoko_price = prices.get('masoko', 0)
            phoneplacekenya_price = prices.get('phoneplacekenya', 0)
            
            # Find cheapest source
            price_comparison = {
                'laptopclinic': laptopclinic_price,
                'jumia': jumia_price,
                'masoko': masoko_price,
                'phoneplacekenya': phoneplacekenya_price
            }
            
            cheapest_source = min(price_comparison.items(), key=lambda x: x[1] if x[1] > 0 else float('inf'))[0]
            
            # Calculate max savings
            other_prices = [p for source, p in price_comparison.items() if source != 'laptopclinic' and p > 0]
            max_savings = max([laptopclinic_price - p for p in other_prices] + [0])
            
            cursor.execute("""
                INSERT INTO product_comparisons 
                (group_key, brand, model, cpu_type, ram_gb, storage, screen_size,
                 laptopclinic_price, jumia_price, masoko_price, phoneplacekenya_price,
                 cheapest_source, max_savings, comparison_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                group_key, specs['brand'], specs['model'], specs['cpu_type'],
                specs['ram_gb'], specs['storage'], specs['screen_size'],
                laptopclinic_price, jumia_price, masoko_price, phoneplacekenya_price,
                cheapest_source, max_savings, len([p for p in [jumia_price, masoko_price, phoneplacekenya_price] if p > 0])
            ))
    
    conn.commit()
    print(f"Loaded price comparisons for {len([g for g in all_groups.values() if len(g) > 1])} product groups")

def main():
    """Main execution function"""
    print("Starting advanced data cleaning and loading...")
    
    # Load data
    data = load_standardized_data()
    print(f"Total records loaded: {len(data)}")
    
    # Create product groups
    exact_groups, fuzzy_groups = create_product_groups(data)
    print(f"Created {len(exact_groups)} exact groups and {len(fuzzy_groups)} fuzzy groups")
    
    # Database connection
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='ecommerce_price_comparison',
        user='ecommerce_user',
        password='ecommerce_password'
    )
    
    try:
        # Create tables
        create_database_and_tables(conn)
        
        # Load data
        load_product_listings(conn, data)
        load_product_groups(conn, exact_groups, fuzzy_groups)
        load_price_comparisons(conn, exact_groups, fuzzy_groups)
        
        print("\n=== Summary ===")
        print(f"Total product listings: {len(data)}")
        print(f"Exact product groups: {len(exact_groups)}")
        print(f"Fuzzy product groups: {len(fuzzy_groups)}")
        print(f"Total comparison groups: {len([g for g in exact_groups.values() if len(g) > 1]) + len([g for g in fuzzy_groups.values() if len(g) > 1])}")
        
        # Show sample comparison
        cursor = conn.cursor()
        cursor.execute("""
            SELECT brand, model, laptopclinic_price, jumia_price, masoko_price, 
                   cheapest_source, max_savings 
            FROM product_comparisons 
            WHERE comparison_count > 0 
            ORDER BY max_savings DESC 
            LIMIT 5
        """)
        
        print("\n=== Top 5 Best Savings ===")
        for row in cursor.fetchall():
            print(f"{row[0]} {row[1]}: LaptopClinic KES{row[2]} vs {row[5]} - Save KES{row[6]}")
        
    finally:
        conn.close()
    
    print("\nData loading completed successfully!")

if __name__ == "__main__":
    main()
