import psycopg2

def rebuild_comparisons():
    """Rebuild product_comparisons table with correct prices"""
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='ecommerce_price_comparison',
        user='ecommerce_user',
        password='ecommerce_password'
    )
    cursor = conn.cursor()
    
    # Drop and recreate product_comparisons table
    cursor.execute("DROP TABLE IF EXISTS product_comparisons CASCADE")
    
    cursor.execute("""
        CREATE TABLE product_comparisons (
            id SERIAL PRIMARY KEY,
            group_key VARCHAR(100),
            group_type VARCHAR(20),
            brand VARCHAR(50),
            model VARCHAR(100),
            cpu_type VARCHAR(50),
            ram_gb INTEGER,
            storage VARCHAR(50),
            screen_size DECIMAL(4,1),
            laptopclinic_price DECIMAL(15,3),
            jumia_price DECIMAL(15,3),
            masoko_price DECIMAL(15,3),
            phoneplacekenya_price DECIMAL(15,3),
            cheapest_source VARCHAR(50),
            max_savings DECIMAL(15,3),
            comparison_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert comparison data using product_groups
    cursor.execute("""
        INSERT INTO product_comparisons 
        (group_key, group_type, brand, model, cpu_type, ram_gb, storage, screen_size,
         laptopclinic_price, jumia_price, masoko_price, phoneplacekenya_price,
         cheapest_source, max_savings, comparison_count)
        WITH price_groups AS (
            SELECT 
                pg.group_key,
                pg.group_type,
                pg.brand,
                pg.model,
                pg.cpu_type,
                pg.ram_gb,
                pg.storage,
                pg.screen_size,
                AVG(CASE WHEN pl.source = 'laptopclinic' THEN pl.price END) as laptopclinic_price,
                AVG(CASE WHEN pl.source = 'jumia' THEN pl.price END) as jumia_price,
                AVG(CASE WHEN pl.source = 'masoko' THEN pl.price END) as masoko_price,
                AVG(CASE WHEN pl.source = 'phoneplacekenya' THEN pl.price END) as phoneplacekenya_price
            FROM product_groups pg
            JOIN product_listings pl ON pg.group_key = pl.group_key
            WHERE pl.price > 0 AND pg.product_count > 1
            GROUP BY pg.group_key, pg.group_type, pg.brand, pg.model, pg.cpu_type, pg.ram_gb, pg.storage, pg.screen_size
        ),
        price_analysis AS (
            SELECT 
                *,
                (jumia_price - laptopclinic_price) as jumia_diff,
                (masoko_price - laptopclinic_price) as masoko_diff,
                (phoneplacekenya_price - laptopclinic_price) as phoneplacekenya_diff,
                GREATEST(
                    CASE WHEN jumia_price > 0 THEN laptopclinic_price - jumia_price ELSE 0 END,
                    CASE WHEN masoko_price > 0 THEN laptopclinic_price - masoko_price ELSE 0 END,
                    CASE WHEN phoneplacekenya_price > 0 THEN laptopclinic_price - phoneplacekenya_price ELSE 0 END
                ) as max_savings,
                CASE 
                    WHEN jumia_price > 0 AND jumia_price < LEAST(laptopclinic_price, COALESCE(masoko_price, 999999999), COALESCE(phoneplacekenya_price, 999999999)) THEN 'jumia'
                    WHEN masoko_price > 0 AND masoko_price < LEAST(laptopclinic_price, COALESCE(jumia_price, 999999999), COALESCE(phoneplacekenya_price, 999999999)) THEN 'masoko'
                    WHEN phoneplacekenya_price > 0 AND phoneplacekenya_price < LEAST(laptopclinic_price, COALESCE(jumia_price, 999999999), COALESCE(masoko_price, 999999999)) THEN 'phoneplacekenya'
                    ELSE 'laptopclinic'
                END as cheapest_source,
                (CASE WHEN jumia_price > 0 THEN 1 ELSE 0 END + 
                 CASE WHEN masoko_price > 0 THEN 1 ELSE 0 END + 
                 CASE WHEN phoneplacekenya_price > 0 THEN 1 ELSE 0 END) as comparison_count
            FROM price_groups
        )
        SELECT 
            group_key, group_type, brand, model, cpu_type, ram_gb, storage, screen_size,
            laptopclinic_price, jumia_price, masoko_price, phoneplacekenya_price,
            cheapest_source, max_savings, comparison_count
        FROM price_analysis
        ORDER BY max_savings DESC
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Product comparisons rebuilt successfully!")

if __name__ == "__main__":
    rebuild_comparisons()
