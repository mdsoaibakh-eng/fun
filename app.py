import os
from flask import Flask, render_template, redirect, url_for, flash, request, session
from dotenv import load_dotenv
from models import db, Event, Admin, Student, Registration
from markupsafe import Markup, escape
from werkzeug.utils import secure_filename
from datetime import datetime

load_dotenv()

# ===========================
# Admin Login Required
# ===========================
def admin_login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Please log in as admin.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# ===========================
# Student Login Required
# ===========================
def student_login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("student_id"):
            flash("Please log in as a student.", "error")
            return redirect(url_for("student_login"))
        return f(*args, **kwargs)
    return wrapper


# ===========================
# Create App
# ===========================
def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Create tables
    with app.app_context():
        db.create_all()

    # ================
    # Template filter
    # ================
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s is None:
            return ""
        return Markup("<br>".join(escape(s).splitlines()))

    # ===========================
    # ADMIN AUTHINCATION
    # ===========================

    @app.route("/admin/register", methods=["GET", "POST"])
    def admin_register():
        if request.method == "POST":
            username = request.form.get("username").strip()
            password = request.form.get("password").strip()

            if not username or not password:
                flash("Username and password required.", "error")
                return render_template("admin_register.html")

            if Admin.query.filter_by(username=username).first():
                flash("Username already taken.", "error")
                return render_template("admin_register.html")

            admin = Admin(username=username)
            admin.set_password(password)

            db.session.add(admin)
            db.session.commit()

            flash("Admin registered successfully.", "success")
            return redirect(url_for("admin_login"))

        return render_template("admin_register.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username").strip()
            password = request.form.get("password").strip()

            admin = Admin.query.filter_by(username=username).first()

            if not admin or not admin.check_password(password):
                flash("Invalid username or password.", "error")
                return render_template("admin_login.html")

            session.clear()
            session["admin_id"] = admin.id

            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))

        return render_template("admin_login.html")

    @app.route("/admin/logout")
    def logout():
        session.pop("admin_id", None)
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    # ###############################################################
    # STUDENT AUTHINCATION
    # ######################################################################

    @app.route("/student/register", methods=["GET", "POST"])
    def student_register():
        if request.method == "POST":
            username = request.form.get("username").strip()
            email = request.form.get("email").strip()
            password = request.form.get("password").strip()

            if not username or not email or not password:
                flash("All fields are required.", "error")
                return render_template("student_register.html")

            if Student.query.filter_by(username=username).first() or Student.query.filter_by(email=email).first():
                flash("Username or email already taken.", "error")
                return render_template("student_register.html")

            student = Student(username=username, email=email)
            student.set_password(password)
            db.session.add(student)
            db.session.commit()

            flash("Registered successfully. Please login.", "success")
            return redirect(url_for("student_login"))

        return render_template("student_register.html")

    @app.route("/student/login", methods=["GET", "POST"])
    def student_login():
        if request.method == "POST":
            username = request.form.get("username").strip()
            password = request.form.get("password").strip()

            student = Student.query.filter_by(username=username).first()

            if not student or not student.check_password(password):
                flash("Invalid username or password.", "error")
                return render_template("student_login.html")

            session.clear()
            session["student_id"] = student.id

            flash("Logged in successfully.", "success")
            return redirect(url_for("student_dashboard"))

        return render_template("student_login.html")

    @app.route("/student/logout")
    def student_logout():
        session.pop("student_id", None)
        flash("Logged out.", "info")
        return redirect(url_for("index"))


    # #####################################################
    # EVENT REGISTRATION
    # ########################################################

    @app.route("/student/register_event/<int:event_id>", methods=["POST"])
    @student_login_required
    def register_event(event_id):
        student = Student.query.get(session["student_id"])
        event = Event.query.get_or_404(event_id)

        # Check if already registered
        existing_reg = Registration.query.filter_by(student_id=student.id, event_id=event.id).first()
        if existing_reg:
            flash("You are already registered for this event.", "info")
            return redirect(url_for("detail", event_id=event.id))

        registration = Registration(student_id=student.id, event_id=event.id)
        db.session.add(registration)
        db.session.commit()

        flash("Registered for event successfully.", "success")
        return redirect(url_for("student_dashboard"))


    # ################################################
    # STUDENT DASHBOARD
    # ####################################################

    @app.route("/student/dashboard")
    @student_login_required
    def student_dashboard():
        student = Student.query.get(session["student_id"])
        registrations = student.registrations
        return render_template("student_dashboard.html", student=student, registrations=registrations)


    # ##########################################
    # Admin: View & Approve Registrations
    # ################################################

    @app.route("/admin/registrations")
    @admin_login_required
    def admin_view_registrations():
        registrations = Registration.query.order_by(Registration.created_at.desc()).all()
        return render_template("admin_registrations.html", registrations=registrations)

    @app.route("/admin/registrations/approve/<int:reg_id>", methods=["POST"])
    @admin_login_required
    def approve_registration(reg_id):
        reg_record = Registration.query.get_or_404(reg_id)
        reg_record.status = "Approved"
        reg_record.approved_at = datetime.utcnow()
        db.session.commit()

        flash("Registration approved.", "success")
        return redirect(url_for("admin_view_registrations"))


    # ##########################################
    # PUBLIC EVENT VIEWS
    # ################################################

    @app.route("/")
    def index():
        page = request.args.get("page", 1, type=int)
        per_page = 6
        events = Event.query.order_by(Event.date.asc()).paginate(page=page, per_page=per_page, error_out=False)
        return render_template("list.html", events=events)

    @app.route("/event/<int:event_id>")
    def detail(event_id):
        event = Event.query.get_or_404(event_id)
        is_registered = False
        if session.get("student_id"):
            student_id = session.get("student_id")
            if Registration.query.filter_by(student_id=student_id, event_id=event.id).first():
                is_registered = True
        
        return render_template("detail.html", event=event, is_registered=is_registered)


    # #######################################
    # ADMIN CRUD (EVENTS)
    # ############################################

    @app.route("/create", methods=["GET", "POST"])
    @admin_login_required
    def create():
        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            description = (request.form.get("description") or "").strip() or None
            location = (request.form.get("location") or "").strip()
            date_str = request.form.get("date")

            if not title or not location or not date_str:
                flash("Title, Location and Date are required.", "error")
                return render_template("create.html", title=title, description=description, location=location, date=date_str)

            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid date format.", "error")
                return render_template("create.html", title=title, description=description, location=location, date=date_str)

            event = Event(title=title, description=description, location=location, date=event_date)
            db.session.add(event)
            db.session.commit()

            flash("Event created successfully.", "success")
            return redirect(url_for("index"))

        return render_template("create.html", title="", description="", location="", date="")

    @app.route("/edit/<int:event_id>", methods=["GET", "POST"])
    @admin_login_required
    def edit(event_id):
        event = Event.query.get_or_404(event_id)

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            description = (request.form.get("description") or "").strip() or None
            location = (request.form.get("location") or "").strip()
            date_str = request.form.get("date")

            if not title or not location or not date_str:
                flash("Title, Location and Date are required.", "error")
                return render_template("edit.html", event=event)

            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid date format.", "error")
                return render_template("edit.html", event=event)

            event.title = title
            event.description = description
            event.location = location
            event.date = event_date

            db.session.commit()

            flash("Event updated.", "success")
            return redirect(url_for("detail", event_id=event.id))

        return render_template("edit.html", event=event)

    @app.route("/delete/<int:event_id>", methods=["POST"])
    @admin_login_required
    def delete(event_id):
        event = Event.query.get_or_404(event_id)
        db.session.delete(event)
        db.session.commit()
        flash("Event deleted.", "info")
        return redirect(url_for("index"))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app

if __name__ == "__main__":
    create_app().run(debug=True)
