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

@app.route("/", methods = ["GET", "POST"])
def index():
    if 'user' in session:
        cursor = conn.cursor()
        query = "SELECT * FROM tag join contentitem ON (contentitem.item_id = tag.item_id) where email_tagged = (%s) and status = 'Pending'"
        cursor.execute(query,session['user'])
        data = cursor.fetchall()
        return render_template("index.html", tag_data = data)
    else:
        return render_template("index.html")

#update peding tags that users can accept or deny
@app.route("/tag", methods = ["POST"])
def tag():
    cursor = conn.cursor()
    tag_key = request.form.getlist('data[]')
    status = tag_key[3]
    tagger = tag_key[2]
    taggee = tag_key[1]
    itemid = tag_key[0]
    sql = "UPDATE tag SET status = (%s) WHERE item_id = (%s) AND email_tagger = (%s) AND email_tagged = (%s)"
    print(tagger, taggee, itemid)
    cursor.execute(sql,(status,itemid,tagger, taggee))
    conn.commit()
    cursor.close()
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

@app.route("/groups/friendAdd", methods=['POST'])
def addFriend():
    cursor = conn.cursor()
    fName = request.form['firstName']
    lName = request.form['lastName']
    fg_name = request.form['fg_name']
    try:
        sqlCount = "select count(distinct email) from person where fname = (%s) and lname = (%s)"
        cursor.execute(sqlCount, (fName,lName))
        count = cursor.fetchone()
        count = count[0] # reformat count
        sqlEmail = "select email from person where fname = (%s) and lname = (%s)"
        cursor.execute(sqlEmail, (fName, lName))
        friendID = cursor.fetchall()
    finally:
        if count == 0:
            msg = "there is no such a user with name " + fName + " " + lName
            cursor.close()
            return jsonify({"noUser":msg})

        sqlAlreadyIn = "select fname, lname, email from belong Natural join person where fname=(%s) and lname=(%s) and owner_email=(%s) and fg_name=(%s)"
        cursor.execute(sqlAlreadyIn,(fName,lName, session['user'], fg_name))
        alreadyIn = cursor.fetchall()

        if count == 1:
            if alreadyIn:
                msg = "user " + fName + " " + lName +" is already in this group"
                print("AlreadyIn")
                cursor.close()
                return jsonify({"alreadyIn":msg})
            else:
                print("not in")
                friendID = friendID[0]
                sqlInsert = "insert into belong (email, owner_email, fg_name) values (%s, %s, %s)"
                cursor.execute(sqlInsert, (friendID, session['user'], fg_name))
                conn.commit()
                cursor.close()
                msg ="Congratulation! user " + fName + " " + lName +" SUCCESSFULLY added!"
                return jsonify({"added":msg})
        else:
            return jsonify({"dup":friendID})


@app.route("/groups/defriend", methods=['DELETE'])
def deFriend():
    cursor = conn.cursor()
    fName = request.form['firstName']
    lName = request.form['lastName']
    fg_name = request.form['fg_name']
    print("deleteing")
    #amount of people with such name in target group
    sqlCount = "select count(distinct email) from person natural join belong where fname = (%s) and lname = (%s) and owner_email = (%s) and fg_name=(%s)"
    cursor.execute(sqlCount, (fName,lName, session["user"], fg_name))
    count = cursor.fetchone()
    count = count[0] # reformat count
    print("count: ",count)
    sqlEmail = "select email from person natural join belong where fname = (%s) and lname = (%s) and owner_email = (%s) and fg_name=(%s)"
    cursor.execute(sqlEmail, (fName, lName, session["user"], fg_name))
    friendID = cursor.fetchall()

    if count == 0:
        print("0")
        msg = "there is no such a user with name " + fName + " " + lName
        cursor.close()
        return jsonify({"noUser":msg})

    sqlAlreadyIn = "select fname, lname, email from belong Natural join person where fname=(%s) and lname=(%s) and owner_email=(%s) and fg_name=(%s)"
    cursor.execute(sqlAlreadyIn,(fName,lName, session['user'], fg_name))
    alreadyIn = cursor.fetchall()
    if count == 1:
        print("1")
        if not alreadyIn:
            msg = "user " + fName + " " + lName +" is already in this group"
            print("notIn")
            cursor.close()
            return jsonify({"notIn":msg})
        else: #delete user
            print("User is In")
            if friendID[0][0] == session["user"]:
                print("suicide")
                msg = "You can't do that! You are the Master of this group!"
                cursor.close()
                return jsonify({"suicide":msg})
            friendID = friendID[0]
            sqlDelete = "delete from belong (email, owner_email, fg_name) values (%s, %s, %s)"
            cursor.execute(sqlDelete, (friendID, session['user'], fg_name))
            conn.commit()
            cursor.close()
            msg ="All Right! user " + fName + " " + lName +" SADLY deleted!"
            return jsonify({"deleted":msg})
    else:
        return jsonify({"dup":friendID})

@app.route("/post/blog/<item_id>/comment",methods=['GET','POST'])
def comment(item_id):
    cursor = conn.cursor()
    if request.method == 'POST':
        content = request.form['comment']
        query = "INSERT into `comment`(`email`, `comment`, `item_id`) Values (%s,%s,%s)"
        cursor.execute(query,(session['user'],content,item_id))
        conn.commit()
        query = "SELECT fname, lname FROM Person where email=(%s)"
        cursor.execute(query,(session['user']))
        name = cursor.fetchone()
        cursor.close()
        return jsonify({'name':name,'comment':content})
    elif request.method == 'GET':
        print("hahah")
        query = "SELECT DISTINCT fname,lname,comment,email FROM comment JOIN person USING(email) where item_id=(%s)"
        cursor.execute(query,(item_id))
        data = cursor.fetchall()
        cursor.close()
        return jsonify({'data':data})

@app.route("/post/blog/<item_id>/tag",methods=['GET','POST'])
def posttag(item_id):
    cursor = conn.cursor()
    if request.method == 'POST':
        content = request.form['tag']
        taggee = []
        l = []
        for i in range(len(content)):
            if content[i] == '@' and i != 0:
                taggee.append(str(''.join(l)).strip())
                l = []
            elif content[i] == '@' and i == 0:continue
            else:l.append(content[i])
        taggee.append(str(''.join(l)).strip())
        #print(taggee);
        return 'hah'

@app.route("/gallery")
def renderGallery():
    return render_template("gallery.html")

@app.route("/post/gallery")
def gallery():
    cursor = conn.cursor()
    if 'user' in session:
        query = "SELECT DISTINCT file_path FROM contentItem JOIN share USING(item_id) JOIN belong ON(belong.owner_email = share.owner_email AND belong.fg_name = share.fg_name) WHERE belong.email = (%s) UNION all SELECT DISTINCT file_path FROM contentItem where is_pub = true"
        cursor.execute(query,session['user'])
    else:
        query = "SELECT file_path FROM contentItem where is_pub = true"
        cursor.execute(query)
    data = cursor.fetchall()
    return jsonify({'data':data})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
	app.run(host='0.0.0.0',debug=True)
