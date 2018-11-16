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

@app.route("/login",methods=['GET','POST'])
def login():
    if request.method == 'POST':
        pass
    else:
        return render_template("login.html")

@app.route("/signup",methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        pass
    else:
        return render_template("signup.html")

if __name__ == "__main__":
	app.run(host='0.0.0.0',debug=True)