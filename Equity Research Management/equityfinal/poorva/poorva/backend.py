import requests
import yfinance as yf
import yfinance as yf
import matplotlib.pyplot as plt
from flask import send_file
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///equity.db'
db = SQLAlchemy(app)

# Your Alpha Vantage API key
ALPHA_VANTAGE_API_KEY = '5MG03OG397XQJ8OM'

# Function to get stock info from Alpha Vantage API
def get_stock_info(symbol):
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return None

def get_historical_prices(symbol):
    try:
        stock = yf.Ticker(symbol)
        historical_data = stock.history(period="max")
        return historical_data
    except Exception as e:
        print(f"Error fetching historical prices for {symbol}: {str(e)}")
        return None

# Route to generate and serve the equity performance chart
@app.route('/equity_performance_chart/<symbol>')
def equity_performance_chart(symbol):
    historical_data = get_historical_prices(symbol)
    if historical_data is not None:
        # Plotting the historical prices
        plt.figure(figsize=(10, 6))
        plt.plot(historical_data.index, historical_data['Close'], label='Close Price')
        plt.title(f'Historical Price for {symbol}')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        
        # Save the plot as a temporary image file
        chart_filename = 'equity_performance_chart.png'
        plt.savefig(chart_filename)
        plt.close()
        
        # Send the image file as a response
        return send_file(chart_filename, mimetype='image/png')
    else:
        return "Failed to fetch historical prices for the equity."

# Define User and Equity models...
def get_financial_metrics(symbol):
    try:
        stock = yf.Ticker(symbol)
        data = stock.info
        financial_metrics = {
            'PE_ratio': data['trailingPE'],
            'EPS': data['trailingEps'],
            'dividend_yield': data['dividendYield']
            # Add more financial metrics as needed
        }
        return financial_metrics
    except Exception as e:
        print(f"Error fetching financial metrics for {symbol}: {str(e)}")
        return None

# Modify the route to fetch equity details to include financial metrics
@app.route('/get_equity_details/<symbol>')
def get_equity_details(symbol):
    equity = Equity.query.filter_by(ticker=symbol, user_id=session['user_id']).first()
    if equity:
        financial_metrics = get_financial_metrics(symbol)
        if financial_metrics:
            return render_template('equity_details.html', equity=equity, financial_metrics=financial_metrics)
        else:
            return "Failed to fetch financial metrics for the equity."
    else:
        return "Equity not found."    

@app.route('/dashboard')
def user_dashboard():
    if 'user_id' in session:
        # Fetch equities for the logged-in user
        equities = Equity.query.filter_by(user_id=session['user_id']).all()
        
        # Calculate total market value of the portfolio
        total_market_value = sum(equity.market_cap * equity.price for equity in equities)
        
        return render_template('dashboard.html', equities=equities, total_market_value=total_market_value)
    
    return redirect(url_for('login'))

@app.route('/get_stock_info', methods=['POST'])
def get_stock_info_route():
    symbol = request.form['symbol']
    stock_info = get_stock_info(symbol)
    if stock_info:
        return render_template('stock_info.html', stock_info=stock_info)
    else:
        return "Failed to fetch stock information."

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Equity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ticker = db.Column(db.String(10), nullable=False)  # New column
    sector = db.Column(db.String(50), nullable=False)
    market_cap = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "Username already exists! Please choose another one."
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        equities = Equity.query.filter_by(user_id=session['user_id']).all()
        return render_template('dashboard.html', equities=equities)
    return redirect(url_for('login'))

@app.route('/add_equity', methods=['POST'])
def add_equity():
    if 'user_id' in session:
        name = request.form['name']
        ticker = request.form['ticker']
        sector = request.form['sector']
        market_cap = float(request.form['market_cap'])
        price = float(request.form['price'])
        new_equity = Equity(name=name, ticker=ticker, sector=sector, market_cap=market_cap, price=price, user_id=session['user_id'])
        db.session.add(new_equity)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/update_equity/<int:id>', methods=['POST'])
def update_equity(id):
    if 'user_id' in session:
        equity = Equity.query.get_or_404(id)
        if equity.user_id == session['user_id']:
            equity.name = request.form['name']
            equity.ticker = request.form['ticker']
            equity.sector = request.form['sector']
            equity.market_cap = float(request.form['market_cap'])
            equity.price = float(request.form['price'])
            db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_equity/<int:id>')
def delete_equity(id):
    if 'user_id' in session:
        equity = Equity.query.get_or_404(id)
        if equity.user_id == session['user_id']:
            db.session.delete(equity)
            db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

