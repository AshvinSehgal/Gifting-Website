from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import razorpay
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Razorpay configuration
RAZORPAY_KEY_ID = 'your_razorpay_key_id'
RAZORPAY_KEY_SECRET = 'your_razorpay_key_secret'
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Shiprocket configuration
SHIPROCKET_EMAIL = 'your_shiprocket_email'
SHIPROCKET_PASSWORD = 'your_shiprocket_password'
SHIPROCKET_TOKEN = None

def get_db_connection():
    conn = sqlite3.connect('GFT_clone.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_shiprocket_token():
    global SHIPROCKET_TOKEN
    if SHIPROCKET_TOKEN:
        return SHIPROCKET_TOKEN
    
    url = "https://apiv2.shiprocket.in/v1/external/auth/login"
    payload = {
        "email": SHIPROCKET_EMAIL,
        "password": SHIPROCKET_PASSWORD
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        SHIPROCKET_TOKEN = response.json().get('token')
        return SHIPROCKET_TOKEN
    return None

@app.route('/')
def index():
    conn = get_db_connection()
    featured_products = conn.execute('SELECT * FROM products LIMIT 6').fetchall()
    customizable_products = conn.execute('SELECT * FROM products WHERE customizable = 1 LIMIT 4').fetchall()
    conn.close()
    return render_template('index.html', featured_products=featured_products, customizable_products=customizable_products)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    
    conn = get_db_connection()
    if category:
        products = conn.execute('SELECT * FROM products WHERE name LIKE ? AND category = ?', 
                               ('%'+query+'%', category)).fetchall()
    else:
        products = conn.execute('SELECT * FROM products WHERE name LIKE ?', 
                               ('%'+query+'%',)).fetchall()
    conn.close()
    return render_template('index.html', products=products, search_query=query)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    if product is None:
        flash('Product not found', 'danger')
        return redirect(url_for('index'))
    return render_template('product.html', product=product)

@app.route('/customize/<int:product_id>', methods=['GET', 'POST'])
def customize(product_id):
    if 'user_id' not in session:
        flash('Please login to customize products', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if request.method == 'POST':
        customization = request.form.get('customization')
        price = float(product['price']) + 100  # Additional customization charge
        
        # Save the custom product (in a real app, you'd save the customized image)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO custom_products (base_product_id, user_id, customization_details, price)
        VALUES (?, ?, ?, ?)
        ''', (product_id, session['user_id'], customization, price))
        custom_product_id = cursor.lastrowid
        
        # Add to cart
        cursor.execute('''
        INSERT INTO cart (user_id, custom_product_id, quantity)
        VALUES (?, ?, 1)
        ''', (session['user_id'], custom_product_id))
        
        conn.commit()
        conn.close()
        flash('Custom product added to cart!', 'success')
        return redirect(url_for('cart'))
    
    conn.close()
    return render_template('customize.html', product=product)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    conn = get_db_connection()
    
    # Check if product already in cart
    existing = conn.execute('''
    SELECT * FROM cart 
    WHERE user_id = ? AND product_id = ? AND custom_product_id IS NULL
    ''', (session['user_id'], product_id)).fetchone()
    
    if existing:
        new_quantity = existing['quantity'] + quantity
        conn.execute('''
        UPDATE cart SET quantity = ? 
        WHERE id = ?
        ''', (new_quantity, existing['id']))
    else:
        conn.execute('''
        INSERT INTO cart (user_id, product_id, quantity)
        VALUES (?, ?, ?)
        ''', (session['user_id'], product_id, quantity))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Product added to cart'})

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please login to view your cart', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cart_items = conn.execute('''
    SELECT c.id, c.quantity, 
           p.id as product_id, p.name as product_name, p.price as product_price, p.image_url as product_image,
           cp.id as custom_product_id, cp.customization_details, cp.price as custom_price
    FROM cart c
    LEFT JOIN products p ON c.product_id = p.id
    LEFT JOIN custom_products cp ON c.custom_product_id = cp.id
    WHERE c.user_id = ?
    ''', (session['user_id'],)).fetchall()
    
    total = 0
    for item in cart_items:
        if item['custom_product_id']:
            total += item['custom_price'] * item['quantity']
        else:
            total += item['product_price'] * item['quantity']
    
    conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    cart_id = request.form.get('cart_id')
    quantity = int(request.form.get('quantity', 1))
    
    if quantity <= 0:
        conn = get_db_connection()
        conn.execute('DELETE FROM cart WHERE id = ?', (cart_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Item removed from cart'})
    
    conn = get_db_connection()
    conn.execute('UPDATE cart SET quantity = ? WHERE id = ?', (quantity, cart_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Cart updated'})

@app.route('/remove_from_cart/<int:cart_id>')
def remove_from_cart(cart_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM cart WHERE id = ?', (cart_id,))
    conn.commit()
    conn.close()
    flash('Item removed from cart', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get cart items
    cart_items = conn.execute('''
    SELECT c.id, c.quantity, 
           p.id as product_id, p.name as product_name, p.price as product_price,
           cp.id as custom_product_id, cp.customization_details, cp.price as custom_price
    FROM cart c
    LEFT JOIN products p ON c.product_id = p.id
    LEFT JOIN custom_products cp ON c.custom_product_id = cp.id
    WHERE c.user_id = ?
    ''', (session['user_id'],)).fetchall()
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('index'))
    
    # Calculate total
    total = 0
    for item in cart_items:
        if item['custom_product_id']:
            total += item['custom_price'] * item['quantity']
        else:
            total += item['product_price'] * item['quantity']
    
    # Get user details
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            'amount': int(total * 100),  # amount in paise
            'currency': 'INR',
            'receipt': f'order_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'payment_capture': '1'
        })
        
        # Create order in database
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO orders (user_id, total_amount, razorpay_order_id, shipping_address)
        VALUES (?, ?, ?, ?)
        ''', (session['user_id'], total, razorpay_order['id'], request.form.get('address')))
        order_id = cursor.lastrowid
        
        # Add order items
        for item in cart_items:
            if item['custom_product_id']:
                cursor.execute('''
                INSERT INTO order_items (order_id, custom_product_id, quantity, price)
                VALUES (?, ?, ?, ?)
                ''', (order_id, item['custom_product_id'], item['quantity'], item['custom_price']))
            else:
                cursor.execute('''
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
                ''', (order_id, item['product_id'], item['quantity'], item['product_price']))
        
        # Clear cart
        conn.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
        
        conn.commit()
        conn.close()
        
        return render_template('checkout.html', 
                             razorpay_order_id=razorpay_order['id'],
                             razorpay_key=RAZORPAY_KEY_ID,
                             amount=total,
                             user=user)
    
    conn.close()
    return render_template('checkout.html', cart_items=cart_items, total=total, user=user)

@app.route('/payment_success', methods=['POST'])
def payment_success():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')
    
    # Verify payment
    params = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        razorpay_client.utility.verify_payment_signature(params)
        
        conn = get_db_connection()
        
        # Update order status
        conn.execute('''
        UPDATE orders SET payment_status = 'paid' 
        WHERE razorpay_order_id = ?
        ''', (razorpay_order_id,))
        
        # Get order details for Shiprocket
        order = conn.execute('''
        SELECT o.*, u.username, u.email, u.phone 
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.razorpay_order_id = ?
        ''', (razorpay_order_id,)).fetchone()
        
        order_items = conn.execute('''
        SELECT oi.*, p.name as product_name, cp.customization_details
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.id
        LEFT JOIN custom_products cp ON oi.custom_product_id = cp.id
        WHERE oi.order_id = ?
        ''', (order['id'],)).fetchall()
        
        # Create Shiprocket shipment
        token = get_shiprocket_token()
        if token:
            shipment_items = []
            for item in order_items:
                shipment_items.append({
                    "name": item['product_name'] or f"Custom {item['customization_details']}",
                    "sku": str(item['product_id'] or item['custom_product_id']),
                    "units": item['quantity'],
                    "selling_price": str(item['price'])
                })
            
            shipment_data = {
                "order_id": razorpay_order_id,
                "order_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pickup_location": "Primary",
                "channel_id": "",
                "comment": "",
                "billing_customer_name": order['username'],
                "billing_last_name": "",
                "billing_address": order['shipping_address'],
                "billing_address_2": "",
                "billing_city": "Mumbai",
                "billing_pincode": "400001",
                "billing_state": "Maharashtra",
                "billing_country": "India",
                "billing_email": order['email'],
                "billing_phone": order['phone'],
                "shipping_is_billing": True,
                "order_items": shipment_items,
                "payment_method": "Prepaid",
                "shipping_charges": 0,
                "giftwrap_charges": 0,
                "transaction_charges": 0,
                "total_discount": 0,
                "sub_total": order['total_amount'],
                "length": 10,
                "breadth": 15,
                "height": 20,
                "weight": 0.5
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            
            response = requests.post(
                "https://apiv2.shiprocket.in/v1/external/orders/create/adhoc",
                data=json.dumps(shipment_data),
                headers=headers
            )
            
            if response.status_code == 200:
                shipment_id = response.json().get('shipment_id')
                conn.execute('''
                UPDATE orders SET shiprocket_shipment_id = ?
                WHERE id = ?
                ''', (shipment_id, order['id']))
                conn.commit()
        
        conn.close()
        flash('Payment successful! Your order has been placed.', 'success')
        return redirect(url_for('account'))
    
    except Exception as e:
        print(f"Payment verification failed: {str(e)}")
        flash('Payment verification failed. Please contact support.', 'danger')
        return redirect(url_for('checkout'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        try:
            conn.execute('''
            INSERT INTO users (username, email, password)
            VALUES (?, ?, ?)
            ''', (username, email, generate_password_hash(password)))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'danger')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    orders = conn.execute('''
    SELECT o.*, 
           (SELECT COUNT(*) FROM order_items WHERE order_id = o.id) as item_count
    FROM orders o
    WHERE o.user_id = ?
    ORDER BY o.order_date DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('account.html', user=user, orders=orders)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)