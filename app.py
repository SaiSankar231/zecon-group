from flask import Flask, request, jsonify, session, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY']             = os.getenv('SECRET_KEY', 'zecon-secret-123')
app.config['SQLALCHEMY_DATABASE_URI']= 'sqlite:///zecon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_USER = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASS = os.getenv('ADMIN_PASSWORD', 'zecon2025')

# ── MODELS ──────────────────────────────────────────────
class Appointment(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100))
    phone      = db.Column(db.String(30))
    email      = db.Column(db.String(120))
    project    = db.Column(db.String(100))
    date       = db.Column(db.String(30))
    message    = db.Column(db.Text)
    status     = db.Column(db.String(20), default='New')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Feedback(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100))
    email      = db.Column(db.String(120))
    rating     = db.Column(db.Integer)
    message    = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ── ADMIN HELPER ─────────────────────────────────────────
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated

# ── PUBLIC ROUTES ────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/appointment', methods=['POST'])
def book_appointment():
    d = request.get_json()
    required = ['name', 'phone', 'email', 'project', 'date']
    for f in required:
        if not d.get(f):
            return jsonify({'success': False, 'error': f'{f} is required'}), 400

    appt = Appointment(
        name   =d['name'],
        phone  =d['phone'],
        email  =d['email'],
        project=d['project'],
        date   =d['date'],
        message=d.get('message', '')
    )
    db.session.add(appt)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Appointment booked!'})

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    d = request.get_json()
    if not d.get('name') or not d.get('message'):
        return jsonify({'success': False, 'error': 'Name and message required'}), 400

    fb = Feedback(
        name   =d['name'],
        email  =d.get('email', ''),
        rating =int(d.get('rating', 5)),
        message=d['message']
    )
    db.session.add(fb)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Feedback submitted!'})

# ── ADMIN ────────────────────────────────────────────────
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['admin'] = True
            return redirect('/admin')
        error = 'Wrong username or password'
    return render_template('login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin/login')

@app.route('/admin')
@admin_required
def admin():
    appointments = Appointment.query.order_by(Appointment.created_at.desc()).all()
    feedbacks    = Feedback.query.order_by(Feedback.created_at.desc()).all()
    stats = {
        'total_appt' : Appointment.query.count(),
        'new_appt'   : Appointment.query.filter_by(status='New').count(),
        'total_fb'   : Feedback.query.count(),
        'avg_rating' : round(db.session.query(db.func.avg(Feedback.rating)).scalar() or 0, 1)
    }
    return render_template('admin.html', appointments=appointments, feedbacks=feedbacks, stats=stats)

@app.route('/admin/appointment/<int:id>/status', methods=['POST'])
@admin_required
def update_status(id):
    a = Appointment.query.get_or_404(id)
    a.status = request.form['status']
    db.session.commit()
    return redirect('/admin')

@app.route('/admin/appointment/<int:id>/delete', methods=['POST'])
@admin_required
def delete_appointment(id):
    db.session.delete(Appointment.query.get_or_404(id))
    db.session.commit()
    return redirect('/admin')

@app.route('/admin/feedback/<int:id>/delete', methods=['POST'])
@admin_required
def delete_feedback(id):
    db.session.delete(Feedback.query.get_or_404(id))
    db.session.commit()
    return redirect('/admin')

# ── RUN ──────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
