import os
import requests

from flask import Flask, jsonify, render_template, request, redirect, session
from flask_session import Session
from flask_socketio import SocketIO, emit
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from time import gmtime, strftime

app = Flask(__name__)
"""app = Flask(__name__, static_url_path='/static')"""

app.config["SESSION_PERMANENT"]=False
app.config["SESSION_TYPE"]="filesystem"
Session(app)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

users = []
rooms = []
true = "true"
false = "false"

class User:
        def __init__(self, name, pwd):
            self.name = name
            self.pwd = pwd
            self.messages = []
            self.channels_more = []
            self.channels = []
        def add_message(self, message):
            self.messages.append(message)
        def add_channel(self, channel):
            self.channels.append(channel)
        def add_channel_more(self, channel):
            self.channels_more.append(channel)
        def __str__(self):
            return f" username: {self.name} "

class Channel:
        def __init__(self, channel, public):
            self.channel = channel
            self.public = public
            self.users = []
            self.messages = []
        def add_user(self, user):
            self.users.append(user)
        def add_message(self, message):
            self.messages.append(message)
            n = 10
            l = len(self.messages)
            if l > n:
                self.messages = self.messages[(l - n) : l]
        def __str__(self):
            return f"channel: {self.channel} "



class Message:
        def __init__(self, message, time, user):
            self.message = message
            self.time = time
            self.user = user
        def __str__(self):
            return f" time : {self.time},  message: {self.message}  "
        def print_info(self):
            return f" username : {self.user.name} / message: {self.message} / time : {self.time}"

def same(sess,pri):
    l = len(sess)
    n = len(pri)
    chat_user_0 = sess
    chat_user_1 = pri[l + 2 : n]
    private_channel_same = "." + chat_user_1 + "&" + chat_user_0
    return private_channel_same

@app.route("/")
def index():
    """content = [
        {"text" : "dog.text", "img" : "dog.img", "p" : "The domestic dog (Canis lupus familiaris when considered a subspecies of the wolf or Canis familiaris when considered a distinct species)[4] is a member of the genus Canis (canines).", "src" : "{{url_for('static', filename='img/dog.jpg')}}}
        {"text" : "fish.text", "img" : "fish.img", "p" : "Fish are gill-bearing aquatic craniate animals that lack limbs with digits. They form a sister group to the tunicates, together forming the olfactores.", "src" : "{{url_for('static', filename='img/fish1.jpg')}}},
        {"text" : "cat.text", "img" : "cat.img", "p" : "Cats are similar in anatomy to the other felids, with a strong flexible body, quick reflexes, sharp retractable claws and teeth adapted to killing small prey.", "src" : "{{url_for('static', filename='img/dog.jpg')}}},
    ]"""

    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    count = 0
    if request.method == "POST":
        name = request.form.get("username")
        pwd = request.form.get("password")
        con = request.form.get("confirmation")
        if(pwd == con and len(pwd) > 0 and len(name) > 0):
            if (len(users) > 0):
                for user in users:
                    if (name != user.name):
                        count += 1
                if count == len(users):

                    user = User(name, pwd)
                    session["user"] = user
                    users.append(user)
            else :

                user = User(name, pwd)
                session["user"] = user
                users.append(user)
        return redirect("/channels")
    else :
        return render_template("register.html")

@socketio.on("check_reg")
def check(data):
    n = 0
    name = data["name"]
    pwd = data["pwd"]
    if len(users)>0:
        for user in users:
            if name == user.name :
                n = n + 1
    else:
        n = n
    emit("checked_reg", {"name":n}, broadcast=False)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method =="POST":
        name = request.form.get("username")
        pwd = request.form.get("password")
        if len(users) > 0:
            for user in users:
                if user.name == name and user.pwd == pwd:
                    if session.get("user"):
                        if session.get("user").channels:
                            l = len(session.get("user").channels_more) - 1
                            channel = session.get("user").channels_more[l].channel
                            if session.get("user").channels_more[l].public == "true":
                                return render_template("channel.html", channel_name=channel, rooms=rooms)
                            elif session.get("user").channels_more[l].public == "false":
                                return render_template("private_channel.html", channel_name=channel, rooms=rooms)
                    else :
                        session["user"] = user
                        return redirect("/channels")
    return render_template("login.html")

