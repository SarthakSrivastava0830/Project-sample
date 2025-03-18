from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    mobile = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username
    
    def __init__(self, username, email, password, name, mobile):
        self.username = username
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        self.name = name
        self.mobile = mobile
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password.encode('utf-8'), password.encode('utf-8'))

with app.app_context():
    db.create_all()


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        mobile = request.form['phone']
        try:
            user = User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first()
            if user:
                return render_template("signup.html", error="user already exist")
        except:
            pass
        aadmi = User(username=username, email=email, password=password, name=name, mobile=mobile)
        db.session.add(aadmi)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template("signup.html")

 
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email_or_mobile = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(mobile=email_or_mobile).first() or User.query.filter_by(email=email_or_mobile).first()
        if user and user.check_password(password):
            return redirect(url_for('dashboard'))
        else:
            return render_template("login.html", error="invalid user")
    return render_template("login.html")







@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)