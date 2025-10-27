from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from functools import wraps
from sqlalchemy import func
import os
from flask_wtf.csrf import CSRFProtect
import json
from datetime import datetime, timezone
import secrets
import re

# =====================
# App Setup
# =====================


app = Flask(__name__)

# Generate a secure secret key for the session
app.secret_key = secrets.token_hex(16)
csrf = CSRFProtect(app)


# Database config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)



# A global dictionary for supported languages
SUPPORTED_LANGUAGES = {
    "bemba": "bemba.json",
    "nyanja": "nyanja.json",
    "tonga": "tonga.json",
    "lozi": "lozi.json",
    "kaonde": "kaonde.json",
    "luvale": "luvale.json",
    "lishi": "lishi.json"
}

# =====================
# Database Models
# =====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="user")
    contributions = db.relationship('Contribution', backref='contributor', lazy=True)

class Contribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    english = db.Column(db.String(500), nullable=False)
    translation = db.Column(db.String(500), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="pending")
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# =====================
# Decorators
# =====================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("You need to login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.get(session.get("user_id"))
        if not user or user.role != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

# =====================
# Routes
# =====================
@app.route("/")
def home():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return render_template("home.html", user=user)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form.get("email", "").strip()
        password = request.form["password"]

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for("register"))
        
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or Email already exists. Please choose a different one.", "error")
            return redirect(url_for("register"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(username=username, password=hashed_password, email=email)
        db.session.add(user)
        db.session.commit()
        
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('main'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/main", methods=["GET", "POST"])
@login_required
def main():
    user = User.query.get(session["user_id"])
    return render_template("main.html", user=user, languages=SUPPORTED_LANGUAGES)

@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        new_username = request.form["username"].strip()
        new_password = request.form.get("password")
        
        if not new_username:
            flash("Username cannot be empty.", "error")
            return redirect(url_for("edit_profile"))

        if new_username != user.username and User.query.filter_by(username=new_username).first():
            flash("This username is already taken.", "error")
            return redirect(url_for("edit_profile"))

        user.username = new_username
        if new_password:
            if len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "error")
                return redirect(url_for("edit_profile"))
            user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
        
        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("main"))
    return render_template("edit_profile.html", user=user)


SUPPORTED_LANGUAGES = {
    "bemba": "bemba.json",
    "nyanja": "nyanja.json",
    "tonga": "tonga.json",
    "lozi": "lozi.json",
    "kaonde": "kaonde.json",
    "luvale": "luvale.json",
    "lunda": "lunda.json",
    # ... add your other languages here
}
# Updated translate function to handle punctuation

@app.route("/translate", methods=["POST"])
@csrf.exempt
def translate():
    data = request.get_json() or {}
    english_text = data.get("text", "").strip()
    language = data.get("lang", "").strip().lower()

    if not english_text or not language:
        return jsonify({"translation": "Missing input."}), 400
    
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"translation": "Unsupported language."}), 400

    file_path = os.path.join("static", "dictionaries", SUPPORTED_LANGUAGES[language])
    data_dict = {}

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data_dict = json.load(f)
        except json.JSONDecodeError:
            return jsonify({
                "translation": None,
                "message": "Error loading dictionary file.",
                "suggestion": "The dictionary file may have a syntax error. Please check and fix it."
            }), 500

    # Split the sentence into words and clean punctuation
    words = re.findall(r"[\w'’]+", english_text.lower())
    original_words = english_text.split()
    
    translated_words = []
    untranslated_words = []
    
    for i, word in enumerate(words):
        translation = data_dict.get(word)
        if translation:
            translated_words.append(translation)
        else:
            # If a word is not found, get the original word from the sentence
            # and wrap it in a span with a special class.
            translated_words.append(f'<span class="untranslated">{original_words[i]}</span>')
            untranslated_words.append(original_words[i])
            
    translated_sentence = " ".join(translated_words)

    if not translated_sentence:
        return jsonify({
            "translation": None,
            "message": "No translation found",
            "suggestion": "If you know it, please add it in the contribution form below."
        })
    else:
        return jsonify({"translation": translated_sentence})
