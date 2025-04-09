from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from config import DB_CONFIG

app = Flask(__name__)
app.secret_key = 'zomato_clone_secret'

def init_db():
    conn = mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )
    cursor = conn.cursor()

    cursor.execute("CREATE DATABASE IF NOT EXISTS zomato_db")
    conn.database = 'zomato_db'

    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        address VARCHAR(255),
        email VARCHAR(100) UNIQUE
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS restaurants (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        location VARCHAR(100),
        image VARCHAR(255)
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS menu_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        restaurant_id INT,
        name VARCHAR(100),
        price DECIMAL(10,2),
        image VARCHAR(255),
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS bookings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(100),
        items TEXT,
        total DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("SELECT COUNT(*) FROM restaurants")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO restaurants (name, location, image) VALUES (%s, %s, %s)", 
                       ("Pizza Palace", "Kolkata", "https://via.placeholder.com/300"))
        cursor.execute("INSERT INTO restaurants (name, location, image) VALUES (%s, %s, %s)", 
                       ("Burger Barn", "Delhi", "https://via.placeholder.com/300"))
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM menu_items")
    if cursor.fetchone()[0] == 0:
        items = [
            (1, "Margherita Pizza", 250.00, "https://drive.google.com/file/d/1ue9kN9y9C8PBn6TsCc3X2xe4mqPGmHCE/view?usp=drive_link"),
            (1, "Farmhouse Pizza", 300.00, "https://via.placeholder.com/300"),
            (2, "Classic Burger", 180.00, "https://via.placeholder.com/300"),
            (2, "Cheese Burst Burger", 220.00, "https://via.placeholder.com/300")
        ]
        cursor.executemany("INSERT INTO menu_items (restaurant_id, name, price, image) VALUES (%s, %s, %s, %s)", items)
        conn.commit()

    cursor.close()
    conn.close()

init_db()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        email = request.form['email']

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO users (name, address, email) VALUES (%s, %s, %s)", 
                       (name, address, email))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['email'] = email
            return redirect(url_for('home'))
        else:
            return "User not found. Please sign up first."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'email' not in session:
        return redirect(url_for('login'))

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM restaurants")
    restaurants = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('home.html', restaurants=restaurants)

@app.route('/restaurant/<int:restaurant_id>')
def restaurant(restaurant_id):
    if 'email' not in session:
        return redirect(url_for('login'))

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM restaurants WHERE id = %s", (restaurant_id,))
    restaurant = cursor.fetchone()
    cursor.execute("SELECT * FROM menu_items WHERE restaurant_id = %s", (restaurant_id,))
    menu_items = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('restaurant.html', restaurant=restaurant, menu=menu_items)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    item_id = request.form['item_id']
    name = request.form['name']
    price = float(request.form['price'])

    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append({'id': item_id, 'name': name, 'price': price})
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    if 'email' not in session:
        return redirect(url_for('login'))

    cart_items = session.get('cart', [])
    total = sum(item['price'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout')
def checkout():
    if 'email' not in session:
        return redirect(url_for('login'))

    cart_items = session.get('cart', [])
    total = sum(item['price'] for item in cart_items)
    email = session['email']

    if cart_items:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        items_str = ', '.join(item['name'] for item in cart_items)
        cursor.execute("INSERT INTO bookings (email, items, total) VALUES (%s, %s, %s)",
                       (email, items_str, total))
        conn.commit()
        cursor.close()
        conn.close()

    session.pop('cart', None)
    return render_template('order_success.html')

if __name__ == '__main__':
    app.run(debug=True)
