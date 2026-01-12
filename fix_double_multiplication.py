import psycopg2

def fix_double_multiplication():
    """Fix Jumia prices that were multiplied by 1000 twice"""
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='ecommerce_price_comparison',
        user='ecommerce_user',
        password='ecommerce_password'
    )
    cursor = conn.cursor()
    
    # Divide product_listings table by 1000 (undo double multiplication)
    cursor.execute("""
        UPDATE product_listings 
        SET price = price / 1000 
        WHERE source = 'jumia'
    """)
    
    # Divide product_comparisons table by 1000 (undo double multiplication)
    cursor.execute("""
        UPDATE product_comparisons 
        SET jumia_price = jumia_price / 1000
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
    
    print("\nSample corrected Jumia prices (after fixing double multiplication):")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[2]} KES - {row[1]}")
    
    cursor.close()
    conn.close()
    print("Jumia prices fixed (divided by 1000) successfully!")

if __name__ == "__main__":
    fix_double_multiplication()
