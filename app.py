from flask import Flask, request, render_template,redirect,url_for,jsonify,session
import pymysql.cursors

app = Flask(__name__)
app.secret_key = 'this_is_supposed_to_be_secret'


def connectDB():
    conn = pymysql.connect(host='127.0.0.1', user='pricosha', database='PriCoSha')
    return conn

@app.route("/")
def index():
    if 'user' in session:
        return render_template("index.html",email=session['user'])
    else:
        return render_template("index.html",email="No one sign in yet")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/login/user",methods=['POST'])
def loginUser():
    email = request.form.get("email")
    pwd = request.form.get("password")
    session['user'] = email
    return redirect(url_for('index'))


@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/signup/user",methods=['POST'])
def signUpUser():
    email = request.form.get("email")
    pwd = request.form.get("password")
    return email


if __name__ == "__main__":
	app.run(host='0.0.0.0',debug=True)