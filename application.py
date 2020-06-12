import os
import requests

from flask import Flask, render_template, request, session, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

#Create a new flask app
app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#Default route
@app.route("/")
def index():
    if 'userid' in session:
        return render_template("userhome.html")
    return render_template("index.html")

#New user route
@app.route("/register", methods=["POST"])
def register():
    #Get new user details from the registration form
    userid = request.form.get("userid")
    password = request.form.get("password")
    email = request.form.get("email")
    mobileno = request.form.get("mobileno")

    #Insert the new user into the database
    db.execute("INSERT INTO users (userid, password, email, mobileno) VALUES(:userid, :password, :email, :mobileno)", {"userid" : userid, "password" : password, "email" : email, "mobileno" : mobileno})
    db.commit()
    return render_template("index.html")

#Login route
@app.route("/login", methods=["POST"])
def login():
    #Get new user details from the login form
    userid = request.form.get("userid")
    password = request.form.get("password")

    #Add userid to the session
    session['userid'] = userid

    #Check if their is any user for provided credentials
    if db.execute("SELECT * FROM users WHERE userid = :userid AND password = :password", {"userid" : userid, "password" : password}).rowcount == 0:
        #Return to index.html
        return render_template("index.html")
    return render_template("userhome.html")


#Logout route
@app.route("/logout", methods=["POST"])
def logout():
    #Remove user from the session
    session.pop('userid', None)
    return render_template("index.html")

#Search book route
@app.route("/search", methods=["POST"])
def search():
    search = "%" + request.form.get("search") + "%"
    searchfilter = request.form.get("searchfilter")
    print(searchfilter)
    if searchfilter == "author":
        books = db.execute("SELECT * FROM books WHERE author LIKE :search", {"search" : search}).fetchall()
    if searchfilter == "title":
        books = db.execute("SELECT * FROM books WHERE title LIKE :search", {"search" : search}).fetchall()
    if searchfilter == "isbn":
        books = db.execute("SELECT * FROM books WHERE isbn LIKE :search", {"search" : search}).fetchall()

    return render_template("searchhome.html", books = books)

#Book information route
@app.route("/book/<int:id>",methods=["GET"])
def book(id):
    book = db.execute("SELECT * FROM books where id = :id", {"id" : id}).fetchone()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key" : "5MrEv1ULNl0OAS1UkxdLmA", "isbns" : book.isbn})
    if res.status_code != 200:
        raise Exception("ERROR: API request unsuccessful.")
    data = res.json()
    numberOfRatings = data['books'][0]['work_ratings_count']
    avgRating = data['books'][0]['average_rating']
    bookreviews = db.execute("SELECT * FROM bookreview where bookid = :bookid", {"bookid" : book.id}).fetchall()
    showReviewOption = False
    if db.execute("SELECT * FROM bookreview where userid = :userid and bookid = :bookid", {"userid" : session["userid"], "bookid" : book.id}).rowcount == 0:
        showReviewOption = True
    return render_template('book.html', book = book, numberOfRatings = numberOfRatings, avgRating = avgRating, bookreviews = bookreviews, showReviewOption = showReviewOption)

#Add book review route
@app.route("/review/<int:bookid>", methods=["POST"])
def review(bookid):
    rating = int(request.form.get('rating'))
    review = request.form.get('review')
    user = db.execute("SELECT * FROM users WHERE userid = :userid", {"userid" : session["userid"]}).fetchone()
    db.execute("INSERT INTO bookreview (bookid, uid, review, rating, userid) VALUES(:bookid, :uid, :review, :rating, :userid)", {"bookid" : bookid, "uid" : user.id, "review" : review, "rating" : rating, "userid" : user.userid})
    db.commit()
    return render_template('success.html')

#Book information API for user
@app.route("/api/book/<int:isbn>", methods=["GET"])
def bookapi(isbn):
    isbn = '{:010d}'.format(isbn)
    isbn = str(isbn)
    book = db.execute("SELECT * FROM books where isbn = :isbn", {"isbn" : isbn}).fetchone()
    if book is None:
        return jsonify({"error" : "Invalid isbn number!!"}), 404
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key" : "5MrEv1ULNl0OAS1UkxdLmA", "isbns" : book.isbn})
    if res.status_code != 200:
        raise Exception("ERROR: API request unsuccessful.")
    data = res.json()
    numberOfRatings = data['books'][0]['work_ratings_count']
    avgRating = data['books'][0]['average_rating']

    return jsonify({
        'title' : book.title,
        'author' : book.author,
        'year' : book.bdate,
        'isbn' : book.isbn,
        'review_count' : numberOfRatings,
        'average_score' : avgRating
    })
