from flask import Flask, request, render_template,redirect,url_for,jsonify,session
import pymysql.cursors
import hashlib
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = '/img'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


app = Flask(__name__)
app.secret_key = 'this_is_supposed_to_be_secret'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

conn = pymysql.connect(host='127.0.0.1', user='pricosha', database='PriCoSha')

def encrypt(hash_str):
    return hashlib.sha256(hash_str.encode()).hexdigest()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def saveFile(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return (app.config['UPLOAD_FOLDER']+filename)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    error = request.args.get('error')
    return render_template("login.html",errors = error )

# Login users
@app.route("/login/user",methods=['GET','POST'])
def loginUser():
    email = request.form["email"]
    pwd = request.form["pwd"]
    cursor = conn.cursor()
    sql = "SELECT * FROM Person WHERE email=(%s) AND password=(%s)"
    cursor.execute(sql,(email,encrypt(pwd)))
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

# Sign up users
@app.route("/signup/user",methods=['GET','POST'])
def signUpUser():
    fname = request.form["fname"]
    lname = request.form["lname"]
    email = request.form["email"]
    pwd = request.form["pwd"]
    secPwd = request.form["2pwd"]
    result = None
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
            pwd = encrypt(pwd)
            sql = "INSERT INTO `person` (`email`,`password`,`fname`,`lname`) VALUES (%s,%s,%s,%s)"
            cursor.execute(sql,(email,pwd,fname,lname))
            conn.commit()
            cursor.close()
            session['user'] = email
            return redirect(url_for('post'))
        else:
            msg = "User Already Exist"
            return redirect(url_for('signup',error=msg))

# Render template for post page
@app.route("/post",methods=['GET'])
def post():
    if 'user' in session:
        # fake data for groups
        session['groups']=['first-group','second-group']
        return render_template('post.html',email=session['user'])
    else:
        return render_template('post.html',email="Visitor")

# Posting a blog 
@app.route("/post/posting",methods=['POST'])
def postBlog():

    content = request.form["content"]
    # file = request.form["file"]
    # file_path = saveFile(file)
    file_path = "No File Path Chosen Yet"
    cursor = conn.cursor()
    query = 'INSERT INTO `contentitem`(`email_post`,`file_path`,`item_name`) VALUES(%s,%s,%s)'
    cursor.execute(query,(session['user'],file_path,content))
    conn.commit()
    id = cursor.lastrowid
    query = 'SELECT email_post, post_time, item_name, file_path,item_id FROM contentitem WHERE item_id = (%s)'
    cursor.execute(query,id)
    data = cursor.fetchone()
    return jsonify({'data':data})

# Fetching the viewable blogs
@app.route("/post/blog")
def fetchBlogs():
    if 'user' in session:      
        cursor = conn.cursor()
        query = 'SELECT email_post, post_time, item_name, file_path,item_id FROM contentitem WHERE email_post = (%s) ORDER BY post_time DESC'
        cursor.execute(query,session['user'])
        data = cursor.fetchall()
        cursor.close()
        return jsonify({'data':data})
    else:
        cursor = conn.cursor()
        query = 'SELECT email_post, post_time, item_name, file_path,item_id FROM contentitem WHERE is_pub = true AND post_time>=DATE_SUB(NOW(), INTERVAL 1 DAY) ORDER BY post_time DESC'
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        return jsonify({'data':data})

# Fetching detailed info of a specific blog
@app.route("/post/blog/<item_id>")
def detailedBlog(item_id):
    cursor = conn.cursor()

    # content of a post
    contentItem = 'SELECT * FROM contentitem WHERE item_id = (%s)'
    cursor.execute(contentItem,item_id)
    content = cursor.fetchone()

    # taggee of a post
    tag = 'SELECT fname,lname FROM person JOIN Tag ON (Tag.email_tagged = person.email) WHERE Tag.item_id = (%s) AND Tag.status=true'
    cursor.execute(tag,item_id)
    taggee = cursor.fetchall()

    # rating of a post
    rate = 'SELECT email, rate_time, emoji FROM rate where item_id = (%s)'
    cursor.execute(rate,item_id)
    rating = cursor.fetchall()
    cursor.close()
    
    return jsonify({'content':content,'tag':taggee,'rate':rating})


@app.route("/groups")
def GroupManagement():
    # Faking Data
    session['groups'] = [
        {
            'name':"Database study group",
            'description': "Three desperate people..."
        },
        {
            'name':"fake group",
            'description':"fake description..."
        }
    ]
    return render_template('GroupManagement.html',email=session['user'], groups=session['groups'])

@app.route("/groups/fetch")
def groupFetch():
    if 'user' in session:
        cursor = conn.cursor()
        query = 'select belong.fg_name as name, belong.owner_email as owner from belong where belong.email = (%s)'
        cursor.execute(query,session['user'])
        data = cursor.fetchall()
        cursor.close()
        return jsonify({'data':data})
    else:
        '''log in first'''
    '''
        Do Stuff Here
        1. Connect to DB Check!
        2. Select the groups I belong to From DB Check!
        3. Remember to commit and close Check!
        4. Return jsonify(fetching result) Check!
    '''

    return "How About This"

@app.route("/groups/create",methods=['POST'])
def createGroup():
    cursor = conn.cursor()
    fg_name = request.form['groupname']
    description = request.form['description']
    result = None
    try:
        sql = "select * from friendgroup where owner_email = (%s) and fg_name = (%s)"
        cursor.execute(sql, (email), (fgname))
        result = cursor.fetchone()
    finally:
        if not result:
            sql = "insert into friendgroup(owner_email, fg_name, description) Values (%s,%s,%s)"
            cursor.execute(sql, (session['user'], fg_name, description))
            sql = "insert into belong(email, owner_email, fg_name) Values (%s,%s,%s)"
            cursor.execute(sql, (session['user'], session['user'], fg_name))
            conn.commit()
            cursor.close()
            return jsonify({'name': fg_name, 'description': description})
        else:
            msg = "Group Already Exist"
            return redirect(url_for('GroupManagement', error=msg))
    '''
        Do Stuff Here
        1. Connect to DB Check!
        2. Insert into DB Check!
        3. Remember to commit and close Check!
        4. You don't need to handle errors. There are a little bit more you need to know before you do that OK!
        5. SQL Instruction:
            5.1 fg_name and owner_email are the composite primary key  Check!
            5.2 After inserting, plz commit!!!  Check!
            
            ?***********************************************************************************************?
            ?5.3 Don't need redirect here, only return the value that needs to be displayed in the front-end?
            ?***********************************************************************************************?
            You right, we need to return group already exist
    '''
    # Return statement is for updating UI using AJAX
    return jsonify({'name':fg_name, 'description':description})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
	app.run(host='0.0.0.0',debug=True)
