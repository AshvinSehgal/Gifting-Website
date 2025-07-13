import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect('GFT_clone.db')
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        address TEXT,
        phone TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        length REAL NOT NULL,
        width REAL NOT NULL,
        height REAL NOT NULL,
        price REAL NOT NULL,
        category TEXT,
        image_url TEXT,
        customizable BOOLEAN DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        base_product_id INTEGER,
        user_id INTEGER,
        customization_details TEXT,
        length REAL NOT NULL,
        width REAL NOT NULL,
        height REAL NOT NULL,
        price REAL NOT NULL,
        image_url TEXT,
        FOREIGN KEY (base_product_id) REFERENCES products(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        custom_product_id INTEGER,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (custom_product_id) REFERENCES custom_products(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount REAL,
        payment_status TEXT DEFAULT 'pending',
        razorpay_order_id TEXT,
        shiprocket_shipment_id TEXT,
        shipping_address TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        custom_product_id INTEGER,
        quantity INTEGER,
        price REAL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (custom_product_id) REFERENCES custom_products(id)
    )
    ''')

    # Insert sample data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ("Rakhi", "Rakhis with varying designs", 10, 1, 1, 99, "rakhis", "bandhan.jpeg", 1),
            ("Personalized Mug", "Custom printed mug with your photo", 10, 10, 10, 299, "soaps", "mug.jpg", 1),
            ("Photo Frame", "Wooden photo frame with customization", 10, 10, 1, 499, "bath salts", "frame.jpg", 1),
            ("Chocolate Box", "Assorted chocolates in gift box", 10, 10, 5, 349, "candles", "chocolates.jpg", 1),
        ]
        cursor.executemany('''
        INSERT INTO products (name, description, length, width, height, price, category, image_url, customizable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_products)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")