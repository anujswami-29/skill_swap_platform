from flask import Flask, render_template, request, redirect, session, send_file
import os
import csv
import io
from werkzeug.utils import secure_filename
from models import db, User, Skill, SwapRequest, Feedback

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

@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            session['user_id'] = user.id
            session['user_email'] = user.email
            return redirect('/dashboard')
        else:
            return "User not found"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('dashboard.html', user=user)
    return redirect('/login')

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

@app.route('/requests')
def view_requests():
    if 'user_id' not in session:
        return redirect('/login')

    received_requests = SwapRequest.query.filter_by(receiver_id=session['user_id']).all()
    return render_template('requests.html', requests=received_requests)

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

@app.route('/feedback/<int:swap_id>', methods=['GET', 'POST'])
def give_feedback(swap_id):
    if 'user_id' not in session:
        return redirect('/login')

    swap = SwapRequest.query.get(swap_id)
    if not swap or swap.status != 'accepted' or swap.receiver_id != session['user_id']:
        return "Invalid or unauthorized feedback request"

    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form['comment']

        feedback = Feedback(
            sender_id=session['user_id'],
            receiver_id=swap.sender_id,
            rating=rating,
            comment=comment,
            swap_id=swap_id
        )
        db.session.add(feedback)
        db.session.commit()
        return redirect('/dashboard')

    return render_template('give_feedback.html')

@app.route('/my_requests')
def my_requests():
    if 'user_id' not in session:
        return redirect('/login')

    sent_requests = SwapRequest.query.filter_by(sender_id=session['user_id']).all()
    return render_template('my_requests.html', requests=sent_requests)

@app.route('/delete_request/<int:id>', methods=['POST'])
def delete_request(id):
    if 'user_id' not in session:
        return redirect('/login')

    swap_request = SwapRequest.query.get(id)
    if swap_request and swap_request.sender_id == session['user_id'] and swap_request.status == 'pending':
        db.session.delete(swap_request)
        db.session.commit()

    return redirect('/my_requests')

# ---------------- ADMIN PANEL ----------------

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    if user.email != 'admin@example.com':
        return "Access Denied"

    users = User.query.all()
    skills = Skill.query.all()
    swaps = SwapRequest.query.all()
    feedbacks = Feedback.query.all()
    message = session.get('broadcast_message')
    return render_template('admin.html', users=users, skills=skills, swaps=swaps, feedbacks=feedbacks, message=message)

@app.route('/ban_user/<int:id>', methods=['POST'])
def ban_user(id):
    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect('/admin')

@app.route('/delete_skill/<int:id>', methods=['POST'])
def delete_skill(id):
    skill = Skill.query.get(id)
    if skill:
        db.session.delete(skill)
        db.session.commit()
    return redirect('/admin')

@app.route('/broadcast', methods=['POST'])
def broadcast():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    if user.email != 'admin@example.com':
        return "Access Denied"

    message = request.form['message']
    session['broadcast_message'] = message
    return redirect('/admin')

@app.route('/export/<string:data_type>')
def export_data(data_type):
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    if user.email != 'admin@example.com':
        return "Access Denied"

    proxy = io.StringIO()
    writer = csv.writer(proxy)

    if data_type == 'users':
        writer.writerow(['ID', 'Name', 'Email', 'Location', 'Availability'])
        for u in User.query.all():
            writer.writerow([u.id, u.name, u.email, u.location, u.availability])
    elif data_type == 'swaps':
        writer.writerow(['ID', 'Sender ID', 'Receiver ID', 'Skill Name', 'Status'])
        for s in SwapRequest.query.all():
            writer.writerow([s.id, s.sender_id, s.receiver_id, s.skill_name, s.status])
    elif data_type == 'feedback':
        writer.writerow(['ID', 'Sender ID', 'Receiver ID', 'Rating', 'Comment'])
        for f in Feedback.query.all():
            writer.writerow([f.id, f.sender_id, f.receiver_id, f.rating, f.comment])
    else:
        return "Invalid export type"

    mem = io.BytesIO()
    mem.write(proxy.getvalue().encode('utf-8'))
    mem.seek(0)
    proxy.close()

    return send_file(mem, as_attachment=True, download_name=f"{data_type}_report.csv", mimetype='text/csv')

# -------------------- LOGOUT --------------------

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    return redirect('/')

# -------------------- MAIN --------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
