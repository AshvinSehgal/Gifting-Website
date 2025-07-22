import sqlite3
from werkzeug.security import generate_password_hash
import os

def init_db():
    # Create database directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect('data/inventory.db')
    cursor = conn.cursor()

    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        country TEXT DEFAULT 'India',
        pincode TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_admin BOOLEAN DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        image_url TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        short_description TEXT,
        price REAL NOT NULL,
        sale_price REAL,
        category_id INTEGER,
        stock_quantity INTEGER DEFAULT 0,
        weight REAL DEFAULT 0.5,
        length REAL DEFAULT 10,
        width REAL DEFAULT 10,
        height REAL DEFAULT 10,
        sku TEXT UNIQUE,
        featured BOOLEAN DEFAULT 0,
        customizable BOOLEAN DEFAULT 0,
        min_customization_price REAL DEFAULT 0,
        tax_class TEXT DEFAULT 'standard',
        shipping_class TEXT DEFAULT 'standard',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS product_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        image_url TEXT NOT NULL,
        is_primary BOOLEAN DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        base_product_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        customization_details TEXT NOT NULL,
        design_data TEXT,
        price REAL NOT NULL,
        image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (base_product_id) REFERENCES products(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER,
        custom_product_id INTEGER,
        quantity INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (custom_product_id) REFERENCES custom_products(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        order_number TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'pending',
        subtotal REAL NOT NULL,
        shipping_total REAL NOT NULL,
        tax_total REAL NOT NULL,
        discount_total REAL DEFAULT 0,
        total REAL NOT NULL,
        payment_method TEXT NOT NULL,
        payment_status TEXT DEFAULT 'pending',
        razorpay_order_id TEXT,
        razorpay_payment_id TEXT,
        razorpay_signature TEXT,
        shipping_first_name TEXT,
        shipping_last_name TEXT,
        shipping_address TEXT NOT NULL,
        shipping_city TEXT NOT NULL,
        shipping_state TEXT NOT NULL,
        shipping_country TEXT DEFAULT 'India',
        shipping_pincode TEXT NOT NULL,
        shipping_phone TEXT NOT NULL,
        shipping_email TEXT,
        shiprocket_shipment_id TEXT,
        shiprocket_awb TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        custom_product_id INTEGER,
        product_name TEXT NOT NULL,
        product_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        subtotal REAL NOT NULL,
        tax_amount REAL NOT NULL,
        weight REAL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (custom_product_id) REFERENCES custom_products(id)
    )
    ''')

    # Insert initial admin user if not exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
        INSERT INTO users (username, email, password, is_admin)
        VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@igpclone.com', generate_password_hash('admin123'), 1))
    
    # Insert sample categories if empty
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        sample_categories = [
            ("Personalized Gifts", "personalized-gifts", "Custom gifts with personal touch"),
            ("Home Decor", "home-decor", "Beautiful items for your home"),
            ("Jewelry", "jewelry", "Elegant jewelry pieces"),
            ("Stationery", "stationery", "Customized stationery items"),
            ("Special Occasions", "special-occasions", "Gifts for special events")
        ]
        cursor.executemany('''
        INSERT INTO categories (name, slug, description)
        VALUES (?, ?, ?)
        ''', sample_categories)
    
    # Insert sample products if empty
    cursor.execute("SELECT id FROM categories WHERE slug = 'personalized-gifts'")
    category_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ("Rakhi", "rakhi", "Customized rakhis", 
             "Rakhi", 149, 99, category_id, 100, 0.01, 10, 1, 1, 
             "RAKHI-001", 1, 1, 100, "standard", "standard"),
            ("Personalized Photo Frame", "personalized-photo-frame", "Custom photo frame with your picture", 
             "Wooden frame with glass front", 599, 499, category_id, 100, 0.8, 12, 15, 2, 
             "PHFRM-001", 1, 1, 100, "standard", "fragile"),
            ("Custom Engraved Bracelet", "custom-engraved-bracelet", "Silver bracelet with custom engraving",
             "Adjustable silver bracelet", 1299, None, category_id, 50, 0.2, 15, 10, 1,
             "BRAC-001", 1, 1, 200, "standard", "jewelry"),
            ("Printed Coffee Mug", "printed-coffee-mug", "Coffee mug with your photo",
             "Ceramic mug, 350ml capacity", 399, 349, category_id, 200, 0.5, 10, 10, 12,
             "MUG-001", 1, 1, 50, "standard", "standard")
        ]
        cursor.executemany('''
        INSERT INTO products (name, slug, description, short_description, price, sale_price, 
        category_id, stock_quantity, weight, length, width, height, sku, featured, customizable, 
        min_customization_price, tax_class, shipping_class)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_products)
        
        # Insert product images
        cursor.execute("SELECT id FROM products WHERE slug = 'rakhi'")
        product_id = cursor.fetchone()[0]
        cursor.execute('''
        INSERT INTO product_images (product_id, image_url, is_primary)
        VALUES (?, ?, ?)
        ''', (product_id, "bandhan.jpeg", 1))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")