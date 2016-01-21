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


import io
import json
import docopt
import random
import base64
import gevent
import sqlite3
import urllib2
import mimetypes

from flask import *
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageOps
from cStringIO import StringIO
from contextlib import closing
from gevent.pywsgi import WSGIServer
from gevent import monkey
monkey.patch_all()


# Create and init the staticfuzz
app = Flask(__name__)
app.config.from_object("config")
db = SQLAlchemy(app)


class Memory(db.Model):
    __tablename__ = "memories"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Unicode(140), unique=True)
    base64_image = db.Column(db.String(), unique=True)

    def __init__(self, text, base64_image=None):
        self.text = text
        self.base64_image = base64_image

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


def init_db():
    """For use on command line for setting up
    the database.

    """

    db.drop_all()
    db.create_all()


def event():

    with app.app_context():
        latest_memory_id = Memory.query.order_by(Memory.id.desc()).first().id

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
def stream():
    """SSE (Server Side Events), for an EventSource. Send
    the event of a new message.

    """

    return Response(event(), mimetype="text/event-stream")


@app.route('/')
def show_memories():
    """Show the memories.

    """

    memories = Memory.query.order_by(Memory.id.asc()).all()
    memories_for_jinja = [memory.to_dict() for memory in memories]

    return render_template('show_memories.html',
                           memories=memories_for_jinja)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """God logs in.

    """

    error = None

    if request.method == 'POST':

        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash("Hello, god.")

            return redirect(url_for('show_memories'))

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """God goes bye!

    """

    session.pop('logged_in', None)
    flash('God goes "bye!"')

    return redirect(url_for('show_memories'))


def glitch_from_url(url_string):
    # get the image from the net
    urlopen_result = urllib2.urlopen(url_string)
    urlopen_result_io = io.BytesIO(urlopen_result.read())

    # open and tweak the image
    tweaked_image = Image.open(urlopen_result_io)
    tweaked_image.thumbnail([app.config['THUMB_MAX_WIDTH'], app.config['THUMB_MAX_HEIGHT']])

    # autocontrast
    tweaked_image = ImageOps.invert(tweaked_image)

    # random chance to invert
    if random.randint(0, 2):
        tweaked_image = ImageOps.invert(tweaked_image)

    tweaked_image = tweaked_image.convert(mode='P', palette=Image.ADAPTIVE,
                                          colors=random.randint(app.config['MIN_COLORS'],
                                                                app.config['MAX_COLORS']))

    # save the image as base64 HTML image
    glitch_image = StringIO()
    tweaked_image.save(glitch_image, "PNG")
    glitch_string = glitch_image.getvalue()

    # glitch right before encoding
    for i in range(1, random.randint(1, 5)):
        # splice
        start_point = random.randint(2500, len(glitch_string))
        end_point = start_point + random.randint(0, len(glitch_string) - start_point)
        section = glitch_string[start_point:end_point]

        repeated = ''

        for i in range(1, random.randint(1, 5)):
            repeated += section

    new_start_point = random.randint(2500, len(glitch_string))
    new_end_point = new_start_point + random.randint(0, len(glitch_string) - new_start_point)
    glitch_string = glitch_string[:new_start_point] + repeated + glitch_string[new_end_point:]

    base64_string = base64.b64encode(glitch_string)

    return base64_string


@app.route('/new_memory', methods=['POST'])
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
        
        return redirect(url_for('show_memories'))

    # memomry text may not exceed MAX_CHARACTERS
    if len(memory_text) > app.config['MAX_CHARACTERS']:
        abort(400)

    # you cannot repost something already in the memories
    if Memory.query.filter_by(text=memory_text).all():

        return redirect(url_for('show_memories'))

    # delete the oldest to make room for the new
    #Memory.query.all().group_by(Memory.id.asc()).first().delete()

    # if it's URI to image let's download it glitch it up and store as base64
    mimetype, __ = mimetypes.guess_type(memory_text)

    if mimetype and mimetype.startswith('image'):
        base64_image = glitch_from_url(memory_text)
    else:
        base64_image = None

    new_memory = Memory(text=memory_text, base64_image=base64_image)
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
        abort(401)  # action forbidden

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
