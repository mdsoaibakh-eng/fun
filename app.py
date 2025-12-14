import os
from flask import Flask, render_template, redirect, url_for, flash, request, session
from dotenv import load_dotenv
from models import db, Event, Admin, Student, Registration, Coordinator, Notification, Category
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
# Coordinator Login Required
# ===========================
def coordinator_login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("coordinator_id"):
            flash("Please log in as a coordinator.", "error")
            return redirect(url_for("coordinator_login"))
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
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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


    # ###############################################################
    # COORDINATOR AUTHENTICATION & DASHBOARD
    # ######################################################################

    @app.route("/coordinator/login", methods=["GET", "POST"])
    def coordinator_login():
        if request.method == "POST":
            username = request.form.get("username").strip()
            password = request.form.get("password").strip()

            coordinator = Coordinator.query.filter_by(username=username).first()

            if not coordinator or not coordinator.check_password(password):
                flash("Invalid username or password.", "error")
                return render_template("coordinator_login.html")

            session.clear()
            session["coordinator_id"] = coordinator.id

            flash("Logged in successfully.", "success")
            return redirect(url_for("coordinator_dashboard"))

        return render_template("coordinator_login.html")

    @app.route("/coordinator/logout")
    def coordinator_logout():
        session.pop("coordinator_id", None)
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    @app.route("/coordinator/dashboard")
    @coordinator_login_required
    def coordinator_dashboard():
        coordinator = Coordinator.query.get(session["coordinator_id"])
        events = coordinator.events
        return render_template("coordinator_dashboard.html", coordinator=coordinator, events=events)

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

    @app.route("/coordinator/create_event", methods=["GET", "POST"])
    @coordinator_login_required
    def coordinator_create_event():
        categories = Category.query.all()
        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            category_id = request.form.get("category_id")
            description = (request.form.get("description") or "").strip() or None
            venue = (request.form.get("venue") or "").strip()
            date_str = request.form.get("date")
            
            # File Upload
            image_file = 'default.jpg'
            if 'image_file' in request.files:
                file = request.files['image_file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_file = filename

            if not title or not venue or not date_str or not category_id:
                flash("Title, Category, Venue and Date are required.", "error")
                return render_template("create.html", title=title, description=description, venue=venue, date=date_str, categories=categories, is_coordinator=True)

            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid date format.", "error")
                return render_template("create.html", title=title, description=description, venue=venue, date=date_str, categories=categories, is_coordinator=True)

            coordinator_id = session["coordinator_id"]
            event = Event(title=title, category_id=category_id, description=description, venue=venue, date=event_date, coordinator_id=coordinator_id, status='Proposed', image_file=image_file)
            db.session.add(event)
            db.session.commit()

            flash("Event proposed successfully. Waiting for admin approval.", "success")
            return redirect(url_for("coordinator_dashboard"))

        return render_template("create.html", title="", description="", venue="", date="", categories=categories, is_coordinator=True)

    @app.route("/coordinator/edit_event/<int:event_id>", methods=["GET", "POST"])
    @coordinator_login_required
    def coordinator_edit_event(event_id):
        event = Event.query.get_or_404(event_id)
        categories = Category.query.all()
        
        if event.coordinator_id != session["coordinator_id"]:
            flash("Unauthorized access.", "error")
            return redirect(url_for("coordinator_dashboard"))

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            category_id = request.form.get("category_id")
            description = (request.form.get("description") or "").strip() or None
            venue = (request.form.get("venue") or "").strip()
            date_str = request.form.get("date")
            announcements = (request.form.get("announcements") or "").strip() or None
            results = (request.form.get("results") or "").strip() or None
            
            if 'image_file' in request.files:
                file = request.files['image_file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    event.image_file = filename

            if not title or not venue or not date_str or not category_id:
                flash("Title, Category, Venue and Date are required.", "error")
                return render_template("edit.html", event=event, categories=categories, is_coordinator=True)

            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid date format.", "error")
                return render_template("edit.html", event=event, categories=categories, is_coordinator=True)

            event.title = title
            event.category_id = category_id
            event.description = description
            event.venue = venue
            event.date = event_date
            event.announcements = announcements
            event.results = results

            db.session.commit()

            flash("Event updated.", "success")
            return redirect(url_for("coordinator_dashboard"))

        return render_template("edit.html", event=event, categories=categories, is_coordinator=True)

    @app.route("/coordinator/event/<int:event_id>/export")
    @coordinator_login_required
    def coordinator_export_participants(event_id):
        event = Event.query.get_or_404(event_id)
        if event.coordinator_id != session["coordinator_id"]:
            flash("Unauthorized access.", "error")
            return redirect(url_for("coordinator_dashboard"))
            
        registrations = Registration.query.filter_by(event_id=event.id).all()
        
        # Generate CSV
        import csv
        from io import StringIO
        from flask import make_response
        
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['Student Username', 'Email', 'Registration Date', 'Status'])
        for reg in registrations:
            cw.writerow([reg.student.username, reg.student.email, reg.created_at.strftime('%Y-%m-%d %H:%M'), reg.status])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=participants_{event.id}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    @app.route("/coordinator/event/<int:event_id>/participants")
    @coordinator_login_required
    def coordinator_event_participants(event_id):
        event = Event.query.get_or_404(event_id)
        if event.coordinator_id != session["coordinator_id"]:
            flash("Unauthorized access.", "error")
            return redirect(url_for("coordinator_dashboard"))
        
        registrations = Registration.query.filter_by(event_id=event.id).all()
        return render_template("coordinator_participants.html", event=event, registrations=registrations)


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
        notifications = Notification.query.filter_by(student_id=student.id, is_read=False).all()
        return render_template("student_dashboard.html", student=student, registrations=registrations, notifications=notifications)

    @app.route("/student/history")
    @student_login_required
    def student_history():
        student = Student.query.get(session["student_id"])
        registrations = Registration.query.filter_by(student_id=student.id).all()
        return render_template("student_history.html", registrations=registrations)

    @app.route("/student/certificate/<int:event_id>")
    @student_login_required
    def student_certificate(event_id):
        student = Student.query.get(session["student_id"])
        registration = Registration.query.filter_by(student_id=student.id, event_id=event_id, status='Approved').first()
        
        if not registration:
            flash("Certificate not available.", "error")
            return redirect(url_for("student_dashboard"))
            
        event = registration.event
        if event.status != 'Completed': # Assuming 'Completed' status exists or we use date check
             # For now, let's allow if approved, or maybe add a check. 
             # Requirement said "Download participation certificates".
             pass

        return render_template("student_certificate.html", student=student, event=event)

    @app.route("/student/notifications")
    @student_login_required
    def student_notifications():
        student = Student.query.get(session["student_id"])
        notifications = Notification.query.filter_by(student_id=student.id).order_by(Notification.created_at.desc()).all()
        
        # Mark as read
        for notif in notifications:
            notif.is_read = True
        db.session.commit()
        
        return render_template("student_notifications.html", notifications=notifications)

    @app.route("/student/profile", methods=["GET", "POST"])
    @student_login_required
    def student_profile():
        student = Student.query.get(session["student_id"])
        
        if request.method == "POST":
            email = request.form.get("email").strip()
            password = request.form.get("password").strip()
            
            if email:
                # Check if email is taken by another student
                existing = Student.query.filter_by(email=email).first()
                if existing and existing.id != student.id:
                    flash("Email already taken.", "error")
                else:
                    student.email = email
            
            if password:
                student.set_password(password)
                
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("student_profile"))
            
        return render_template("student_profile.html", student=student)


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
        categories = Category.query.all()
        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            category_id = request.form.get("category_id")
            description = (request.form.get("description") or "").strip() or None
            venue = (request.form.get("venue") or "").strip()
            date_str = request.form.get("date")
            
            # File Upload
            image_file = 'default.jpg'
            if 'image_file' in request.files:
                file = request.files['image_file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_file = filename

            if not title or not venue or not date_str or not category_id:
                flash("Title, Category, Venue and Date are required.", "error")
                return render_template("create.html", title=title, description=description, venue=venue, date=date_str, categories=categories)

            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash("Invalid date format.", "error")
                return render_template("create.html", title=title, description=description, venue=venue, date=date_str, categories=categories)

            # Admin created events are automatically approved
            event = Event(title=title, category_id=category_id, description=description, venue=venue, date=event_date, status='Approved', image_file=image_file)
            db.session.add(event)
            db.session.commit()

            flash("Event created successfully!", "success")
            return redirect(url_for("index"))

        return render_template("create.html", title="", description="", venue="", date="", categories=categories)

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

    # ##########################################
    # Admin: Manage Coordinators
    # ################################################

    @app.route("/admin/coordinators")
    @admin_login_required
    def admin_coordinators():
        coordinators = Coordinator.query.all()
        return render_template("admin_coordinators.html", coordinators=coordinators)

    @app.route("/admin/coordinators/create", methods=["GET", "POST"])
    @admin_login_required
    def admin_create_coordinator():
        if request.method == "POST":
            username = request.form.get("username").strip()
            password = request.form.get("password").strip()
            department = request.form.get("department").strip()

            if not username or not password:
                flash("Username and password required.", "error")
                return render_template("admin_create_coordinator.html")

            if Coordinator.query.filter_by(username=username).first():
                flash("Username already taken.", "error")
                return render_template("admin_create_coordinator.html")

            coordinator = Coordinator(username=username, department=department)
            coordinator.set_password(password)
            db.session.add(coordinator)
            db.session.commit()

            flash("Coordinator created successfully.", "success")
            return redirect(url_for("admin_coordinators"))

        return render_template("admin_create_coordinator.html")

    @app.route("/admin/coordinators/delete/<int:id>", methods=["POST"])
    @admin_login_required
    def admin_delete_coordinator(id):
        coordinator = Coordinator.query.get_or_404(id)
        db.session.delete(coordinator)
        db.session.commit()
        flash("Coordinator deleted.", "success")
        return redirect(url_for("admin_coordinators"))

    @app.route("/admin/event/<int:event_id>/approve", methods=["POST"])
    @admin_login_required
    def admin_approve_event(event_id):
        event = Event.query.get_or_404(event_id)
        event.status = 'Approved'
        db.session.commit()
        flash("Event approved.", "success")
        return redirect(url_for("index"))

    @app.route("/admin/event/<int:event_id>/reject", methods=["POST"])
    @admin_login_required
    def admin_reject_event(event_id):
        event = Event.query.get_or_404(event_id)
        event.status = 'Rejected'
        db.session.commit()
        flash("Event rejected.", "success")
        return redirect(url_for("index"))

    @app.route("/admin/students")
    @admin_login_required
    def admin_students():
        students = Student.query.all()
        return render_template("admin_students.html", students=students)

    @app.route("/admin/students/delete/<int:id>", methods=["POST"])
    @admin_login_required
    def admin_delete_student(id):
        student = Student.query.get_or_404(id)
        db.session.delete(student)
        db.session.commit()
        flash("Student account deleted.", "success")
        return redirect(url_for("admin_students"))

    @app.route("/admin/reports")
    @admin_login_required
    def admin_reports():
        total_students = Student.query.count()
        total_events = Event.query.count()
        total_registrations = Registration.query.count()
        
        # Event stats
        events = Event.query.all()
        event_stats = []
        for event in events:
            count = Registration.query.filter_by(event_id=event.id).count()
            event_stats.append({
                'title': event.title,
                'date': event.date,
                'registrations': count,
                'status': event.status
            })
            
        return render_template("admin_reports.html", 
                             total_students=total_students,
                             total_events=total_events,
                             total_registrations=total_registrations,
                             event_stats=event_stats)

    return app

if __name__ == "__main__":
    create_app().run(debug=True)
