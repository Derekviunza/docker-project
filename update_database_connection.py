"""
Update database connection in Superset with correct IP
"""

import psycopg2

def update_database_connection():
    """Update database connection with current IP"""
    
    # Connect to Superset database
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='superset',
        user='superset',
        password='superset'
    )
    cursor = conn.cursor()
    
    # Update database connection with correct IP
    cursor.execute("""
        UPDATE dbs 
        SET sqlalchemy_uri = 'postgresql+psycopg2://ecommerce_user:ecommerce_password@172.18.0.2:5432/ecommerce_price_comparison'
        WHERE database_name = 'ecommerce_price_comparison'
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database connection updated to 172.18.0.2:5432")

if __name__ == "__main__":
    update_database_connection()
