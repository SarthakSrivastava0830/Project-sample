from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import jwt
from datetime import datetime, timedelta, timezone
import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = 'aywuit98723hsiddufhg'  # JWT Token

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ✅ User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    mobile = db.Column(db.String(10), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'farmer' or 'admin'

    def __init__(self, username, email, password, name, mobile, role):
        self.username = username
        self.email = email
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.name = name
        self.mobile = mobile
        self.role = role

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)


with app.app_context():
    db.create_all()

# Load the dataset
df = pd.read_csv()

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/home')
def home_page():
    return render_template("index.html")

@app.route('/about')
def about_page():
    return render_template("about.html")


# ✅ Signup Page Route
@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template("signup.html")


# ✅ Sign Up API
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    mobile = data.get('phone')
    role = data.get('role')

    if not all([username, email, password, name, mobile, role]):
        return jsonify({"error": "All fields are required"}), 400

    if role not in ["User", "admin"]:
        return jsonify({"error": "Invalid role"}), 400

    # ✅ Check if user already exists
    existing_user = User.query.filter(
        (User.email == email) | (User.username == username) | (User.mobile == mobile)
    ).first()
    
    if existing_user:
        return jsonify({"error": "User with this email, username, or mobile already exists"}), 400

    # ✅ Create new user
    new_user = User(username, email, password, name, mobile, role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


# ✅ Login Page Route
@app.route('/login', methods=['GET'])
def login_page():
    return render_template("login.html")


# ✅ Login API
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # ✅ Validate Inputs
    if not email or not password:
        return jsonify({"error": "Both email/mobile and password are required"}), 400

    # ✅ Fetch User from DB
    user = User.query.filter((User.email == email) | (User.mobile == email)).first()

    if user and user.check_password(password):
        # ✅ Generate JWT Token
        token_payload = {
            "user_id": user.id,
            "role": user.role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(token_payload, app.config["SECRET_KEY"], algorithm="HS256")

        return jsonify({"token": token, "role": user.role}), 200

    return jsonify({"error": "Invalid email, mobile, or password"}), 401


#Graphs function
def most_affected_crops():
    fig1 = go.Figure()
    top_crops = df['Crop'].value_counts().nlargest(10).reset_index()
    top_crops.columns = ['Crop', 'Count']

    fig1 = px.bar(
        top_crops,
        x='Crop',
        y='Count',
        title='🌾 Most Affected Crops by Grievances',
        labels={'Crop': 'Crop', 'Count': 'Number of Grievances'},
        color='Count',
        color_continuous_scale='YlGn'
    )
    graph1_html = pio.to_html(fig1, full_html=False)
    return graph1_html


#Analysis Pages

@app.route('/crop-analysis')
def crop_analysis():
    graph1 = most_affected_crops()
    return render_template("crop_analysis.html",graph1=graph1)


if __name__ == '__main__':
    app.run(debug=True)
