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

def checkUser():
    if 'user' not in session:
        return redirect(url_for('login',error="you must login to access that page"))

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
    query = "SELECT is_pub from contentitem where item_id = (%s)"
    cursor.execute(query,(item_id))
    result = cursor.fetchone()
    if not result:
        return render_template('content.html',item="You don't have access to this blog",tag='', rate='',file='')
    data = int(result[0])
    if data == 0:
        user = ''
        if 'user' in session:
            query = "SELECT fg_name, owner_email from contentitem JOIN share using (item_id) JOIN belong using(owner_email,fg_name) where item_id = (%s) and email = (%s)"
            cursor.execute(query,(item_id,session['user']))
            user = cursor.fetchone()
        else:
            return redirect(url_for('login',error="It's a private blog, you must login first"))
        if user is None:
            return render_template('content.html',item="False",tag='', rate='',file='')

    # content of a post
    contentItem = 'SELECT * FROM contentitem WHERE item_id = (%s)'
    cursor.execute(contentItem,item_id)
    content = cursor.fetchone()

    # taggee of a post
    tag = 'SELECT fname,lname FROM person JOIN Tag ON (Tag.email_tagged = person.email) WHERE Tag.item_id = (%s) AND Tag.status=true'
    cursor.execute(tag,item_id)
    taggee = cursor.fetchall()
    tagger = 'SELECT fname,lname FROM person JOIN Tag ON (Tag.email_tagger = person.email) WHERE Tag.item_id = (%s) AND Tag.status=true'
    cursor.execute(tagger,item_id)
    tagger = cursor.fetchall()
    tag = [taggee,tagger]
    result = []
    for t in taggee:
        result.append([t])
    counter = 0
    for t in tagger:
        result[counter].append(t)
        counter += 1



    # rating of a post
    rate = 'SELECT email, rate_time, emoji FROM rate where item_id = (%s)'
    cursor.execute(rate,item_id)
    rating = cursor.fetchall()
    cursor.close()
    return render_template('content.html',item=content,tag=result, rate=rating,file=content[3])


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
    print('fetching');
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
    print("in addFriend")

    '''# of people with such name not in group'''
    sqlCount = "select count(*) from (select email from person where fname = (%s) and lname = (%s) and email Not In (select email from belong where owner_email = (%s) and fg_name = (%s))) as T"
    cursor.execute(sqlCount, (fName,lName, session['user'], fg_name))
    count = cursor.fetchone()
    count = count[0] # reformat count
    print("Count: ", count)

    sqlEmail = "select email from person where fname = (%s) and lname = (%s) and email Not In (select email from belong where owner_email = (%s) and fg_name = (%s))"
    cursor.execute(sqlEmail, (fName, lName, session['user'], fg_name))
    friendID = cursor.fetchall()
    print("FriendID: ", friendID)

    sqlAlreadyIn = "select * from belong Natural join person where fname=(%s) and lname=(%s) and owner_email=(%s) and fg_name=(%s)"
    cursor.execute(sqlAlreadyIn,(fName,lName, session['user'], fg_name))
    alreadyIn = cursor.fetchall()

    if count > 1:
        return jsonify({"dup": friendID})

    if count == 1:
        print("not in")
        friendID = friendID[0]
        sqlInsert = "insert into belong (email, owner_email, fg_name) values (%s, %s, %s)"
        cursor.execute(sqlInsert, (friendID, session['user'], fg_name))
        conn.commit()
        cursor.close()
        msg ="Congratulation! user " + fName + " " + lName +" SUCCESSFULLY added!"
        return jsonify({"added":msg})

    if alreadyIn:
        msg = "user " + fName + " " + lName + " is already in this group"
        print("AlreadyIn")
        cursor.close()
        return jsonify({"alreadyIn": msg})

    if count == 0:
        msg = "there is no such a user with name " + fName + " " + lName
        cursor.close()
        return jsonify({"noUser":msg})




@app.route("/groups/friendAddWithEmail", methods = ['POST'])
def addFriendWithEmail():
    print("in addFriendWithEmail")
    cursor = conn.cursor()
    fName = request.form['firstName']
    lName = request.form['lastName']
    fg_name = request.form['fg_name']
    email = request.form['email']
    print(fName, lName)
    #check if input email is valid

    sqlCheck = "select email from person where fname =(%s) and lname = (%s) and email not in (select email from belong where owner_email = (%s) and fg_name = (%s))"
    cursor.execute(sqlCheck, (fName, lName, session['user'], fg_name))
    available = cursor.fetchall()
    for i in range(len(available)):
        if available[i][0] == email: # a valid input
            sqlInsert = "insert into belong (email, owner_email, fg_name) values (%s, %s, %s)"
            cursor.execute(sqlInsert, (email, session['user'], fg_name))
            conn.commit()
            cursor.close()
            msg = "Congratulation! user " + fName + " " + lName + " SUCCESSFULLY added!"
            return jsonify({"added": msg})
    msg = "Invalid Email. Be careful PLEASE!"
    cursor.close()
    return jsonify({"failed":msg})

