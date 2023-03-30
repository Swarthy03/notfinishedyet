from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
import time


class AddPostForm(Form):
    apost = TextAreaField("Ne göndermek istiyorsunuz?",validators=[validators.data_required(message="Lütfen geçerli alanı doldurunuz")])


class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.data_required(message="Lütfen geçerli alanı doldurunuz"),validators.length(min=5,max=50,message="En az 5 en fazla 50 karakter")])
    username = StringField("Kullanıcı Adı",validators=[validators.data_required(message="Lütfen geçerli alanı doldurunuz."),validators.length(min=5,max=15,message="En az 5 en fazla 15 karakter")])
    email = StringField("Email",validators=[validators.email(),validators.data_required(message="Lütfen geçerli alanı doldurunuz.")])
    password = PasswordField("Şifre",validators=[validators.equal_to(fieldname="confirmpassword",message="Parolanız uyuşmuyor."),validators.data_required(message="Lütfen geçerli alanı doldurunuz."),validators.length(min=5,max=15,message="En az 5 en fazla 15 karakter")])
    confirmpassword = PasswordField("Parola Doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı",validators=[validators.data_required(message="Lütfen geçerli alanı doldurunuz."),validators.length(min=5,max=15,message="En az 5 en fazla 15 karakter")])
    password = PasswordField("Şifre",validators=[validators.data_required(message="Lütfen geçerli alanı doldurunuz."),validators.length(min=5,max=15,message="En az 5 en fazla 15 karakter")])
    
app = Flask(__name__)

app.secret_key = 'some_secret'

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "socialmedia"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


@app.route('/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if session["logged_in"] == True and request.method == "POST":
        cur = mysql.connection.cursor()
        cur.execute("SELECT likes FROM posts where id = %s",(post_id,))
        current_likes = cur.fetchone()
        for i in current_likes.values():
            current_likes = i
        current_likes+=1
        cur.execute("UPDATE posts SET likes = %s where id = %s",(current_likes,post_id))
        mysql.connection.commit()
        return redirect(request.referrer)


@app.route("/",methods = ["POST","GET"])
def mainpage():
    if not "logged_in" in session.keys():
        session["logged_in"] = False
    if not "username" in session.keys():
        session["username"] = ""
    username = session["username"]
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM posts")
    liste = cur.fetchall()

    return render_template("mainpage.html",liste = liste)

@app.route("/register",methods=["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users where username = %s",(username,))
        a = cur.fetchall()
        if len(a) == 0:
            cur.execute("INSERT INTO users(name,username,email,password) VALUES(%s,%s,%s,%s)",(name,username,email,password))
            mysql.connection.commit()
            session["logged_in"] = True
            session["username"] = username
        else:
            flash("Fuck you dostum böyle bir kullanıcı adı zaten var")
            return redirect(url_for("register"))
        return redirect(url_for("mainpage"))
    return render_template("register.html",form=form)

@app.route("/login",methods = ["POST","GET"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password = form.password.data
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users where username = %s",(username,))
        a = cur.fetchall()
        if len(a) == 0:
            flash("Fuck you dostum böyle bir hesap yok")
        else:
            if sha256_crypt.verify(password,a[0]["password"]):
                session["logged_in"] = True
                session["username"] = username
                flash("Başarıyla giriş yaptınız")
                return redirect(url_for("mainpage"))
    return render_template("login.html",form=form)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("mainpage"))

@app.route("/message/<username>",methods = ["POST","GET"])
def messageto(username):
    if username == session["username"]:
        flash("Kendi kendine mesaj atmayı mı deniyon aq?")
        return redirect(url_for("mainpage"))
    cur = mysql.connection.cursor()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {session['username']+'to'+username}(sender TEXT,message TEXT,time TIMESTAMP DEFAULT CURRENT_TIMESTAMP())")
    mysql.connection.commit()
    cur.execute(f"CREATE TABLE IF NOT EXISTS {username+'to'+session['username']}(sender TEXT,message TEXT,time TIMESTAMP DEFAULT CURRENT_TIMESTAMP())")
    mesaj = request.form.get("mesaj")
    cur.execute(f"SELECT * FROM {session['username']+'to'+username}")
    mesajlar = cur.fetchall()
    cur.close()
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT * FROM {username+'to'+session['username']}")
    gelen_mesajlar = cur.fetchall()
    mesajlar = list(mesajlar)
    gelen_mesajlar = list(gelen_mesajlar)
    mesajlar.extend(gelen_mesajlar)
    mesajlar = sorted(mesajlar, key=lambda x: x['time'])
    print(mesajlar)
    if request.method == "POST":
        cur.execute("INSERT INTO {}(sender,message) values(%s,%s)".format(session["username"]+"to"+username),(session["username"],mesaj))
        mysql.connection.commit()
        cur.close()
        return redirect(f"/message/{username}")
    return render_template("dmto.html",biz = session["username"],username=username,mesajlar=mesajlar)

@app.route("/message",methods = ["GET","POST"])
def message():
    
    username = session["username"]
    cur = mysql.connection.cursor()
    cur.execute("SHOW TABLES LIKE %s",('%'+username+'to'+'%',))
    b = cur.fetchall()
    cur.close()
    c = []
    d = []
    for i in b:
        k = str(i.values())
        c.append(k.split("\'"))
    for i in c:
        if i[1].startswith(session["username"] + "to") == True:
            d.append(i[1][len(session["username"]+"to"):])
    if session["logged_in"] == False:
        flash("Önce giriş yapmanız gerekmekte.")
        return redirect(url_for("mainpage"))
    if request.method == "POST":
        username = session["username"]
        aranan = request.form.get("arama")
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users where username like %s",("%"+aranan+"%",))
        a = cur.fetchall()
        uzunluk = len(a)
        return render_template("dm.html",lastmessages = d,users = a,username = username,uzunluk = uzunluk)
    print(d)
    return render_template("dm.html",lastmessages = d,username = username)

@app.route("/addpost",methods = ["GET","POST"])
def addpost():
    form = AddPostForm(request.form)
    content = form.apost.data
    if request.method == "POST":
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO posts(username,post) values(%s,%s)",(session["username"],content))
        mysql.connection.commit()
    return render_template("addpost.html",form = form)

@app.route("/profile/<username>/<id>")
def profileposts(username,id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM posts where username = %s and id = %s",(username,id))
    a = cur.fetchone()
    if len(a) == 0:
        flash("Kardeşim böyle bir şey yok")
        return redirect(url_for("profileposts"))
    
    return render_template("profileposts.html",a=a)

if __name__ == "__main__":
    app.run(debug=True)