from flask import Flask, render_template, request, redirect, session
from models import db, User  # Import db & User from models.py

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'skill_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# Initialize Database with App
db.init_app(app)

# -------------------- ROUTES --------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        
        user = User(name=name, email=email)
        db.session.add(user)
        db.session.commit()
        
        return redirect('/')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            session['user_id'] = user.id
            return redirect('/dashboard')
        else:
            return "User not found"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('dashboard.html', user=user)
    else:
        return redirect('/login')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

# -------------------- MAIN --------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