@app.route("/groups/defriend", methods=['DELETE'])
def deFriend():
    cursor = conn.cursor()
    fName = request.form['firstName']
    lName = request.form['lastName']
    fg_name = request.form['fg_name']
    print("deleteing")
    #amount of people with such name in target group except self
    sqlCount = "select count(email) from person natural join belong where fname = (%s) and lname = (%s) and owner_email = (%s) and fg_name=(%s) and email not in (%s)"
    cursor.execute(sqlCount, (fName,lName, session["user"], fg_name, session['user']))
    count = cursor.fetchone()
    count = count[0] # reformat count
    print("count: ",count)
    #email of people with target name in group except self
    sqlEmail = "select email from person natural join belong where fname = (%s) and lname = (%s) and owner_email = (%s) and fg_name=(%s) and email not in (%s)"
    cursor.execute(sqlEmail, (fName, lName, session["user"], fg_name, session["user"]))
    friendID = cursor.fetchall()
    print("FINAL STEP??? of course not")
    if count == 0:
        print("0")
        msg = "there is no such a user with name " + fName + " " + lName + " in this group. btw, you can't delete youself"
        cursor.close()
        return jsonify({"noUser":msg})

    sqlAlreadyIn = "select fname, lname, email from belong Natural join person where fname=(%s) and lname=(%s) and owner_email=(%s) and fg_name=(%s)"
    cursor.execute(sqlAlreadyIn,(fName,lName, session['user'], fg_name))
    alreadyIn = cursor.fetchall()
    if count == 1:
        print("1")
 #delete user
        print("User is In")
        if friendID[0][0] == session["user"]:
            print("suicide")
            msg = "You can't do that! You are the Master of this group!"
            cursor.close()
            return jsonify({"suicide":msg})
        friendID = friendID[0][0]
        sqlDelete = "delete from belong where email = (%s) and owner_email = (%s) and fg_name = (%s)"
        cursor.execute(sqlDelete, (friendID, session['user'], fg_name))
        conn.commit()
        cursor.close()
        msg ="All Right! user " + fName + " " + lName +" SADLY deleted!"
        return jsonify({"deleted":msg})
    else:
        return jsonify({"dup":friendID})

