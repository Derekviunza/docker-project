import psycopg2

def fix_jumia_prices():
    """Multiply Jumia prices by 1000 to fix the division issue"""
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='ecommerce_price_comparison',
        user='ecommerce_user',
        password='ecommerce_password'
    )
    cursor = conn.cursor()
    
    # Update product_listings table
    cursor.execute("""
        UPDATE product_listings 
        SET price = price * 1000 
        WHERE source = 'jumia'
    """)
    
    # Update product_comparisons table - just the jumia_price
    cursor.execute("""
        UPDATE product_comparisons 
        SET jumia_price = jumia_price * 1000
        WHERE jumia_price > 0
    """)
    
    conn.commit()
    
    # Show sample corrected prices
    cursor.execute("""
        SELECT source, original_title, price 
        FROM product_listings 
        WHERE source = 'jumia' 
        LIMIT 3
    """)
    
    print("\nSample corrected Jumia prices:")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[2]} KES - {row[1]}")
    
    cursor.close()
    conn.close()
    print("Jumia prices multiplied by 1000 successfully!")
    
if __name__ == "__main__":
    fix_jumia_prices()
