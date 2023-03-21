import os
import re


from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, ordinal

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///diary.db")



# db = connection.cursor()
#session["friends_id"] = ""

@app.route("/")
@login_required
def index():
    """Show welcome and recent entries, status etc."""
    today = db.execute("SELECT entryid FROM entries WHERE date(date) = (SELECT date('now'));")
    amount = db.execute("SELECT COUNT(entry) FROM entries WHERE id = :i", i=session["user_id"])[0]["COUNT(entry)"]
    return render_template("index.html", username=session["user_id"], amount=amount, today=today)


@app.route("/new", methods=["GET", "POST"])
@login_required
def new():
    """New Entries"""
    amount = db.execute("SELECT entrieseverexisted FROM users WHERE id = :i", i=session["user_id"])[0]["entrieseverexisted"]
    if request.method == "POST":
        title = request.form.get("title")
        entry = request.form.get("entry")
        # if no title, replace with /
        if not title:
            title = "/"
            print("Replaced empty title with '/'")
        u = session["user_id"]
        # insert
        db.execute("UPDATE users SET entrieseverexisted = entrieseverexisted + 1 WHERE id = :i", i=session["user_id"])
        print("Updated entry count.")
        db.execute("INSERT INTO entries (id, entry, title) VALUES (:i, :e, :t)", i=u, e=entry, t=title)
        print("Entry inserted.")
        return redirect("/entries")
    return render_template("new.html", amount=ordinal(amount + 1))


@app.route("/entries", methods=["GET", "POST"])
@login_required
def entries():
    """Show existing entries"""
    # sorted according to time
    if request.method == "POST":
        if request.form.get("delete"):
            db.execute("DELETE FROM entries WHERE id = :u AND entryid = :e", u=session["user_id"], e=request.form.get("delete"))
            print("Entry deleted.")
            return redirect("/entries")
        elif request.form.get("sort"):
            db.execute("UPDATE users SET sort = :s WHERE id = :u", s=request.form.get("sort"), u=session["user_id"])
            print("Sort preference updated to" + request.form.get("sort"))
        elif request.form.get("view"):
            entry = db.execute("SELECT * FROM entries WHERE entryid = :e", e=request.form.get("view"))
            return render_template("view.html", entry=entry[0])

    # if GET
    if db.execute("SELECT sort FROM users WHERE id = :u", u=session["user_id"])[0]["sort"] == "DESC":
        table = db.execute("SELECT * FROM entries WHERE id = :u ORDER BY date ASC", u=session["user_id"])
    else:
        table = db.execute("SELECT * FROM entries WHERE id = :u ORDER BY date DESC", u=session["user_id"])
    return render_template("entries.html", entries=table)


@app.route("/entries/edit", methods=["GET", "POST"])
@login_required
def edit():
    if request.method == "POST":
        i = request.form.get("submit")
        db.execute("UPDATE entries SET title = :t, entry = :e WHERE entryid = :u;", t=request.form.get("title"), e=request.form.get("entry"), u=i)
        print("Entry edited.")
        return redirect("/entries")
    i = request.args.get("edit")
    return render_template("edit.html", row=db.execute("SELECT * FROM entries WHERE entryid = :e", e=i))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # done by javascript disable

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        print("Logged in" + session["username"] + ", ID" + session["username"])
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    print("Logging out " + session["username"] + ", ID" + session["username"])
    # Forget any user_id
    session.clear()
    print("Done.")
    # Redirect user to login form
    return redirect("/")


@app.route("/friends", methods=["GET", "POST"])
@login_required
def friends():
    """Add and view friends"""
    if request.method == "POST":
        search = request.form.get("username")
        add = request.form.get("addfriend")
        if add:
            # add friend
            db.execute("INSERT INTO friends (main_id, friend_id) VALUES (:i, :f)", i=session["user_id"], f=add)
            return redirect("/friends")
        d = "%" + search + "%"
        # error check

        if search != session["username"]:
            try:
                # search
                if db.execute("SELECT sort FROM users WHERE id = :u", u=session["user_id"])[0]["sort"] == "DESC":
                    results = db.execute("SELECT * FROM users WHERE username LIKE :d", d=d)
                else:
                    results = db.execute("SELECT * FROM users WHERE username LIKE :d", d=d)
                    # loop added
                for friend in results:
                    if friend["status"] == "PRIV":
                        results.remove(friend)
                # select the user whose id is in the friend list of current user, to check if he is a friend
                added = db.execute("SELECT * FROM friends WHERE friend_id = :f AND main_id = :u", f=friend['id'], u=session["user_id"])
                friend.update({"added": added})
                return render_template("friends.html", friends = results)
            except:
                return apology("user does not exist")
        else:
            return apology("you are searching for yourself dude")



    if db.execute("SELECT sort FROM users WHERE id = :u", u=session["user_id"])[0]["sort"] == "DESC":
        friends = db.execute("SELECT id, username FROM users WHERE id IN (SELECT friend_id FROM friends WHERE main_id = :u) ORDER BY id DESC", u=session["user_id"])
    else:
        friends = db.execute("SELECT id, username FROM users WHERE id IN (SELECT friend_id FROM friends WHERE main_id = :u) ORDER BY id ASC", u=session["user_id"])

    return render_template("searchfriend.html", friends = friends)



