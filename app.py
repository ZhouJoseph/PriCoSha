from flask import Flask, request, render_template,redirect,url_for,jsonify,session
app = Flask(__name__)
app.secret_key = 'this_is_supposed_to_be_secret'

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
	app.run(host='0.0.0.0',debug=True)