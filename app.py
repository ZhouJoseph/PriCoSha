from flask import Flask, request, render_template,redirect,url_for,jsonify,session
import pymysql.cursors

app = Flask(__name__)
app.secret_key = 'this_is_supposed_to_be_secret'

conn = pymysql.connect(host='127.0.0.1', user='pricosha', database='PriCoSha')


class error:
    def __init__(self,err=None):
        self.UserAlreadyExist = False
        self.UserNotFound = False
        self.PwdNotMatch = False
        self.EmailLength = False
        self.SecPwdMatch = False
        if err == "UserAlreadyExist":
            self.UserAlreadyExist = True
        elif err == "UserNotFound":
            self.UserNotFound = True
        elif err == "PwdNotMatch":
            self.PwdNotMatch = True
        elif err == "EmailLength":
            self.EmailLength = True
        elif err == "2PwdMatch":
            self.SecPwdMatch = True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    error = request.args.get('error')
    return render_template("login.html",errors = error )

@app.route("/login/user",methods=['GET','POST'])
def loginUser():
    email = request.form["email"]
    pwd = request.form["pwd"]
    cursor = conn.cursor()
    sql = "SELECT * FROM person WHERE email=(%s) AND password=(%s)"
    cursor.execute(sql,(email,pwd))
    data = cursor.fetchone()
    cursor.close()
    error = None
    if(data):
        session['user'] = email
        return redirect(url_for('post'))
    else:
        msg = 'Invalid login or username'
        return redirect(url_for('login', error=msg))

@app.route("/signup")
def signup():
    error = request.args.get('error')
    return render_template("signup.html",errors = error)

@app.route("/signup/user",methods=['GET','POST'])
def signUpUser():
    fname = request.form["fname"]
    lname = request.form["lname"]
    email = request.form["email"]
    pwd = request.form["pwd"]
    secPwd = request.form["2pwd"]

    if pwd != secPwd:
        msg = "Your Passwords should match each other"
        return redirect(url_for('signup',error=msg))
    if len(email) > 20:
        msg = "Sorry, but email length cannot exceed 20"
        return redirect(url_for('signup',error=msg))
    cursor = conn.cursor()
    try:
        sql = "SELECT * FROM person WHERE email=(%s)"
        cursor.execute(sql,(email))
        result = cursor.fetchone()
    finally:
        if not result:
            sql = "INSERT INTO `person` (`email`,`password`,`fname`,`lname`) VALUES (%s,%s,%s,%s)"
            cursor.execute(sql,(email,pwd,fname,lname))
            session['user'] = email
            return redirect(url_for('post'))
        else:
            msg = "User Already Exist"
            return redirect(url_for('signup',error=msg))

@app.route("/post",methods=['GET','POST'])
def post():
    if request.method == 'GET':
        if 'user' in session:
            return render_template('post.html',email=session['user'])
        else:
            return redirect(url_for('login'))
    else:
        pass

@app.route("/groups",methods=['GET','POST'])
def GroupManagement():
    return render_template('GroupManagement.html')


if __name__ == "__main__":
	app.run(host='0.0.0.0',debug=True)