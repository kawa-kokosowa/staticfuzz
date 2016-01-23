"""staticfuzz: async SSE transient textboard

If this script is invoked directly, it can be used
as a CLI for managing staticfuzz.

You can test this by running:
    gunicorn -b 127.0.0.1:5000 -k gevent main:app

Usage:
    staticfuzz.py init_db
    staticfuzz.py serve
    staticfuzz.py -h | --help

Options:
    -h --help    Show this screen.

"""


import json
import random
import glitch
import docopt
import base64
import gevent
import sqlite3
import requests
import mimetypes

from flask import *
from flask_limiter import Limiter
from flask_sqlalchemy import SQLAlchemy
from contextlib import closing
from gevent.pywsgi import WSGIServer
from gevent import monkey
monkey.patch_all()


# Create and init the staticfuzz
app = Flask(__name__)
app.config.from_object("config")
db = SQLAlchemy(app)
limiter = Limiter(app)


class Memory(db.Model):
    __tablename__ = "memories"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Unicode(140), unique=True)
    base64_image = db.Column(db.String(), unique=True)

    def __init__(self, text):
        self.text = text

        # if it's URI to image let's download it glitch it up and store as base64
        mimetype, __ = mimetypes.guess_type(text)

        if mimetype and mimetype.startswith(u'image'):
            self.base64_image = glitch.glitch_from_url(text)
        else:
            self.base64_image = None

    def __repr__(self):

        return "<Memory #%d: %s>" % (self.id, self.text)

    @classmethod
    def from_dict(cls, memory_dict):
        
        return cls(text=memory_dict["text"],
                   base64_image=memory_dict.get("base64_image"))

    def to_dict(self):

        return {"text": self.text,
                "base64_image": self.base64_image,
                "id": self.id}

    def newer_than(self, id):

        return (Memory.query.
                filter(Memory.id > id).
                order_by(Memory.id.asc()))


@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate exceeding error message.

    """

    return app.config["ERROR_RATE_EXCEEDED"], 429


def danbooru_image(tags):
    endpoint = ('http://danbooru.donmai.us/posts.json?tags=%s&limit=10&page1' % tags)
    r = requests.get(endpoint)
    results = r.json()
    random_image = "http://danbooru.donmai.us" + random.choice(results)["file_url"]

    return random_image


def init_db():
    """For use on command line for setting up
    the database.

    """

    db.drop_all()
    db.create_all()

    new_memory = Memory(text=app.config["FIRST_MESSAGE"])
    db.session.add(new_memory)
    db.session.commit()


def event():

    with app.app_context():

        try:
            latest_memory_id = Memory.query.order_by(Memory.id.desc()).first().id
        except AttributeError:
            # .id will raise AttributeError if the query doesn't match anything
            latest_memory_id = 0

    while True:

        with app.app_context():
            memories = (Memory.query.filter(Memory.id > latest_memory_id).
                        order_by(Memory.id.asc()).all())

        if memories:
            latest_memory_id = memories[-1].id
            newer_memories = [memory.to_dict() for memory in memories]

            yield "data: " + json.dumps(newer_memories) + "\n\n"

        with app.app_context():
            gevent.sleep(app.config['SLEEP_RATE'])


@app.route('/stream/', methods=['GET', 'POST'])
@limiter.limit("15/minute")
def stream():
    """SSE (Server Side Events), for an EventSource. Send
    the event of a new message.

    """

    return Response(event(), mimetype="text/event-stream")


@app.route('/')
@limiter.limit("2/second")
def show_memories():
    """Show the memories.

    """

    memories = Memory.query.order_by(Memory.id.asc()).all()
    memories_for_jinja = [memory.to_dict() for memory in memories]

    return render_template('show_memories.html',
                           memories=memories_for_jinja)


@app.route('/new_memory', methods=['POST'])
@limiter.limit("1/second")
def new_memory():
    """Attempt to add a new memory.
    
    Forget the 11th oldest memory.

    The memory must meet these requirements:

      * At least 1 character long
      * 140 characters or less
      * Cannot already exist in the database

    """

    # The text submitted to us from POST
    memory_text = request.form['text'].strip()

    # memory must be at least 1 char
    if len(memory_text) == 0:

        return u"Too short!", 400

    # is this a command?
    if memory_text.startswith(u'/login '):

        if memory_text == u'/login ' + app.config['WHISPER_SECRET']:
            session['logged_in'] = True
            flash(app.config["GOD_GREET"])

            return redirect(url_for('show_memories'))

        else:

            return app.config["LOGIN_FAIL"], 401

    elif memory_text == u'/logout':
        session.pop('logged_in', None)
        flash(app.config["GOD_GOODBYE"])

        return redirect(url_for('show_memories'))

    elif memory_text.startswith(u"/danbooru "):
        memory_text = memory_text.replace(u"/danbooru ", "")
        memory_text = danbooru_image(memory_text)

    # memomry text may not exceed MAX_CHARACTERS
    if len(memory_text) > app.config['MAX_CHARACTERS']:

        return app.config["ERROR_TOO_LONG"], 400

    # you cannot repost something already in the memories
    if Memory.query.filter_by(text=memory_text).all():

        return app.config["ERROR_UNORIGINAL"], 400

    # if ten entries in db, delete oldest to make room for new
    if Memory.query.count() == 10:
        memory_to_delete = Memory.query.order_by(Memory.id.asc()).first()
        db.session.delete(memory_to_delete)

    new_memory = Memory(text=memory_text)
    db.session.add(new_memory)
    db.session.commit()
    flash("A memory made, another forgotten")

    return redirect(url_for('show_memories'))


@app.route('/forget', methods=['POST'])
def forget():
    """God can make us all forget.

    Delete a memory.

    """

    if not session.get('logged_in'):
        abort(401)

    Memory.query.filter_by(id=request.form["id"]).delete()
    db.session.commit()
    flash('Forgotten.')

    return redirect(url_for('show_memories'))


if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)

    if arguments["init_db"]:
        init_db()

    if arguments["serve"]:
        WSGIServer(('', 5000), app).serve_forever()