@app.route("/groups/friendDeleteWithEmail", methods = ['Delete'])
def deFriendWithEmail():
    print("in Delete FriendWithEmail")
    cursor = conn.cursor()
    fName = request.form['firstName']
    lName = request.form['lastName']
    fg_name = request.form['fg_name']
    email = request.form['email']
    print(fName, lName)
    #check if input email is valid
    sqlCheck = "select email from person natural join belong where fname = (%s) and lname = (%s) and owner_email = (%s) and fg_name=(%s) and email not in (%s)"
    cursor.execute(sqlCheck, (fName, lName, session['user'], fg_name, session['user']))
    available = cursor.fetchall()
    print("Given: ", email)
    for i in range(len(available)):
        print("checking ", available[i][0])
        if available[i][0] == email: # a valid input
            print("A valid email!")
            sqlInsert = "delete from belong where email = (%s) and owner_email = (%s) and fg_name = (%s)"
            cursor.execute(sqlInsert, (email, session['user'], fg_name))
            conn.commit()
            cursor.close()
            msg = "All Right! user " + fName + " " + lName +" SADLY deleted!"
            return jsonify({"deleted": msg})
    msg = "Invalid Email. Be careful PLEASE!"
    cursor.close()
    return jsonify({"failed":msg})


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
        members = []

        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

        for i in range(len(content)):
            if content[i] == '@' and i != 0:
                taggee.append(str(''.join(l)).strip())
                l = []
            elif content[i] == '@' and i == 0:continue
            else:l.append(content[i])
        taggee.append(str(''.join(l)).strip())

        sql1 = "SELECT `email` FROM person WHERE `fname` = (%s) AND `lname` = (%s)"      #find taggee's email
        sql2 = "INSERT into `tag`(`email_tagged`, `email_tagger`, `item_id`, `status`, `tagtime`) Values (%s, %s, %s, %s, %s)"
        sql3 = "SELECT `email_tagged`, `email_tagger`, `item_id` FROM `tag`"
        status = isPublic(cursor, item_id)
        print("status", status)
        if status == 1:
            sql = "SELECT email FROM person"
            cursor.execute(sql)
            members = cursor.fetchall()
        else:
            members = ContentSharedGroup(cursor, item_id)
        msg = 'Tagged!'
        dup_name = False
        dup_id = ''
        repeated = False

        for i in taggee:
            #print('user: '+ session['user'])
            space_index = taggee[0].find(' ')
            #print(taggee[0][0 : space_index], taggee[0][space_index+1 : ])
            cursor.execute(sql1, (taggee[0][0 : space_index], taggee[0][space_index+1 : ]))
            taggees_email = cursor.fetchall()
            #print(taggees_email)
            for j in taggees_email:
                cursor.execute(sql3)
                data = cursor.fetchall()
                print("dup data", data)
                newData = (j[0], session['user'], int(item_id))
                print(type(newData))
                repeated = False
                if len(taggees_email) > 1:
                    dup_name = True
                    dup_id = taggees_email
                    msg = 'multiple people with same name D:'
                else:
                    for i in data:
                        if ((i[0] == newData[0]) and (i[1] == newData[1]) and (i[2] == newData[2])):
                            repeated = True
                    print(repeated)
                    test = False
                    print(members)
                    for member in members:
                        print(j[0], member, '\n')
                        if member[0] == j[0]:
                            test = True
                    print(test)
                    if repeated == False and test:
                        if j[0] == session['user']:
                            cursor.execute(sql2, (j[0], session['user'], item_id, 1, timestamp))
                            conn.commit()
                        else:
                            print('WHYYYYYYYYYY')
                            cursor.execute(sql2, (j[0], session['user'], item_id, 'Pending', timestamp))
                            conn.commit()
                        msg = "Tagged!"
                    else:
                        msg = 'Sorry you cannot do this :('
        cursor.close()
        print("msg1", msg)
        return jsonify({"msg":msg, "repeated": repeated, "dup_name":dup_name, "dup_id":dup_id})

@app.route("/post/blog/<item_id>/tagEmail",methods=['GET','POST'])
def tagEmail(item_id):
    msg = 'Tagged!'
    email = request.form['tag']
    cursor = conn.cursor()
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    status = isPublic(cursor, item_id)
    members = []
    print("status", status)
    if status == 1:
        sql = "SELECT email FROM person"
        cursor.execute(sql)
        members = cursor.fetchall()
    else:
        members = ContentSharedGroup(cursor, item_id)
    sql = "SELECT * FROM `tag` WHERE email_tagged = (%s) AND email_tagger = (%s) AND item_id = (%s)"
    sql2 = "INSERT into `tag`(`email_tagged`, `email_tagger`, `item_id`, `status`, `tagtime`) Values (%s, %s, %s, %s, %s)"
    print("email, members: ", email, members)
    test = False
    for member in members:
        if member[0] == email:
            test = True
    if test:
        print("HEREEEEEEEEEE")
        cursor.execute(sql, (email, session['user'], item_id))
        dup = cursor.fetchall()
        print(dup)
        if len(dup) == 0:
            print("NOOOOOOOOOOOOOOO")
            cursor.execute(sql2, (email, session['user'], item_id, 'Pending', timestamp))
            conn.commit()
            msg = "Tagged"
        else:
            msg = 'Sorry you cannot do this'
    else:
        msg = 'Sorry you cannot do this:('

    print("msg2", msg)
    return msg

def isPublic(cursor, item_id):
    sql = "SELECT is_pub FROM contentitem WHERE item_id = (%s)"
    cursor.execute(sql, item_id)
    status = cursor.fetchone()
    print(status)
    return status[0]


def ContentSharedGroup(cursor, item_id):
    sql = "SELECT `fg_name` FROM share WHERE item_id = (%s)"
    cursor.execute(sql, item_id)
    sharedGroup = cursor.fetchall()
    people = PeopleInGroup(cursor, sharedGroup) #People who have access to blog content
    return people

def PeopleInGroup(cursor, sharedGroup):
    sql = "SELECT `email` FROM belong WHERE `fg_name` = (%s)"
    res = []
    for group in sharedGroup:
        cursor.execute(sql, group[0])
        data = cursor.fetchall();
        for i in data:
            if i[0] not in res:
                res.append(i[0])
    print('res', res)
    return res






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
