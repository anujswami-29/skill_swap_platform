from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)

    # New fields
    location = db.Column(db.String(100))
    availability = db.Column(db.String(100))
    is_public = db.Column(db.Boolean, default=True)
    profile_pic = db.Column(db.String(200))  # filename of uploaded image

    skills = db.relationship('Skill', backref='user', lazy=True)
    feedback_received = db.relationship('Feedback', foreign_keys='Feedback.receiver_id', backref='receiver', lazy=True)

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    is_offered = db.Column(db.Boolean)  # True = offered, False = wanted
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class SwapRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    skill_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer)  # 1 to 5
    comment = db.Column(db.Text)
    swap_id = db.Column(db.Integer, db.ForeignKey('swap_request.id'))
