import psycopg2

def recalculate_comparisons():
    """Recalculate price comparisons after fixing Jumia prices"""
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='ecommerce_price_comparison',
        user='ecommerce_user',
        password='ecommerce_password'
    )
    cursor = conn.cursor()
    
    # Update product_comparisons with corrected prices
    cursor.execute("""
        UPDATE product_comparisons 
        SET 
            jumia_price = pl.jumia_price,
            masoko_price = pl.masoko_price,
            phoneplacekenya_price = pl.phoneplacekenya_price,
            jumia_diff = pl.jumia_price - laptopclinic_price,
            masoko_diff = pl.masoko_price - laptopclinic_price,
            phoneplacekenya_diff = pl.phoneplacekenya_price - laptopclinic_price,
            max_savings = GREATEST(
                CASE WHEN pl.jumia_price > 0 THEN laptopclinic_price - pl.jumia_price ELSE 0 END,
                CASE WHEN pl.masoko_price > 0 THEN laptopclinic_price - pl.masoko_price ELSE 0 END,
                CASE WHEN pl.phoneplacekenya_price > 0 THEN laptopclinic_price - pl.phoneplacekenya_price ELSE 0 END
            ),
            cheapest_source = CASE 
                WHEN pl.jumia_price > 0 AND pl.jumia_price < LEAST(laptopclinic_price, COALESCE(pl.masoko_price, 999999999), COALESCE(pl.phoneplacekenya_price, 999999999)) THEN 'jumia'
                WHEN pl.masoko_price > 0 AND pl.masoko_price < LEAST(laptopclinic_price, COALESCE(pl.jumia_price, 999999999), COALESCE(pl.phoneplacekenya_price, 999999999)) THEN 'masoko'
                WHEN pl.phoneplacekenya_price > 0 AND pl.phoneplacekenya_price < LEAST(laptopclinic_price, COALESCE(pl.jumia_price, 999999999), COALESCE(pl.masoko_price, 999999999)) THEN 'phoneplacekenya'
                ELSE 'laptopclinic'
            END
        FROM (
            SELECT 
                group_key,
                AVG(CASE WHEN source = 'laptopclinic' THEN price END) as laptopclinic_price,
                AVG(CASE WHEN source = 'jumia' THEN price END) as jumia_price,
                AVG(CASE WHEN source = 'masoko' THEN price END) as masoko_price,
                AVG(CASE WHEN source = 'phoneplacekenya' THEN price END) as phoneplacekenya_price
            FROM product_listings
            WHERE price > 0
            GROUP BY group_key
        ) pl
        WHERE product_comparisons.group_key = pl.group_key
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Price comparisons recalculated successfully!")

if __name__ == "__main__":
    recalculate_comparisons()
