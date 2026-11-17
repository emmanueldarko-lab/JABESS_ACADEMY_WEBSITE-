import secrets, string
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from . import get_db
bp = Blueprint('main', __name__)

CLASSES = ['KG 1','KG 2'] + [f'Primary {i}' for i in range(1,7)] + [f'JHS {i}' for i in range(1,4)]
IMAGES = ['Jabess Academy School Assembly.png','students.jpg','kids.jpg','ai.jpg','ai 2.jpg','color hat.jpg','Gemini_Generated_Image_2rrqv32rrqv32rrq.jpg']

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapped(*a, **kw):
            if not session.get('user_id'): return redirect(url_for('main.student_login' if role=='student' else 'main.admin_login'))
            if role and session.get('role') != role: abort(403)
            return fn(*a, **kw)
        return wrapped
    return deco

@bp.context_processor
def common(): return {'school_name':'JABESS ACADEMY','classes':CLASSES,'images':IMAGES}

@bp.route('/')
def home():
    db=get_db(); news=db.execute('SELECT * FROM news WHERE published=1 ORDER BY created_at DESC LIMIT 3').fetchall()
    return render_template('home.html', news=news)
@bp.route('/about')
def about(): return render_template('about.html')
@bp.route('/academics')
def academics(): return render_template('academics.html')
@bp.route('/facilities')
def facilities(): return render_template('facilities.html')
@bp.route('/library')
def library(): return render_template('library.html', books=get_db().execute('SELECT * FROM books ORDER BY title').fetchall())
@bp.route('/admissions', methods=['GET','POST'])
def admissions():
    if request.method=='POST':
        f=request.form
        required=['student_name','dob','gender','class_applied','guardian_name','phone']
        if any(not f.get(k,'').strip() for k in required): flash('Please complete all required fields.','error'); return render_template('admissions.html')
        ref='JAB-'+''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(8))
        db=get_db(); db.execute('''INSERT INTO admissions(reference,student_name,dob,gender,nationality,address,previous_school,class_applied,academic_year,guardian_name,relationship,phone,alt_phone,email,emergency_name,emergency_phone,extra) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (ref,*[f.get(k,'').strip() for k in ['student_name','dob','gender','nationality','address','previous_school','class_applied','academic_year','guardian_name','relationship','phone','alt_phone','email','emergency_name','emergency_phone','extra']]))
        db.commit(); return render_template('admission_success.html', reference=ref)
    return render_template('admissions.html')
@bp.route('/news')
def news(): return render_template('news.html', news=get_db().execute('SELECT * FROM news WHERE published=1 ORDER BY created_at DESC').fetchall())
@bp.route('/contact', methods=['GET','POST'])
def contact():
    if request.method=='POST':
        f=request.form
        if not all(f.get(k,'').strip() for k in ['name','email','subject','message']): flash('Please complete the required fields.','error')
        else:
            db=get_db(); db.execute('INSERT INTO messages(name,email,phone,subject,message) VALUES(?,?,?,?,?)',(f['name'],f['email'],f.get('phone',''),f['subject'],f['message'])); db.commit(); flash('Your message has been sent to the school.','success'); return redirect(url_for('main.contact'))
    return render_template('contact.html')

@bp.route('/student-portal', methods=['GET','POST'])
def student_login():
    if request.method=='POST':
        name=request.form.get('full_name','').strip(); password=request.form.get('password','')
        user=get_db().execute("SELECT * FROM users WHERE role='student' AND lower(full_name)=lower(?) AND active=1",(name,)).fetchone()
        if user and check_password_hash(user['password_hash'],password):
            session.clear(); session.update(user_id=user['id'],full_name=user['full_name'],role=user['role'])
            if user['must_change_password']: return redirect(url_for('main.change_password'))
            return redirect(url_for('main.student_dashboard'))
        flash('The name or password is incorrect.','error')
    return render_template('student_login.html')
@bp.route('/change-password', methods=['GET','POST'])
@login_required()
def change_password():
    if request.method=='POST':
        p=request.form.get('password','')
        if len(p)<8: flash('Use at least 8 characters.','error')
        else:
            db=get_db(); db.execute('UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?',(generate_password_hash(p),session['user_id'])); db.commit(); flash('Password updated.','success'); return redirect(url_for('main.admin_dashboard' if session.get('role')=='admin' else 'main.student_dashboard'))
    return render_template('change_password.html')
@bp.route('/student/dashboard')
@login_required('student')
def student_dashboard(): return render_template('student_dashboard.html', news=get_db().execute('SELECT * FROM news WHERE published=1 ORDER BY created_at DESC LIMIT 5').fetchall())
@bp.route('/logout')
def logout(): session.clear(); flash('You have been signed out.','success'); return redirect(url_for('main.home'))

@bp.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        u=get_db().execute("SELECT * FROM users WHERE username=? AND role='admin' AND active=1",(request.form.get('username',''),)).fetchone()
        if u and check_password_hash(u['password_hash'],request.form.get('password','')):
            session.clear(); session.update(user_id=u['id'],full_name=u['full_name'],role='admin')
            if u['must_change_password']: return redirect(url_for('main.change_password'))
            return redirect(url_for('main.admin_dashboard'))
        flash('Invalid administrator credentials.','error')
    return render_template('admin_login.html')
@bp.route('/admin')
@login_required('admin')
def admin_dashboard():
    db=get_db()
    stat_queries = {
        'students': "SELECT COUNT(*) AS total FROM users WHERE role='student'",
        'applications': 'SELECT COUNT(*) AS total FROM admissions',
        'pending': "SELECT COUNT(*) AS total FROM admissions WHERE status IN ('Submitted','Under Review')",
        'news': 'SELECT COUNT(*) AS total FROM news',
        'books': 'SELECT COUNT(*) AS total FROM books',
        'messages': 'SELECT COUNT(*) AS total FROM messages WHERE read=0',
    }
    stats = {key: db.execute(query).fetchone()['total'] for key, query in stat_queries.items()}
    return render_template('admin_dashboard.html',stats=stats,applications=db.execute('SELECT * FROM admissions ORDER BY created_at DESC LIMIT 30').fetchall(),messages=db.execute('SELECT * FROM messages ORDER BY created_at DESC LIMIT 20').fetchall(),books=db.execute('SELECT * FROM books ORDER BY title').fetchall())
@bp.route('/admin/admission/<int:aid>', methods=['POST'])
@login_required('admin')
def update_admission(aid):
    status=request.form.get('status'); allowed=['Submitted','Under Review','Additional Information Required','Approved','Rejected']
    if status in allowed: db=get_db(); db.execute('UPDATE admissions SET status=? WHERE id=?',(status,aid)); db.commit()
    return redirect(url_for('main.admin_dashboard'))
@bp.route('/admin/news', methods=['POST'])
@login_required('admin')
def add_news():
    f=request.form
    if f.get('title') and f.get('body'):
        db=get_db(); db.execute('INSERT INTO news(title,category,body) VALUES(?,?,?)',(f['title'],f.get('category','Announcement'),f['body'])); db.commit(); flash('Announcement published.','success')
    return redirect(url_for('main.admin_dashboard'))
@bp.route('/admin/book', methods=['POST'])
@login_required('admin')
def add_book():
    f=request.form
    if f.get('title'):
        db=get_db(); db.execute('INSERT INTO books(title,author,category,reading_level) VALUES(?,?,?,?)',(f['title'],f.get('author',''),f.get('category','General'),f.get('reading_level','All levels'))); db.commit(); flash('Book added to catalogue.','success')
    return redirect(url_for('main.admin_dashboard'))
