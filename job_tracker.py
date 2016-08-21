from flask import Flask, flash, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, login_user, logout_user
import pandas as pd

# "postgresql://postgres:1malirudolf@localhost/app1"

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://mfsqowwrzxhlra:Wga1CdXQFUWqGp_P567WYQ9SaF@ec2-54-243-249-137.compute-1.amazonaws.com:5432/db14sddu9ssmtn"
app.config["SECRET_KEY"] = "ITSASECRET"
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(db.Model):

  __tablename__ = "users"

  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(80), unique=True)
  password = db.Column(db.String(120), unique=False)

  def __init__(self, username, password):
    self.username = username
    self.password = password

  def is_active(self):
    return True

  def get_id(self):
    return self.id

  def is_authenticated(self):
    return self.authenticated

  def is_anonymous(self):
    return False

  def __repr__(self):
    return self.username

class Job(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(80), db.ForeignKey("users.username"))
  company_name = db.Column(db.String(100), unique=False)
  position_name = db.Column(db.String(100), unique=False)
  requirements = db.Column(db.String(300), unique=False)
  link_to_ad = db.Column(db.String(300), unique=False)
  link_to_job = db.Column(db.String(300), unique=False)
  submitted = db.Column(db.Boolean, unique=False)

  user = db.relationship("User", lazy="select", backref="jobs")

  def __init__(self, username, company_name, position_name, requirements, link_to_ad, link_to_job, submitted):
    self.username = username
    self.company_name = company_name
    self.position_name = position_name
    self.requirements = requirements
    self.link_to_ad = link_to_ad
    self.link_to_job = link_to_job
    self.submitted = submitted

  def __repr__(self):
    return "%s %s, %s, %s, %s, %s, %s>" % (self.username, self.company_name, self.position_name,
                                          self.requirements, self.link_to_ad, self.link_to_job, self.submitted)

@login_manager.user_loader
def load_user(id):
  return User.query.get(int(id))

@app.route("/register", methods=["GET", "POST"])
def register():
  if request.method == "GET":
    return render_template("register.html")
  user = User(request.form["username"], request.form["password"])
  allUsers = []
  for u in User.query.all(): allUsers.append(str(u))
  uname = request.form["username"]
  print(allUsers)
  if not uname in allUsers:
    db.session.add(user)
    db.session.commit()
  else: flash("That username already exists! Please log in.")
  return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
  if request.method == "GET":
    return render_template("login.html")
  username = request.form["username"]
  password = request.form["password"]
  registered_user = User.query.filter_by(username=username, password=password).first()
  if registered_user is None:
    registered_user2 = User.query.filter_by(username=username).first()
    if registered_user2 is None:
      flash("This account is non-existent. Please register.")
      return redirect(url_for("register"))
    else:
      flash("Incorrect password. Please try again.")
      return redirect(url_for("login"))
  login_user(registered_user)
  return redirect(url_for("list_jobs", name=request.form["username"]))

@app.route("/logout")
def logout():
  logout_user()
  return redirect(url_for("index"))

@app.route("/", methods=["GET"])
def index():
  return render_template("index.html")

@app.route("/list_jobs/<name>", methods=["GET"])
@login_required
def list_jobs(name):
  allJobs = Job.query.filter_by(username=name)
  data_records = [rec.__dict__ for rec in allJobs]
  dfJobs = pd.DataFrame.from_records(data_records)
  colNames = ["ID", "Employer", "Position", "Notes"]
  colNames2 = ["Job ID", "Company", "Position", "Requirements"]
  if not dfJobs.empty:
    del dfJobs["_sa_instance_state"]; print(dfJobs)
    for i in range(len(dfJobs.index)):
      if dfJobs.ix[i, "link_to_ad"][0:3] != "htt": dfJobs.ix[i, "link_to_ad"] = "http://" + dfJobs.ix[i, "link_to_ad"]
      if dfJobs.ix[i, "link_to_job"][0:3] != "htt": dfJobs.ix[i, "link_to_job"] = "http://" + dfJobs.ix[i, "link_to_job"]
    dfJobs.columns = ["Company", "Job ID", "Link to Ad", "Link to Job", "Position", "Requirements", "Submitted", "Username"]
    dfJobsSub = dfJobs.ix[dfJobs.Submitted == True, ["Job ID", "Company", "Position", "Requirements", "Link to Ad", "Link to Job"]].reset_index(drop=True)
    dfJobsUnsub = dfJobs.ix[dfJobs.Submitted == False, ["Job ID", "Company", "Position", "Requirements", "Link to Ad", "Link to Job"]].reset_index(drop=True)
  else: dfJobsSub = dfJobsUnsub = None
  return render_template("list_jobs.html", name=name, dfJobsSub=dfJobsSub, dfJobsUnsub=dfJobsUnsub, colNames=colNames, colNames2=colNames2)

@app.route("/post_job/<name>", methods=["POST"])
@login_required
def post_job(name):
  job = Job(name, request.form["company_name"], request.form["position_name"],
            request.form["requirements"], request.form["link_to_ad"], request.form["link_to_job"], False)
  db.session.add(job)
  db.session.commit()
  return redirect(url_for("list_jobs", name=name))

@app.route("/delete_job/<int:id>", methods=["POST"])
@login_required
def delete_job(id):
  print(id)
  user = pd.DataFrame.from_records([rec.__dict__ for rec in Job.query.filter_by(id=id).all()])
  username = user["username"].astype("str")[0]
  deljob = Job.query.get(int(request.form["delete"]))
  db.session.delete(deljob)
  db.session.commit()
  return redirect(url_for("list_jobs", name=username))

@app.route("/complete_job/<int:id>", methods=["POST"])
@login_required
def complete_job(id):
  user = pd.DataFrame.from_records([rec.__dict__ for rec in Job.query.filter_by(id=id).all()])
  username = user["username"].astype("str")[0]
  completeJob = Job.query.get(int(request.form["complete"]))
  completeJob.submitted = True
  db.session.commit()
  return redirect(url_for("list_jobs", name=username))

@app.route("/redir", methods=["GET", "POST"])
def redir():
  link = "http://" + request.form["link"]
  print(link)
  actual_link = "5;URL=" + link
  return render_template("redir.html", **locals())

if __name__ == "__main__":
  db.create_all()
  app.run(debug=True)