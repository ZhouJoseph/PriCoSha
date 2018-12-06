from flask import Flask, request, render_template,redirect,url_for,jsonify,session
import pymysql.cursors
import hashlib
import os
import time
import datetime
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.getcwd()+'/static/img/'
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
        filename = secure_filename(session['user']+file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return os.path.join("/static/img", filename)

def getGroups(email):
    cursor = conn.cursor()
    query = "SELECT owner_email, fg_name FROM belong where email=(%s)"
    cursor.execute(query,email)
    groups = cursor.fetchall()
    cursor.close()
    return groups

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
@app.route("/post")
def post():
    if 'user' in session:
        session['groups']=getGroups(session['user'])
        return render_template('post.html',email=session['user'],groups=session['groups'])
    else:
        return render_template('post.html',email="Visitor")


def postContent(email_post,post_time,file_path,item_name,is_pub,groups=[]):
    cursor = conn.cursor()
    query = 'INSERT INTO `contentitem`(`email_post`,`post_time`,`file_path`,`item_name`,`is_pub`) VALUES(%s,%s,%s,%s,%s)'
    cursor.execute(query,(email_post,post_time,file_path,item_name,is_pub))
    conn.commit()
    id = cursor.lastrowid
    query = 'SELECT email_post, post_time, item_name, file_path,item_id FROM contentitem WHERE item_id = (%s)'
    cursor.execute(query,id)
    data = cursor.fetchone()
    counter = 0
    sharedGroup = []
    for shared in groups:
        if shared == True:
            sharedGroup.append(session['groups'][counter])
            counter+=1
        else:
            counter+=1
    for shared in sharedGroup:
        query = 'INSERT INTO `share`(`owner_email`,`fg_name`,`item_id`) VALUES(%s,%s,%s)'
        cursor.execute(query,(shared[0],shared[1],id))
        conn.commit()
    cursor.close()
    return data

# Posting a blog
@app.route("/post/posting/public",methods=['POST'])
def postBlog():
    is_pubB = True
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    try:
        upload_file = request.files['file']
        content = request.form["content"]
        file_path = saveFile(upload_file)
        data = postContent(session['user'],timestamp,file_path,content,is_pubB)
        return jsonify({'data':data})
    except:
        content = request.form["content"]
        data = postContent(session['user'], timestamp, 'none', content, is_pubB)
        return jsonify({'data':data})

@app.route("/post/posting/private",methods=['POST'])
def postPrivateBlog():
    content = request.form["content"]
    is_pubB = False
    groups = request.form["group"]
    groups = groups.split(",")
    print(groups)
    groups = [True if int(i) == 1 else False for i in groups]
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    try:
        upload_file = request.files['file']
        file_path = saveFile(upload_file)
        data = postContent(session['user'],timestamp,file_path,content,is_pubB,groups)
        return jsonify({'data':data})
    except:
        data = postContent(session['user'],timestamp,'none',content,is_pubB,groups)
        return jsonify({'data':data})


# Fetching the viewable blogs
@app.route("/post/blog")
def fetchBlogs():
    if 'user' in session:
        cursor = conn.cursor()
        query = 'SELECT DISTINCT * FROM(SELECT email_post, post_time, item_name, file_path, item_id FROM contentitem WHERE is_pub = true AND post_time>=DATE_SUB(NOW(), INTERVAL 1 DAY) UNION all SELECT email_post, post_time, item_name, file_path, item_id FROM belong JOIN share USING(owner_email,fg_name) JOIN contentitem USING(item_id) WHERE email = (%s)) a ORDER BY post_time DESC;'
        cursor.execute(query,session['user'])
        data = cursor.fetchall()
        cursor.close()
        return jsonify({'data':data})
    else:
        cursor = conn.cursor()
        query = 'SELECT email_post, post_time, item_name, file_path, item_id FROM contentitem WHERE is_pub = true AND post_time>=DATE_SUB(NOW(), INTERVAL 1 DAY) order by post_time DESC'
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        return jsonify({'data':data})

# Fetching detailed info of a specific blog
@app.route("/post/blog/<item_id>")
def detailedBlog(item_id):
    cursor = conn.cursor()

    # we need to check if the current user have access to this page or not.

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
    return render_template('content.html',item=content,tag=taggee,rate=rating,file=content[3])


@app.route("/groups")
def GroupManagement():
    if 'user' in session:
        error = request.args.get('error')
        return render_template('GroupManagement.html',errors = error)
    else:
        msg = "You need to log in first"
        return redirect(url_for('login',error=msg))

@app.route("/groups/fetch")
def groupFetch():
    if 'user' in session:
        cursor = conn.cursor()
        query = 'select belong.fg_name,friendgroup.description,belong.owner_email from belong join friendgroup using(owner_email,fg_name) where belong.email = (%s)'
        cursor.execute(query,session['user'])
        data = cursor.fetchall()
        cursor.close()
        return jsonify({'data':data,'user':session['user']})
    else:
        msg = "You need to log in first"
        return redirect(url_for('login',error=msg))

@app.route("/groups/create",methods=['GET','POST'])
def createGroup():
    cursor = conn.cursor()
    fg_name = request.form['groupname']
    description = request.form['description']
    result = None
    try:
        sql = "select * from friendgroup where owner_email = (%s) and fg_name = (%s)"
        cursor.execute(sql, (session['user'],fg_name))
        result = cursor.fetchone()
    finally:
        if not result:
            sql = "insert into friendgroup(owner_email, fg_name, description) Values (%s,%s,%s)"
            cursor.execute(sql, (session['user'], fg_name, description))
            sql = "insert into belong(email, owner_email, fg_name) Values (%s,%s,%s)"
            cursor.execute(sql, (session['user'], session['user'], fg_name))
            conn.commit()
            cursor.close()
            return jsonify({'fg_name': fg_name, 'owner':session['user'], 'description': description})
        else:
            msg = "Group Already Exist"
            return redirect(url_for('GroupManagement', error=msg))
    # Return statement is for updating UI using AJAX
    return jsonify({'name':fg_name, 'description':description})
            #return redirect(url_for('GroupManagement',error=msg))

    '''Add friend should be a option following each group description in your groups page
        clicking on the option will pop up a user search by email address'''

@app.route("/groups/friendAdd", methods=['get','post'])
def addFriend(ownerID, fg_name):
    cursor = conn.cursor()
    fName = request.form["fName"]
    lName = request.form["lName"]
    text = document.getElementById('')

    try:
        sqlCount = "select count(distinct email) from person where fname = (%s) and lname = (%s)"
        cursor.execute(sqlCount, (fName,lName))
        count = cursor.fetchone()
        sqlEmail = "select email from person where fname = (%s) and lname = (%s)"
        cursor.execute(sqlEmail, (fName, lName))
        friendID = cursor.fetchone()
        sqlAlreadyIn = "select * from belong join person on (email) where fname=(%s) and lname=(%s) and owner_email=(%s) and fg_name=(%s)"
        cursor.execute(sqlAlreadyIn,(fName,lName,"ownerEmail", 'fg_name'))
        alreadyIn = cursor.fetchone()

    finally:
        if (count and count[0] > 1):
            '''duplicated name, further request of email address'''
        elif (not alreadyIn) and friendID:
            sqlInsert = "insert into belong (email, owner_email, fg_name) values (%s, %s, %s)"
            cursor.execute(sqlInsert, (friendID, ownerID, fg_name))
            conn.commit()
            cursor.close()
            return """Updata group"""
        elif (alreadyIn):
            msg = "Friend Already in Group"
            return '''Error Message'''
        else:
            msg = "Invalid Friend Email"
            return '''Error Message'''

def deFriend(ownerID, fg_name):
    cursor = conn.cursor()
    fName = request.form["fName"]
    lName = request.form["lName"]
    try:
        sqlCount = "select count(distinct email) from person join belong on (email) where fname = (%s) and lname = (%s)"
        cursor.execute(sqlCount, (fName,lName))
        count = cursor.fetchone()
        sqlEmail = "select email from person where fname = (%s) and lname = (%s)"
        cursor.execute(sqlEmail, (fName, lName))
        friendID = cursor.fetchone()
        sqlAlreadyIn = "select * from belong join person on (email) where fname=(%s) and lname=(%s) and owner_email=(%s) and fg_name=(%s)"
        cursor.execute(sqlAlreadyIn,(fName,lName,"ownerEmail", 'fg_name'))
        alreadyIn = cursor.fetchone()

    finally:
        if (count and count[0] > 1):
            '''duplicated name, further request of email address'''
        elif (alreadyIn) and friendID:
            sqldelete = "delete from belong where email=(%s) and owner_email=(%s) and fg_name=(%s)"
            cursor.execute(sqlDelete, (friendID, ownerID, fg_name))
            conn.commit()
            cursor.close()
            return """Updata group"""
        elif (not alreadyIn):
            msg = "Person not in Group"
            return '''Error Message'''
        else:
            msg = "Invalid Friend Email"
            return '''Error Message'''


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
	app.run(host='0.0.0.0',debug=True)