@socketio.on("check_login")
def check_login(data):
    n = 0
    name = data["name"]
    pwd = data["pwd"]
    if len(users) > 0:
        for i in range(len(users)):
            if (name == users[i].name and pwd == users[i].pwd):
                n += 1
    else :
        n = 0
    emit("checked_login", {"check":n}, broadcast=False)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/channels", methods=["GET", "POST"])
def channels():
    if session.get("user") is None:
        return redirect("/login")
    count = 0
    if request.method == "POST":
        newroom = request.form.get("newroom")
        if len(rooms) > 0:

            for room in rooms:
                if newroom == room.channel:
                    count += 1
            if count == 0:
                new_channel = Channel(newroom, true)
                rooms.append(new_channel)
        else :
                new_channel = Channel(newroom, true)
                rooms.append(new_channel)
        return redirect("/channels")
    else:
        return render_template("channels.html", users=users, rooms=rooms, user0=session.get("user").name)

@socketio.on("check1")
def check1(data):
    check = 0
    count = 0
    room = data["room"]
    l = len(rooms)
    if l > 0:
        for chat_room in rooms:
            if room == chat_room.channel:
                count += 1
        if count == 0:
            check = 1
    else :
        check = 1
    emit("checked1", {"check":check, "room":room}, broadcast="False")

@app.route("/channels/<string:channel_name>", methods=["GET", "POST"])
def channel(channel_name):
    if session.get("user") is None:
        return redirect("/login")
    if request.method == "POST":
        new_message = request.form.get("message")
        time = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
        message = Message(new_message, time, session.get("user"))
        n = 0
        l = len(rooms)
        if l > 0:
            for room in rooms :
                if channel_name == room.channel:
                    room.add_user(session.get("user"))
                    session.get("user").add_channel(room)
                    room.add_message(message)
                    session.get("user").add_channel_more(room)
                    n += 1

        if n == 0:
            return render_template("error.html", message="No such channel.")
    return render_template("channel.html", channel_name=channel_name, rooms=rooms)

@socketio.on("message")
def message(data):
    new_message = data["message"]
    time = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
    channel = data["channel"]
    message = Message(new_message, time, session.get("user"))
    emit("send_message", {"message":message.print_info(), "channel":channel}, broadcast=True)

@app.route("/create_private_channel/<string:private_channel>", methods=["GET"])
def create_private(private_channel):
    if session.get("user") is None:
        return redirect("/login")
    a = 0
    b = 0
    l = len(session.get("user").name)
    n = len(private_channel)
    chat_user_0 = session.get("user").name
    chat_user_1 = private_channel[l + 2 : n]
    private_channel_same = "." + chat_user_1 + "&" + chat_user_0
    print("true")
    print(private_channel_same)
    print("true")
    for room in rooms:
        if room.channel == private_channel:
            a += 1
    if a == 0:
        for room in rooms:
            if room.channel == private_channel_same:
                b += 1
        if b > 0:
            return render_template("create_private.html", channel_name=private_channel_same, rooms=rooms)
        channel = Channel(private_channel, false)
        channel.add_user(session.get("user"))
        session.get("user").add_channel(channel)
        for user in users:
            if user.name == chat_user_1:
                channel.add_user(user)
                user.add_channel(channel)
        rooms.append(channel)
    return render_template("create_private.html", channel_name=private_channel, rooms=rooms)

@app.route("/private/<string:channel_name>", methods=["GET", "POST"])
def private(channel_name):
    if session.get("user") is None:
        return redirect("/login")
    if request.method == "POST":
        new_message = request.form.get("message")
        time = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
        message = Message(new_message, time, session.get("user"))
        session.get("user").add_message(message)
        for room in rooms :
            if room.channel == channel_name:
                room.add_message(message)
                session.get("user").add_channel_more(room)
    """channel_name_same = same(session.get("user").name, channel_name)"""
    l = len(session.get("user").name)
    n = len(channel_name)
    chat_user_0 = session.get("user").name
    chat_user_1 = channel_name[l + 2 : n]
    channel_name_same = "." + chat_user_1 + "&" + chat_user_0
    print(channel_name)
    print("first")
    print(channel_name_same)
    print("last")
    print(" done ")
    return render_template("private_channel.html", channel_name=channel_name, channel_name_same=channel_name_same, rooms=rooms)

@socketio.on("message_pri")
def message_pri(data):
    new_message = data["message"]
    channel = data["channel"]
    time = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
    message = Message(new_message, time, session.get("user"))
    emit("send_message_pri", {"channel":channel, "message":message.print_info()}, broadcast=True)