@app.route("/friends/friendsdiary", methods=["GET", "POST"])
@login_required
def friends_diary():
    if request.method == "POST":
        session["friend_id"] = request.form.get("viewfriend")
    elif not session["friend_id"]:
        return apology("you don't come here this way...")

    if db.execute("SELECT sort FROM users WHERE id = :u", u=session["friend_id"])[0]["sort"] == "DESC":
        table = db.execute("SELECT * FROM entries WHERE id = :u ORDER BY id DESC", u=session["friend_id"])
    else:
        table = db.execute("SELECT * FROM entries WHERE id = :u ORDER BY id DESC", u=session["friend_id"])

    return render_template("friendsdiary.html", table = table)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        pw = request.form.get("password")
        un = request.form.get("username")
        # Ensure username was unique
        if db.execute("SELECT username FROM users WHERE username = :username", username=un):
            return apology("username is already taken", 403)
        elif re.search(" ", un):
            return apology("username must not contain spaces")
        # Ensure password was up to specs
        elif len(un) > 15 :
            return apology("username is limited to 15 characters")
        # database
        db.execute("INSERT INTO users ('username', 'hash', 'length') VALUES (:u, :p, :l)",
                   u=un, p=generate_password_hash(pw), l=len(pw))
        # Remember which user has logged in
        session["user_id"] = db.execute("SELECT id FROM users WHERE username = :username",
                                        username=un)[0]["id"]
        session["username"] = un

        # setting status of user, by default its public
        status = request.form.get("status")
        if status == "PRIV":
             db.execute("UPDATE users SET status = :s WHERE id = :u", s = status, u = session["user_id"])

        # Redirect user to home page
        return redirect("/")
    return render_template("register.html")


@app.route("/advice", methods=["GET", "POST"])
@login_required
def advice():
    """Ask for advice"""
    if request.method == "POST":
        # is it a post or comment
        return
    return render_template("advice.html")


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    status = db.execute("SELECT status FROM users WHERE id = :i", i=session["user_id"])
    if request.method == "POST":
        un = request.form.get("changeun")
        pw = request.form.get("changepw")
        if request.form.get("status"):
            db.execute("UPDATE users SET status = 'PRIV' WHERE id = :u", u=session["user_id"])
        elif pw:
            db.execute("UPDATE users SET hash = :h, length = :l WHERE id = :u", h=generate_password_hash(pw), l=len(pw), u=session["user_id"])
        elif un:
            if len(un) > 15 :
                return apology("username is limited to 15 characters")
            if re.search(" ", un) or re.search("^0|1|2|3|4|5|6|7|8|9", un):
                return apology("username must not contain spaces or start with a number")
            if db.execute("SELECT username FROM users WHERE username = :u", u=un):
                return apology("username is taken")
            db.execute("UPDATE users SET username = :un WHERE id = :i", un=un, i=session["user_id"])
        else:
            db.execute("UPDATE users SET status = 'PUB' WHERE id = :u", u=session["user_id"])
        return redirect ("/account")
    length = db.execute("SELECT length FROM users WHERE id = :u", u=session["user_id"])[0]["length"]
    return render_template("account.html", u=session["user_id"], stars="*" * length, status=status[0]["status"])

@app.route("/notifications", methods=["GET", "POST"])
@login_required
def notifs():
    """Show messages"""
    if request.method == "POST":
        return
    return render_template("advice.html")

@app.route("/search_d", methods=["GET", "POST"])
@login_required
def search():
    """Search"""
    if request.method == "POST":
        search_phrase = request.form.get("search_item")
        d = "%" + search_phrase + "%"
        s = session["user_id"]
        try:
            x = db.execute(f"SELECT * FROM entries WHERE id = {s} AND entry LIKE :d OR title LIKE :d;", d=d)
            y = db.execute(f"SELECT * FROM entries WHERE id = {s} AND title LIKE :d OR entry LIKE :d;", d=d)
            print(x, y)
            if len(x)==0 and len(y)==0:
                return apology("None.....")
            else:
                return render_template("search_result.html", x = x)
        except:
            return apology("None.....")
    return render_template("search.html")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
