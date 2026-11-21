import os
import re
import secrets
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import config
from database import get_db, init_app, init_db

CATEGORIES = ["Road and Transportation", "Water Supply", "Electricity", "Garbage Collection", "Drainage and Sanitation", "Streetlights", "Public Safety", "Other"]
STATUSES = ["Pending", "In Progress", "Resolved", "Rejected"]

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(config)
    if test_config:
        app.config.update(test_config)
    Path(app.config["INSTANCE_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    init_app(app)

    @app.before_request
    def csrf_check():
        if request.method == "POST":
            supplied = request.form.get("csrf_token", "")
            expected = session.get("csrf_token", "")
            if not supplied or not expected or not secrets.compare_digest(supplied, expected):
                abort(400, "Your form expired. Refresh the page and try again.")

    @app.context_processor
    def inject_globals():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {"csrf_token": session["csrf_token"], "current_user": session.get("user"), "categories": CATEGORIES}

    def login_required(role=None):
        def decorator(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                user = session.get("user")
                if not user:
                    flash("Please sign in to continue.", "warning")
                    return redirect(url_for("login"))
                if role and user["role"] != role:
                    abort(403)
                return view(*args, **kwargs)
            return wrapped
        return decorator

    def fetch_complaint(where, params):
        return get_db().execute("""SELECT c.*, u.full_name, d.department_name, f.rating AS feedback_rating
            FROM complaints c JOIN users u ON u.id=c.user_id
            LEFT JOIN departments d ON d.id=c.department_id LEFT JOIN feedback f ON f.complaint_id=c.id
            WHERE """ + where, params).fetchone()

    @app.route("/")
    def index():
        db = get_db()
        stats = {
            "total": db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0],
            "resolved": db.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0],
            "active": db.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('Pending','In Progress')").fetchone()[0],
            "departments": db.execute("SELECT COUNT(*) FROM departments").fetchone()[0],
        }
        return render_template("public/index.html", stats=stats)

    @app.route("/about")
    def about():
        return render_template("public/about.html")

    @app.route("/services")
    def services():
        return render_template("public/services.html")

    @app.route("/how-it-works")
    def how_it_works():
        return render_template("public/how_it_works.html")

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            name=request.form.get("name", "").strip()
            email=request.form.get("email", "").strip().lower()
            subject=request.form.get("subject", "").strip()
            message=request.form.get("message", "").strip()
            if len(name)<2 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(subject)<3 or len(message)<10:
                flash("Please provide a valid name, email, subject and message.", "danger")
            else:
                db=get_db()
                db.execute("INSERT INTO contact_messages(name,email,subject,message) VALUES(?,?,?,?)",(name,email,subject,message))
                db.commit()
                flash("Thank you. Your message has been received by the portal team.", "success")
                return redirect(url_for("contact"))
        return render_template("public/contact.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name, email = request.form.get("full_name", "").strip(), request.form.get("email", "").strip().lower()
            mobile, address = request.form.get("mobile", "").strip(), request.form.get("address", "").strip()
            password, confirm = request.form.get("password", ""), request.form.get("confirm_password", "")
            if request.form.get("terms") != "accepted":
                flash("Please accept the terms to create your account.", "danger")
            elif len(name) < 2 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or not re.fullmatch(r"[0-9+() -]{8,20}", mobile) or len(address) < 5:
                flash("Please provide valid details in every field.", "danger")
            elif len(password) < 8:
                flash("Password must contain at least 8 characters.", "danger")
            elif password != confirm:
                flash("Passwords do not match.", "danger")
            else:
                try:
                    get_db().execute("INSERT INTO users(full_name,email,mobile,address,password_hash) VALUES(?,?,?,?,?)", (name,email,mobile,address,generate_password_hash(password)))
                    get_db().commit()
                    flash("Account created. You can now sign in.", "success")
                    return redirect(url_for("login"))
                except sqlite3.IntegrityError:
                    flash("An account with that email already exists.", "danger")
        return render_template("auth/register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
                session.clear()
                session["user"] = {"id": user["id"], "name": user["full_name"], "email": user["email"], "role": user["role"]}
                session["csrf_token"] = secrets.token_urlsafe(32)
                session.permanent = request.form.get("remember") == "yes" and user["role"] == "citizen"
                return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "citizen_dashboard"))
            flash("Email or password is incorrect.", "danger")
        return render_template("auth/login.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = get_db().execute("SELECT * FROM users WHERE email=? AND role='admin'", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
                session.clear()
                session["user"] = {"id": user["id"], "name": user["full_name"], "email": user["email"], "role": user["role"]}
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("admin_dashboard"))
            flash("Administrator email or password is incorrect.", "danger")
        return render_template("auth/admin_login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("index"))

    @app.route("/citizen/dashboard")
    @login_required("citizen")
    def citizen_dashboard():
        uid = session["user"]["id"]
        db = get_db()
        counts = {status: db.execute("SELECT COUNT(*) FROM complaints WHERE user_id=? AND status=?", (uid,status)).fetchone()[0] for status in STATUSES}
        total = db.execute("SELECT COUNT(*) FROM complaints WHERE user_id=?", (uid,)).fetchone()[0]
        rows = db.execute("SELECT * FROM complaints WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (uid,)).fetchall()
        return render_template("citizen/dashboard.html", total=total, counts=counts, complaints=rows)

    @app.route("/dashboard")
    def legacy_dashboard():
        return redirect(url_for("citizen_dashboard"), code=301)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required("citizen")
    def profile():
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id=? AND role='citizen'", (session["user"]["id"],)).fetchone()
        if request.method == "POST":
            name = request.form.get("full_name", "").strip()
            mobile = request.form.get("mobile", "").strip()
            address = request.form.get("address", "").strip()
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            if len(name) < 2 or not re.fullmatch(r"[0-9+() -]{8,20}", mobile) or len(address) < 5:
                flash("Please enter a valid name, mobile number, and address.", "danger")
            elif new_password and (len(new_password) < 8 or not check_password_hash(user["password_hash"], current_password)):
                flash("Enter your current password and choose a new password of at least 8 characters.", "danger")
            else:
                if new_password:
                    db.execute("UPDATE users SET full_name=?,mobile=?,address=?,password_hash=? WHERE id=?", (name,mobile,address,generate_password_hash(new_password),user["id"]))
                else:
                    db.execute("UPDATE users SET full_name=?,mobile=?,address=? WHERE id=?", (name,mobile,address,user["id"]))
                db.commit()
                session["user"]["name"] = name
                flash("Your profile has been updated.", "success")
                return redirect(url_for("profile"))
            user = {**dict(user), "full_name": name, "mobile": mobile, "address": address}
        return render_template("citizen/profile.html", profile=user)

    @app.route("/complaints/new", methods=["GET", "POST"])
    @login_required("citizen")
    def submit_complaint():
        if request.method == "POST":
            title=request.form.get("title", "").strip(); category=request.form.get("category", "")
            description=request.form.get("description", "").strip(); location=request.form.get("location", "").strip(); area=request.form.get("area", "").strip()
            image=request.files.get("image"); filename=None
            valid=len(title)>=5 and category in CATEGORIES and len(description)>=20 and len(location)>=3 and len(area)>=2
            if not valid:
                flash("Complete all required fields with meaningful details.", "danger")
            elif image and image.filename:
                ext=image.filename.rsplit(".",1)[-1].lower() if "." in image.filename else ""
                if ext not in app.config["ALLOWED_EXTENSIONS"]:
                    flash("Upload a PNG, JPG, JPEG, or WEBP image.", "danger")
                    return render_template("citizen/submit_complaint.html")
                filename=secrets.token_hex(16)+"."+ext
                image.save(Path(app.config["UPLOAD_DIR"])/secure_filename(filename))
            if valid:
                complaint_id="PGMS-"+secrets.token_hex(4).upper()
                db=get_db(); cur=db.execute("""INSERT INTO complaints(complaint_id,user_id,title,category,description,location,area,image_filename)
                    VALUES(?,?,?,?,?,?,?,?)""",(complaint_id,session["user"]["id"],title,category,description,location,area,filename))
                db.execute("INSERT INTO complaint_history(complaint_id,new_status,remarks,updated_by) VALUES(?,?,?,?)",(cur.lastrowid,"Pending","Complaint submitted",session["user"]["id"]))
                db.commit(); flash(f"Complaint submitted. Your tracking ID is {complaint_id}.","success")
                return redirect(url_for("complaint_details", complaint_id=complaint_id))
        return render_template("citizen/submit_complaint.html")

    @app.route("/complaints/my")
    @login_required("citizen")
    def my_complaints():
        rows=get_db().execute("SELECT c.*,d.department_name FROM complaints c LEFT JOIN departments d ON d.id=c.department_id WHERE c.user_id=? ORDER BY c.created_at DESC",(session["user"]["id"],)).fetchall()
        return render_template("citizen/my_complaints.html", complaints=rows)

    @app.route("/complaints")
    def legacy_my_complaints():
        return redirect(url_for("my_complaints"), code=301)

    @app.route("/complaints/track", methods=["GET", "POST"])
    @login_required("citizen")
    def track_complaint():
        complaint=None
        # IDs are issued in uppercase, but citizens often copy them with spaces
        # or type them in lowercase. Normalize before doing the owner-scoped lookup.
        complaint_id=re.sub(r"\s+", "", request.values.get("complaint_id", "")).upper()
        if complaint_id:
            complaint=fetch_complaint("c.complaint_id=? COLLATE NOCASE AND c.user_id=?",(complaint_id,session["user"]["id"]))
            if not complaint: flash("We couldn't match that tracking ID to a complaint on your account. Check the code and sign in with the account that submitted it.","warning")
        history=[]
        if complaint:
            history=get_db().execute("SELECT h.*,u.full_name AS actor FROM complaint_history h LEFT JOIN users u ON u.id=h.updated_by WHERE h.complaint_id=? ORDER BY h.created_at,h.id",(complaint["id"],)).fetchall()
        return render_template("citizen/track_complaint.html", complaint=complaint, history=history, searched=bool(complaint_id), tracking_id=complaint_id)

    @app.route("/track")
    def legacy_track():
        return redirect(url_for("track_complaint", **request.args), code=301)

    @app.route("/complaints/<complaint_id>")
    @login_required("citizen")
    def complaint_details(complaint_id):
        complaint=fetch_complaint("c.complaint_id=? AND c.user_id=?",(complaint_id,session["user"]["id"]))
        if not complaint: abort(404)
        history=get_db().execute("SELECT h.*,u.full_name AS actor FROM complaint_history h LEFT JOIN users u ON u.id=h.updated_by WHERE h.complaint_id=? ORDER BY h.created_at,h.id",(complaint["id"],)).fetchall()
        return render_template("citizen/complaint_details.html", complaint=complaint, history=history)

    @app.route("/feedback/<complaint_id>", methods=["GET", "POST"])
    @login_required("citizen")
    def feedback(complaint_id):
        complaint=fetch_complaint("c.complaint_id=? AND c.user_id=?",(complaint_id,session["user"]["id"]))
        if not complaint: abort(404)
        if complaint["status"]!="Resolved" or complaint["feedback_rating"] is not None:
            flash("Feedback is available once, after resolution.","info"); return redirect(url_for("complaint_details",complaint_id=complaint_id))
        if request.method=="POST":
            try: rating=int(request.form.get("rating","0"))
            except ValueError: rating=0
            message=request.form.get("message","").strip()
            if rating not in range(1,6) or len(message)<5: flash("Choose a rating and write at least 5 characters.","danger")
            else:
                get_db().execute("INSERT INTO feedback(complaint_id,user_id,rating,message) VALUES(?,?,?,?)",(complaint["id"],session["user"]["id"],rating,message)); get_db().commit()
                flash("Thank you for your feedback.","success"); return redirect(url_for("complaint_details",complaint_id=complaint_id))
        return render_template("citizen/feedback.html", complaint=complaint)

    @app.route("/complaints/<complaint_id>/feedback", methods=["GET", "POST"])
    def legacy_feedback(complaint_id):
        return redirect(url_for("feedback", complaint_id=complaint_id), code=307 if request.method == "POST" else 301)

    @app.route("/admin/dashboard")
    @login_required("admin")
    def admin_dashboard():
        db=get_db(); counts={status:db.execute("SELECT COUNT(*) FROM complaints WHERE status=?",(status,)).fetchone()[0] for status in STATUSES}
        total_users=db.execute("SELECT COUNT(*) FROM users WHERE role='citizen'").fetchone()[0]
        latest=db.execute("SELECT c.*,u.full_name FROM complaints c JOIN users u ON u.id=c.user_id ORDER BY c.created_at DESC LIMIT 8").fetchall()
        categories=db.execute("SELECT category,COUNT(*) AS total FROM complaints GROUP BY category ORDER BY total DESC LIMIT 8").fetchall()
        months=db.execute("SELECT strftime('%Y-%m',created_at) AS month,COUNT(*) AS total FROM complaints WHERE created_at >= date('now','-5 months','start of month') GROUP BY month ORDER BY month").fetchall()
        max_category=max((row["total"] for row in categories),default=1)
        max_month=max((row["total"] for row in months),default=1)
        return render_template("admin/dashboard.html", counts=counts,total_users=total_users,complaints=latest,categories=categories,months=months,max_category=max_category,max_month=max_month)

    @app.route("/admin")
    def legacy_admin_dashboard():
        return redirect(url_for("admin_dashboard"), code=301)

    @app.route("/admin/complaints")
    @login_required("admin")
    def manage_complaints():
        search=request.args.get("q","").strip(); status=request.args.get("status",""); category=request.args.get("category","")
        sql="SELECT c.*,u.full_name,d.department_name FROM complaints c JOIN users u ON u.id=c.user_id LEFT JOIN departments d ON d.id=c.department_id WHERE 1=1"; params=[]
        if search: sql+=" AND (c.complaint_id LIKE ? OR c.title LIKE ? OR u.full_name LIKE ?)"; params += [f"%{search}%"]*3
        if status in STATUSES: sql+=" AND c.status=?"; params.append(status)
        if category in CATEGORIES: sql+=" AND c.category=?"; params.append(category)
        rows=get_db().execute(sql+" ORDER BY c.created_at DESC",params).fetchall()
        return render_template("admin/manage_complaints.html",complaints=rows,statuses=STATUSES,selected_status=status,selected_category=category)

    @app.route("/admin/complaints/<complaint_id>")
    @login_required("admin")
    def admin_complaint(complaint_id):
        complaint=fetch_complaint("c.complaint_id=?",(complaint_id,))
        if not complaint: abort(404)
        history=get_db().execute("SELECT h.*,u.full_name AS actor FROM complaint_history h LEFT JOIN users u ON u.id=h.updated_by WHERE h.complaint_id=? ORDER BY h.created_at,h.id",(complaint["id"],)).fetchall()
        departments=get_db().execute("SELECT * FROM departments ORDER BY department_name").fetchall()
        feedback_row=get_db().execute("SELECT f.*,u.full_name FROM feedback f JOIN users u ON u.id=f.user_id WHERE f.complaint_id=?",(complaint["id"],)).fetchone()
        return render_template("citizen/complaint_details.html",complaint=complaint,history=history,admin=True,departments=departments,statuses=STATUSES,feedback_row=feedback_row)

    @app.route("/admin/complaints/<complaint_id>/update", methods=["POST"])
    @login_required("admin")
    def update_complaint(complaint_id):
        db=get_db(); row=db.execute("SELECT * FROM complaints WHERE complaint_id=?",(complaint_id,)).fetchone()
        if not row: abort(404)
        status=request.form.get("status",""); remarks=request.form.get("admin_remarks","").strip(); dept=request.form.get("department_id","")
        if status not in STATUSES: flash("Select a valid status.","danger")
        else:
            department_id=int(dept) if dept.isdigit() else None
            db.execute("UPDATE complaints SET status=?,admin_remarks=?,department_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(status,remarks,department_id,row["id"]))
            if status != row["status"] or remarks:
                db.execute("INSERT INTO complaint_history(complaint_id,previous_status,new_status,remarks,updated_by) VALUES(?,?,?,?,?)",(row["id"],row["status"],status,remarks,session["user"]["id"]))
            db.commit(); flash("Complaint updated.","success")
        return redirect(url_for("admin_complaint",complaint_id=complaint_id))

    @app.route("/admin/departments", methods=["GET", "POST"])
    @login_required("admin")
    def manage_departments():
        db=get_db()
        if request.method=="POST":
            name=request.form.get("department_name","").strip(); description=request.form.get("description","").strip()
            if len(name)<3: flash("Enter a department name.","danger")
            else:
                try: db.execute("INSERT INTO departments(department_name,description) VALUES(?,?)",(name,description)); db.commit(); flash("Department added.","success")
                except sqlite3.IntegrityError: flash("That department already exists.","warning")
        rows=db.execute("SELECT d.*,COUNT(c.id) AS complaint_count FROM departments d LEFT JOIN complaints c ON c.department_id=d.id GROUP BY d.id ORDER BY d.department_name").fetchall()
        return render_template("admin/manage_departments.html",departments=rows)

    @app.errorhandler(413)
    def too_large(_error):
        flash("Image must be 5 MB or smaller.","danger"); return redirect(url_for("submit_complaint")),413

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.error("Unhandled application error: %s", error)
        return render_template("errors/500.html"), 500

    with app.app_context():
        init_db()
    return app

app=create_app()
if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG")=="1")
