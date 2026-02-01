from flask import Flask, flash, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, login_user, logout_user, UserMixin, current_user
import pandas as pd
import os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Use environment variables for configuration
# Default to SQLite for local development if DATABASE_URL is not set
database_url = os.environ.get("DATABASE_URL", "sqlite:///jobtracker.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-please-change")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return self.username

class Job(db.Model):
    __tablename__ = "jobs"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), db.ForeignKey("users.username"), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    position_name = db.Column(db.String(100), nullable=False)
    requirements = db.Column(db.String(300))
    link_to_ad = db.Column(db.String(300))
    link_to_job = db.Column(db.String(300))
    submitted = db.Column(db.Boolean, default=False)

    user = db.relationship("User", backref=db.backref("jobs", lazy=True))

    def __init__(self, username, company_name, position_name, requirements, link_to_ad, link_to_job, submitted=False):
        self.username = username
        self.company_name = company_name
        self.position_name = position_name
        self.requirements = requirements
        self.link_to_ad = link_to_ad
        self.link_to_job = link_to_job
        self.submitted = submitted

    def __repr__(self):
        return f"<{self.username} {self.company_name}, {self.position_name}>"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    
    username = request.form["username"]
    password = request.form["password"]
    
    if User.query.filter_by(username=username).first():
        flash("That username already exists! Please log in.")
        return redirect(url_for("login"))
    
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
        
    username = request.form["username"]
    password = request.form["password"]
    
    user = User.query.filter_by(username=username).first()
    
    if user is None or not user.check_password(password):
        flash("Invalid username or password")
        return redirect(url_for("login"))
        
    login_user(user)
    return redirect(url_for("list_jobs", name=username))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/list_jobs/<name>", methods=["GET"])
@login_required
def list_jobs(name):
    if name != current_user.username:
        # Prevent users from viewing other users' jobs
        flash("You are not authorized to view this page.")
        return redirect(url_for("list_jobs", name=current_user.username))

    jobs = Job.query.filter_by(username=name).all()
    
    # Convert to list of dicts for DataFrame
    data_records = []
    for job in jobs:
        data_records.append({
            "Job ID": job.id,
            "Company": job.company_name,
            "Position": job.position_name,
            "Requirements": job.requirements,
            "Link to Ad": job.link_to_ad,
            "Link to Job": job.link_to_job,
            "Submitted": job.submitted,
            "Username": job.username
        })

    dfJobs = pd.DataFrame(data_records)
    
    colNames = ["ID", "Employer", "Position", "Notes"]
    colNames2 = ["Job ID", "Company", "Position", "Requirements"]
    
    dfJobsSub = None
    dfJobsUnsub = None

    if not dfJobs.empty:
        # Fix links
        for i in dfJobs.index:
            if dfJobs.loc[i, "Link to Ad"] and not dfJobs.loc[i, "Link to Ad"].startswith("http"):
                dfJobs.loc[i, "Link to Ad"] = "https://" + dfJobs.loc[i, "Link to Ad"]
            if dfJobs.loc[i, "Link to Job"] and not dfJobs.loc[i, "Link to Job"].startswith("http"):
                dfJobs.loc[i, "Link to Job"] = "https://" + dfJobs.loc[i, "Link to Job"]
        
        # Filter submitted vs unsubmitted
        dfJobsSub = dfJobs.loc[dfJobs["Submitted"] == True, ["Job ID", "Company", "Position", "Requirements", "Link to Ad", "Link to Job"]].reset_index(drop=True)
        dfJobsUnsub = dfJobs.loc[dfJobs["Submitted"] == False, ["Job ID", "Company", "Position", "Requirements", "Link to Ad", "Link to Job"]].reset_index(drop=True)

    return render_template("list_jobs.html", name=name, dfJobsSub=dfJobsSub, dfJobsUnsub=dfJobsUnsub, colNames=colNames, colNames2=colNames2)

@app.route("/post_job/<name>", methods=["POST"])
@login_required
def post_job(name):
    if name != current_user.username:
        return redirect(url_for("list_jobs", name=current_user.username))

    job = Job(
        username=name,
        company_name=request.form["company_name"],
        position_name=request.form["position_name"],
        requirements=request.form["requirements"],
        link_to_ad=request.form["link_to_ad"],
        link_to_job=request.form["link_to_job"],
        submitted=False
    )
    db.session.add(job)
    db.session.commit()
    return redirect(url_for("list_jobs", name=name))

@app.route("/delete_job/<int:id>", methods=["POST"])
@login_required
def delete_job(id):
    job_to_delete = Job.query.get_or_404(int(request.form["delete"]))
    
    if job_to_delete.username != current_user.username:
        flash("You cannot delete this job.")
        return redirect(url_for("list_jobs", name=current_user.username))
    
    username = job_to_delete.username
    db.session.delete(job_to_delete)
    db.session.commit()
    return redirect(url_for("list_jobs", name=username))

@app.route("/complete_job/<int:id>", methods=["POST"])
@login_required
def complete_job(id):
    job_to_complete = Job.query.get_or_404(int(request.form["complete"]))
    
    if job_to_complete.username != current_user.username:
        flash("You cannot update this job.")
        return redirect(url_for("list_jobs", name=current_user.username))

    username = job_to_complete.username
    job_to_complete.submitted = True
    db.session.commit()
    return redirect(url_for("list_jobs", name=username))

@app.route("/redir", methods=["GET", "POST"])
def redir():
    link = request.form.get("link", "")
    if link and not link.startswith("http"):
        link = "https://" + link
    return render_template("redir.html", link=link)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)