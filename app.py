from datetime import datetime, timezone
from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy import func
import requests
import re
from werkzeug.utils import secure_filename
from sklearn.preprocessing import StandardScaler
import numpy as np
from datetime import timedelta




app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SECRET_KEY"] = "root"
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)

class Cash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(250))
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))  # Automatically set date on creation
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('Users', backref=db.backref('cash_entries', lazy=True))

class Expenses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now(timezone.utc))  # Use timezone-aware UTC
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('Users', backref=db.backref('expenses', lazy=True))
with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, int(user_id))

@app.route("/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        user = Users.query.filter_by(username=request.form.get("username")).first()
        if user and user.password == request.form.get("password"):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        # Check if username already exists
        if Users.query.filter_by(username=username).first():
            flash("Username already exists. Please choose a different one.")
            return redirect(url_for("register"))

        # Create new user
        new_user = Users(username=username, password=password)  # Note: Consider hashing passwords!
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route('/addcash', methods=['GET', 'POST'])
@login_required
def add_cash():
    if request.method == 'POST':
        amount = request.form.get("amount")
        reason = request.form.get("reason")
        if amount and amount.replace('.', '', 1).isdigit():
            new_cash_entry = Cash(amount=float(amount), reason=reason, user_id=current_user.id)
            db.session.add(new_cash_entry)
            db.session.commit()
            return redirect(url_for("add_cash"))

    # Retrieve all cash entries for the current user
    cash_entries = Cash.query.filter_by(user_id=current_user.id).all()
    return render_template('addcash.html', cash_entries=cash_entries, username=current_user.username)


@app.route("/dashboard")
@login_required
def dashboard():
    # Calculate total cash added by the user
    total_balance = db.session.query(func.sum(Cash.amount)).filter_by(user_id=current_user.id).scalar() or 0
    total_expenses = db.session.query(func.sum(Expenses.amount)).filter_by(user_id=current_user.id).scalar() or 0
    remaining_balance = total_balance - total_expenses

    # Group expenses by category and calculate the total amount per category
    expenses_summary = db.session.query(
        Expenses.category,
        func.sum(Expenses.amount).label('total_amount')
    ).filter_by(user_id=current_user.id).group_by(Expenses.category).all()
    
    # Add monthly data aggregation
    monthly_expenses = db.session.query(
        func.strftime('%Y-%m', Expenses.date).label('month'),
        func.sum(Expenses.amount).label('total')
    ).filter_by(user_id=current_user.id
    ).group_by('month').order_by('month').all()
    
    return render_template("dashboard.html", 
                         total_balance=remaining_balance, 
                         expenses_summary=expenses_summary,
                         monthly_expenses=monthly_expenses,
                         username=current_user.username)

@app.route("/addexpense", methods=["POST"])
@login_required
def add_expense():
    if request.method == "POST":
        category = request.form.get("category")
        amount = request.form.get("amount")
        
        # Check if amount is valid
        if not amount or not amount.replace('.', '', 1).isdigit():
            flash("Please enter a valid amount.")
            return redirect(url_for("track_expenses"))
        
        amount = float(amount)
        
        # Calculate remaining balance
        total_balance = db.session.query(func.sum(Cash.amount)).filter_by(user_id=current_user.id).scalar() or 0
        total_expenses = db.session.query(func.sum(Expenses.amount)).filter_by(user_id=current_user.id).scalar() or 0
        remaining_balance = total_balance - total_expenses
        
        # Check if adding this expense will exceed available balance
        if amount > remaining_balance:
            flash("Insufficient balance. Please enter a smaller amount.")
            return redirect(url_for("track_expenses"),username=current_user.username)
        
        # If balance is sufficient, proceed with adding the expense
        new_expense = Expenses(category=category, amount=amount, user_id=current_user.id)
        db.session.add(new_expense)
        db.session.commit()
        return redirect(url_for("track_expenses"))


@app.route('/trackexpenses', methods=['GET'])
@login_required
def track_expenses():
    expenses = Expenses.query.filter_by(user_id=current_user.id).all()
    return render_template('trackexpenses.html', expenses=expenses,username=current_user.username)  # Ensure 'trackexpenses.html' is the correct template name

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# Replace the imports at the top
import PyPDF2
import re

# Add these imports at the top
import requests
import json

# Add the analyze_receipt function
# Update these constants
GEMINI_API_KEY = "AIzaSyArSNs1ocJD28MmgZFQRv0-8wZLpHM25EU"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
from checkFile import analyze_receipt

@app.route('/upload_receipt', methods=['GET', 'POST'])
@login_required
def upload_receipt():
    error = None
    success = None
    valid_categories = ['Shopping', 'Medical', 'Food', 'Rent', 'Others']
    
    if request.method == 'POST':
        if 'receipt' not in request.files:
            error = "No file part."
            return render_template('upload_receipt.html', error=error, username=current_user.username)
        
        file = request.files['receipt']
        if file.filename == '':
            error = "No selected file."
            return render_template('upload_receipt.html', error=error, username=current_user.username)
        
        if not file.filename.lower().endswith('.pdf'):
            error = "Please upload a PDF file only."
            return render_template('upload_receipt.html', error=error, username=current_user.username)
        
        if file:
            try:
                # Read PDF content
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                print(text)
                # Use the analyze_receipt function from checkFile.py
                response_text = analyze_receipt(text)
                if response_text is None:
                    raise Exception("Receipt analysis failed")

                # Parse the response text and ensure it's valid JSON
                try:
                    if isinstance(response_text, str):
                        analysis = json.loads(response_text)
                    else:
                        analysis = response_text
                    
                    # Validate category and set to 'Other' if invalid
                    if analysis['category'] not in valid_categories:
                        analysis['category'] = 'Other'

                    # Add expense to DB
                    new_expense = Expenses(
                        category=analysis['category'],
                        amount=float(analysis['amount']),
                        user_id=current_user.id
                    )
                    db.session.add(new_expense)
                    db.session.commit()
                    
                    success = f"Successfully added expense of ₹{analysis['amount']:.2f} under '{analysis['category']}'\nDescription: {analysis['description']}"
                    
                    # Add AI analysis
                    analyzer = ExpenseAnalyzer()
                    recent_expenses = Expenses.query.filter_by(user_id=current_user.id)\
                        .filter(Expenses.date >= datetime.now() - timedelta(days=30)).all()
                    
                    insights = analyzer.analyze_spending_patterns(recent_expenses, float(analysis['amount']))
                    if insights and insights['recommendations']:
                        success += "\n\nAI Insights:\n" + "\n".join(insights['recommendations'])
                
                except json.JSONDecodeError as je:
                    raise Exception(f"Invalid JSON format: {str(je)}")
                except KeyError as ke:
                    raise Exception(f"Missing required field: {str(ke)}")
                except ValueError as ve:
                    raise Exception(f"Invalid value in response: {str(ve)}")
            
            except Exception as e:
                error = f"Error processing receipt: {str(e)}"
                
    return render_template('upload_receipt.html', error=error, success=success, username=current_user.username)

# Keep only this logout route



# Add these imports at the top
from sklearn.preprocessing import StandardScaler
import numpy as np
from datetime import timedelta

# Add this new class for AI recommendations
class ExpenseAnalyzer:
    def __init__(self):
        self.scaler = StandardScaler()
    
    def analyze_spending_patterns(self, expenses, cash_flow):
        if not expenses:
            return None
        
        # Calculate basic metrics
        total_spent = sum(exp.amount for exp in expenses)
        category_totals = {}
        for expense in expenses:
            category_totals[expense.category] = category_totals.get(expense.category, 0) + expense.amount
        
        # Identify unusual spending
        avg_daily_spend = total_spent / 30  # Assuming monthly analysis
        
        recommendations = []
        
        # Analyze spending patterns
        if len(category_totals) > 0:
            highest_category = max(category_totals.items(), key=lambda x: x[1])
            if highest_category[1] > total_spent * 0.4:  # If one category takes >40% of expenses
                recommendations.append(f"Consider reducing spending on {highest_category[0]}. "
                                    f"It accounts for {(highest_category[1]/total_spent*100):.1f}% of your expenses.")
        
        # Cash flow analysis
        if cash_flow < total_spent * 0.2:  # If savings are less than 20% of spending
            recommendations.append("Your savings rate is low. Consider setting aside at least 20% of your income.")
        
        # Budget recommendations
        recommended_budget = {
            'Essential': 0.5,  # 50% for essential expenses
            'Savings': 0.3,   # 30% for savings
            'Discretionary': 0.2  # 20% for discretionary spending
        }
        
        return {
            'recommendations': recommendations,
            'budget_allocation': recommended_budget,
            'spending_insights': category_totals,
            'monthly_forecast': total_spent * 1.1  # Estimated next month's expenses
        }

# Add this new route for AI recommendations
@app.route("/ai_insights")
@login_required
def ai_insights():
    # Get all expenses for the current user
    expenses = Expenses.query.filter_by(user_id=current_user.id).all()
    
    # Calculate total spending and category-wise spending
    total_spent = sum(expense.amount for expense in expenses)
    category_totals = {}
    for expense in expenses:
        if expense.category in category_totals:
            category_totals[expense.category] = category_totals[expense.category] + expense.amount
        else:
            category_totals[expense.category] = expense.amount

    # Calculate savings rate and projected savings
    total_income = db.session.query(func.sum(Cash.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    savings_rate = ((total_income - total_spent) / total_income * 100) if total_income > 0 else 0
    projected_savings = (total_income * 0.2) * 3  # 20% savings over 3 months

    # Determine spending trend
    trend_direction = "Stable"
    if len(expenses) >= 2:
        recent_expenses = sorted(expenses, key=lambda x: x.date, reverse=True)[:2]
        if recent_expenses[0].amount > recent_expenses[1].amount:
            trend_direction = "Increasing"
        elif recent_expenses[0].amount < recent_expenses[1].amount:
            trend_direction = "Decreasing"

    # Calculate improvement potential
    improvement_potential = total_spent * 0.15  # Assuming 15% potential improvement

    # Prepare insights dictionary with all required fields
    insights = {
        'spending_insights': {
            'total_spent': total_spent,
            'category_totals': category_totals
        },
        'savings_rate': savings_rate,
        'trend_direction': trend_direction,
        'projected_savings': projected_savings,
        'improvement_potential': improvement_potential,
        'spending_analysis': f"Your monthly spending is ₹{total_spent:.2f}",
        'budget_analysis': "Based on the 50/30/20 rule:",
        'future_projection': f"If you maintain a 20% savings rate, you could save ₹{projected_savings:.2f} in 3 months.",
        'spending_points': [
            f"Your highest expense category is {max(category_totals.items(), key=lambda x: x[1])[0] if category_totals else 'None'}",
            f"Your current savings rate is {savings_rate:.1f}%",
            f"Your spending trend is {trend_direction.lower()}"
        ],
        'category_analysis': [
            {'name': cat, 'percentage': (amt/total_spent*100 if total_spent > 0 else 0), 'status': 'Normal'}
            for cat, amt in category_totals.items()
        ],
        'action_items': [
            {
                'priority': 'high',
                'title': 'Optimize Highest Expense',
                'description': f"Focus on reducing spending in your highest category",
                'impact': 5
            },
            {
                'priority': 'medium',
                'title': 'Build Emergency Fund',
                'description': "Aim to save 3-6 months of expenses",
                'impact': 4
            },
            {
                'priority': 'low',
                'title': 'Track Daily Expenses',
                'description': "Record all expenses to identify saving opportunities",
                'impact': 3
            }
        ],
        'recommendations': [
            {
                'icon': 'fa-chart-pie',
                'title': 'Category Analysis',
                'description': f'Your highest spending category is {max(category_totals.items(), key=lambda x: x[1])[0] if category_totals else "None"}.',
                'saving_potential': total_spent * 0.1
            },
            {
                'icon': 'fa-piggy-bank',
                'title': 'Savings Opportunity',
                'description': 'Try to save 20% of your income each month.',
                'saving_potential': total_income * 0.2 if total_income > 0 else 0
            },
            {
                'icon': 'fa-balance-scale',
                'title': 'Budget Balance',
                'description': 'Consider using the 50/30/20 rule for budgeting.',
                'saving_potential': None
            }
        ],
        'metrics': {
            'savings_score': min(int(savings_rate), 100),
            'spending_score': 70,
            'budget_score': 80
        },
        'health_score': min(int((savings_rate + 70 + 80) / 3), 100)
    }

    return render_template(
        "ai_insights.html",
        insights=insights,
        username=current_user.username
    )
if __name__ == "__main__":
    app.run(port=8000)

