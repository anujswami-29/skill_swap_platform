from flask import Flask, render_template, request, redirect, session
import os
from werkzeug.utils import secure_filename
from models import db, User, Skill, SwapRequest

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'skill_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# Upload folder configuration
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Database
db.init_app(app)

# -------------------- ROUTES --------------------

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        location = request.form.get('location')
        availability = request.form.get('availability')
        is_public = True if request.form.get('is_public') == 'on' else False

        profile_pic = request.files.get('profile_pic')
        filename = None
        if profile_pic and profile_pic.filename != '':
            filename = secure_filename(profile_pic.filename)
            profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        user = User(
            name=name,
            email=email,
            location=location,
            availability=availability,
            is_public=is_public,
            profile_pic=filename
        )
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

# Login
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

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('dashboard.html', user=user)
    return redirect('/login')

# Add Skill
@app.route('/add_skill', methods=['POST'])
def add_skill():
    if 'user_id' not in session:
        return redirect('/login')

    skill_name = request.form['skill_name']
    is_offered = True if request.form['is_offered'] == '1' else False

    new_skill = Skill(
        name=skill_name,
        is_offered=is_offered,
        user_id=session['user_id']
    )
    db.session.add(new_skill)
    db.session.commit()
    return redirect('/dashboard')

# Browse
@app.route('/browse', methods=['GET'])
def browse():
    if 'user_id' not in session:
        return redirect('/login')

    query = request.args.get('q')
    all_users = User.query.filter(User.id != session['user_id'], User.is_public == True).all()

    if query:
        filtered_users = []
        for user in all_users:
            matching_skills = [s for s in user.skills if s.is_offered and query.lower() in s.name.lower()]
            if matching_skills:
                user.filtered_skills = matching_skills
                filtered_users.append(user)
        users = filtered_users
    else:
        users = all_users
        for u in users:
            u.filtered_skills = [s for s in u.skills if s.is_offered]

    return render_template('browse.html', users=users, query=query)

# Request Swap
@app.route('/request_swap', methods=['POST'])
def request_swap():
    if 'user_id' not in session:
        return redirect('/login')

    receiver_id = request.form['receiver_id']
    skill_name = request.form['skill_name']

    new_request = SwapRequest(
        sender_id=session['user_id'],
        receiver_id=receiver_id,
        skill_name=skill_name,
        status='pending'
    )
    db.session.add(new_request)
    db.session.commit()

    return redirect('/browse')

# View Requests
@app.route('/requests')
def view_requests():
    if 'user_id' not in session:
        return redirect('/login')

    received_requests = SwapRequest.query.filter_by(receiver_id=session['user_id']).all()
    return render_template('requests.html', requests=received_requests)

# Update Request (Accept/Reject)
@app.route('/update_request/<int:id>', methods=['POST'])
def update_request(id):
    if 'user_id' not in session:
        return redirect('/login')

    swap_request = SwapRequest.query.get(id)

    if swap_request and swap_request.receiver_id == session['user_id']:
        action = request.form['action']
        if action == 'accept':
            swap_request.status = 'accepted'
        elif action == 'reject':
            swap_request.status = 'rejected'
        db.session.commit()

    return redirect('/requests')

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

# -------------------- MAIN --------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
