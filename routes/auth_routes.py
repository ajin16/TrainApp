from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '').strip()
        
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['role'] = user.role
            
            flash(f"Welcome back, {user.full_name}!", "success")
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.index'))
        else:
            flash("Invalid username/email or password.", "danger")
            
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not username or not email or not password or not full_name:
            flash("Please fill in all required fields.", "warning")
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/register.html')
            
        if User.query.filter_by(username=username).first():
            flash("Username already taken. Please choose another.", "danger")
            return render_template('auth/register.html')
            
        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "danger")
            return render_template('auth/register.html')
            
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            phone=phone,
            role='user'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash("Registration successful! Please login to continue.", "success")
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('user.index'))
