from flask import Flask, request, render_template,redirect,url_for,jsonify,session
import pymysql.cursors

app = Flask(__name__)
app.secret_key = 'this_is_supposed_to_be_secret'

def connectDB():
    conn = pymysql.connect(host='127.0.0.1', user='pricosha', database='PriCoSha')
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/login/user",methods=['POST'])
def loginUser():
    email = request.form["email"]
    pwd = request.form["pwd"]
    session['user'] = email
    return redirect(url_for('post'))

@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/signup/user",methods=['POST'])
def signUpUser():
    fname = request.form["fname"]
    lname = request.form["lname"]
    email = request.form["email"]
    pwd = request.form["pwd"]
    conn = connectDB()
    result = []
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM person WHERE email=(%s)"
            cursor.execute(sql,(email))
            result = cursor.fetchone()
            if not result:
                sql = "INSERT INTO `person` (`email`,`password`,`fname`,`lname`) VALUES (%s,%s,%s,%s)"
                cursor.execute(sql,(email,pwd,fname,lname))
    finally:
        conn.commit()
        conn.close()
        if result is None:
            session['user'] = email
            return redirect(url_for('post'))
        else:
            return 505


    session['user'] = email
    return redirect(url_for('post'))

@app.route("/post",methods=['GET','POST'])
def post():
    if request.method == 'GET':
        if 'user' in session:
            return render_template('post.html',email=session['user'])
        else:
            return redirect(url_for('login'))
    else:
        pass


if __name__ == "__main__":
	app.run(host='0.0.0.0',debug=True)