@app.route('/contribute', methods=['POST'])
@login_required
def contribute():
    data = request.get_json() or {}
    english = data.get('english', '').strip()
    translated = data.get('translation', '').strip()
    language = data.get('language', '').strip().lower()

    if not all([english, translated, language]):
        return jsonify({"message": "All fields are required."}), 400
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"message": "Unsupported language."}), 400
    
    user_id = session['user_id']
    new_contribution = Contribution(
        english=english,
        translation=translated,
        language=language,
        user_id=user_id,
        status="pending"
    )
    db.session.add(new_contribution)
    db.session.commit()

    return jsonify({"message": "Your contribution has been submitted for review."})

@app.route("/review_contributions")
@login_required
@admin_required
def review_contributions():
    # The 'review_contribution.html' template is the refactored version
    contributions = Contribution.query.filter_by(status="pending").order_by(Contribution.timestamp.desc()).all()
    return render_template("review_contribution.html", contributions=contributions)

@app.route("/approve_contribution/<int:id>", methods=["POST"])
@login_required
@admin_required
def approve_contribution(id):
    contribution = Contribution.query.get_or_404(id)
    file_path = os.path.join("static", "dictionaries", SUPPORTED_LANGUAGES[contribution.language])
    data_dict = {}
    
    # Load existing dictionary data, handling empty files
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data_dict = json.load(f)
            except json.JSONDecodeError:
                data_dict = {}
    
    # Add new translation to the dictionary
    data_dict[contribution.english] = contribution.translation
    
    # Write the updated dictionary back to the file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=2)
        
    contribution.status = "approved"
    db.session.commit()
    
    flash("Contribution approved and added to the dictionary!", "success")
    return redirect(url_for("review_contributions"))

@app.route("/reject_contribution/<int:id>", methods=["POST"])
@login_required
@admin_required
def reject_contribution(id):
    contribution = Contribution.query.get_or_404(id)
    contribution.status = "rejected"
    db.session.commit()
    
    flash("Contribution rejected.", "error")
    return redirect(url_for("review_contributions"))

@app.route("/admin_panel")
@login_required
@admin_required
def admin_panel():
    users = User.query.all()
    return render_template("admin_panel.html", users=users)

@app.route("/delete_user/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    if user.id == session.get("user_id"):
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin_panel"))
    
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' has been deleted.", "success")
    return redirect(url_for("admin_panel"))

@app.route("/toggle_admin/<int:id>", methods=["POST"])
@login_required
@admin_required
def toggle_admin(id):
    user = User.query.get_or_404(id)
    if user.id == session.get("user_id"):
        flash("You cannot change your own admin status.", "error")
        return redirect(url_for("admin_panel"))
    
    if user.role == "admin":
        user.role = "user"
        flash(f"'{user.username}' is no longer an admin.", "warning")
    else:
        user.role = "admin"
        flash(f"'{user.username}' has been made an admin.", "success")
    db.session.commit()
    return redirect(url_for("admin_panel"))

@app.route("/my_contributions")
@login_required
def my_contributions():
    user_id = session['user_id']
    contributions = Contribution.query.filter_by(user_id=user_id).order_by(Contribution.timestamp.desc()).all()
    return render_template("my_contributions.html", contributions=contributions)

@app.route("/leaderboard")
def leaderboard():
    top_contributors = db.session.query(
        User.username,
        func.count(Contribution.id).label('approved_contributions')
    ).join(Contribution).filter(Contribution.status == 'approved').group_by(User.id).order_by(func.count(Contribution.id).desc()).limit(10).all()
    
    return render_template("leaderboard.html", top_contributors=top_contributors)

@app.route("/profile/<username>")
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    approved_contributions_count = Contribution.query.filter_by(user_id=user.id, status="approved").count()
    return render_template("profile.html", user=user, approved_contributions_count=approved_contributions_count)

# =====================
# App Entry Point
# =====================
if __name__ == "__main__":
    with app.app_context():
        # This will create your database and tables if they don't exist
        db.create_all()
        
        # Optional: Add a default admin user if none exists
        if not User.query.filter_by(username='admin').first():
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin_user = User(username='admin', email='admin@example.com', password=hashed_password, role='admin')
            db.session.add(admin_user)
            db.session.commit()

    app.run(debug=True)