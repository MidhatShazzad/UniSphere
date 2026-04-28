import os
import sys
from threading import Timer
from flask import Flask, redirect, session, url_for
from config import Config
from models.db import init_app as init_db_app

from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.faculty_routes import faculty_bp
from routes.admin_routes import admin_bp
from routes.course_routes import course_bp

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
init_db_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(student_bp, url_prefix="/student")
app.register_blueprint(faculty_bp, url_prefix="/faculty")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(course_bp)

@app.route("/")
def home():
    return redirect(url_for("auth.login"))

@app.route("/dashboard")
def dashboard_router():
    role = session.get("role")

    if not role:
        return redirect(url_for("auth.login"))

    if role == "student":
        return redirect(url_for("student.dashboard"))
    elif role == "faculty":
        return redirect(url_for("faculty.dashboard"))
    elif role == "admin":
        return redirect(url_for("admin.dashboard"))

    return redirect(url_for("auth.login"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

if __name__ == "__main__":
    def open_browser():
        url = "http://127.0.0.1:5000/login"
        if sys.platform == 'win32':
            os.startfile(url)
        else:
            import webbrowser
            webbrowser.open(url)
    
    # Open browser after 1 second delay to allow server to start
    timer = Timer(1, open_browser)
    timer.daemon = True
    timer.start()
    
    app.run(debug=True, use_reloader=False)
