"""staticfuzz: async transient textboard

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
from PIL import Image, ImageOps
from cStringIO import StringIO
from contextlib import closing
from gevent.pywsgi import WSGIServer
from gevent import monkey
monkey.patch_all()


# Create and init the staticfuzz
app = Flask(__name__)

app.config.from_object("config")


def connect_db():

    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    """For use on command line for setting up
    the database.

    """

    with closing(connect_db()) as db:

        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())

        db.commit()


@app.before_request
def before_request():
    """For each request, init a db connection before and
    close it afterwards.

    """

    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)

    if db is not None:
        db.close()


def event():
    latest_memory_id = 0

    while True:

        with app.app_context():
            db = connect_db()
            sql = "SELECT * FROM memories WHERE id > ? ORDER BY id ASC"

            cursor = db.execute(sql, (latest_memory_id,))
            query_results = cursor.fetchall()
            db.close()

        fields = ('id', 'memory', 'image')

        if query_results:
            latest_memory_id = query_results[-1][0]
            newer_memories = [dict(zip(fields, row)) for row in query_results]

            yield "data: " + json.dumps(newer_memories) + "\n\n"

        with app.app_context():
            gevent.sleep(app.config['SLEEP_RATE'])


@app.route('/stream/', methods=['GET', 'POST'])
def stream():

    return Response(event(), mimetype="text/event-stream")


@app.route('/list_memories')
def list_memories():

    cur = g.db.execute('SELECT id, memory, image FROM memories ORDER BY id ASC')
    memories = [{'id': row[0], 'memory': row[1], 'image': row[2]} for row in cur.fetchall()]

    return json.dumps(memories)


@app.route('/')
def show_memories():
    """Show the memories.

    """

    cur = g.db.execute('SELECT id, memory, image FROM memories ORDER BY id ASC')
    memories = [dict(id=row[0], memory=row[1], image=row[2]) for row in cur.fetchall()]

    return render_template('show_memories.html', memories=memories)


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


@app.route('/add_memory', methods=['POST'])
def add_memory():
    """Remember something; add a memory.
    
    Then forget the 11th oldest memory.

    """

    memory_text = request.form['memory'].strip()

    if len(memory_text) == 0:
        
        return redirect(url_for('show_memories'))

    # you cannot repost something already in the memories
    cursor = g.db.execute("SELECT memory FROM memories WHERE memory=?", (memory_text,))

    if cursor.fetchall():

        return redirect(url_for('show_memories'))

    # if memory is longer than MAX_CHARACTERS
    # then we send a bad request
    if len(memory_text) > app.config['MAX_CHARACTERS']:
        abort(400)

    # delete the oldest to make room for the new
    g.db.execute('''
                 DELETE FROM memories
                 WHERE id NOT IN
                   (SELECT id FROM memories
                    ORDER BY id DESC LIMIT 9)
                 ''')

    # if it's URI to image let's download it glitch it up and store as base64
    mimetype, __ = mimetypes.guess_type(memory_text)

    if mimetype and mimetype.startswith('image'):
        base64_string = glitch_from_url(memory_text)
    
        g.db.execute('insert into memories (memory, image) values (?, ?)',
                     [memory_text, base64_string])

    else:
        g.db.execute('insert into memories (memory) values (?)',
                     [memory_text])

    g.db.commit()
    flash("A memory made, another forgotten")

    return redirect(url_for('show_memories'))


@app.route('/forget', methods=['POST'])
def forget():
    """God can make us all forget.

    Delete a memory.

    """

    if not session.get('logged_in'):
        abort(401)  # action forbidden

    print "The id is " + request.form['id']
    g.db.execute('delete from memories where id=?',
                 [request.form['id']])
    g.db.commit()
    flash('Forgotten.')

    return redirect(url_for('show_memories'))


if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)

    if arguments["init_db"]:
        init_db()

    if arguments["serve"]:
        WSGIServer(('', 5000), app).serve_forever()
