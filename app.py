from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODELS ---

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False) # Product Code (e.g., 123ab)
    name = db.Column(db.String(100), nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    sell_price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100))
    product_code = db.Column(db.String(50))
    quantity = db.Column(db.Integer)
    total_amount = db.Column(db.Float)
    profit = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.now)

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.now)

with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route('/')
def dashboard():
    # Calculation Logic
    investments = Investment.query.all()
    total_invest = sum(i.amount for i in investments)
    
    sales = Transaction.query.all()
    total_sales = sum(s.total_amount for s in sales)
    total_profit = sum(s.profit for s in sales)
    
    products = Product.query.all()
    current_stock_value = sum(p.buy_price * p.stock for p in products)
    
    # Recent 5 transactions
    recent_sales = Transaction.query.order_by(Transaction.date.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                           invest=total_invest, 
                           sales=total_sales, 
                           profit=total_profit, 
                           stock_value=current_stock_value,
                           transactions=recent_sales)

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        buy_price = float(request.form['buy_price'])
        sell_price = float(request.form['sell_price'])
        stock = int(request.form['stock'])
        
        # Check if code already exists
        existing = Product.query.filter_by(code=code).first()
        if existing:
            return render_template('inventory.html', error="Code already exists!", products=Product.query.all())

        new_prod = Product(code=code, name=name, buy_price=buy_price, sell_price=sell_price, stock=stock)
        db.session.add(new_prod)
        
        # Add to investment history automatically
        invest_note = f"Stock: {name} ({stock} pcs)"
        new_invest = Investment(amount=buy_price*stock, note=invest_note)
        db.session.add(new_invest)
        
        db.session.commit()
        return redirect(url_for('inventory'))
        
    products = Product.query.all()
    return render_template('inventory.html', products=products)

# --- API FOR SEARCHING PRODUCT BY CODE ---
@app.route('/get_product/<code>')
def get_product(code):
    product = Product.query.filter_by(code=code).first()
    if product:
        return jsonify({
            'success': True,
            'name': product.name,
            'price': product.sell_price,
            'stock': product.stock,
            'buy_price': product.buy_price,
            'id': product.id
        })
    return jsonify({'success': False})

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if request.method == 'POST':
        code = request.form['code']
        qty = int(request.form['quantity'])
        
        product = Product.query.filter_by(code=code).first()
        
        if product and product.stock >= qty:
            total_sell = product.sell_price * qty
            total_cost = product.buy_price * qty
            profit = total_sell - total_cost
            
            # Record Transaction
            new_sale = Transaction(product_name=product.name, product_code=product.code, 
                                   quantity=qty, total_amount=total_sell, profit=profit)
            
            # Decrease Stock
            product.stock -= qty
            
            db.session.add(new_sale)
            db.session.commit()
            return redirect(url_for('sell', status='success'))
        else:
            return redirect(url_for('sell', status='error'))

    return render_template('sell.html')

@app.route('/report')
def report():
    sales = Transaction.query.order_by(Transaction.date.desc()).all()
    return render_template('base.html', content_type='report', sales=sales)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
