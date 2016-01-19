import io
import json
import random
import base64
import sqlite3
import urllib2
import mimetypes

from flask import *
from PIL import Image
from cStringIO import StringIO
from contextlib import closing


# Create and init the staticfuzz
app = Flask(__name__)
app.config.from_object("config")


def connect_db():

    return sqlite3.connect(app.config['DATABASE'])


def init_db():

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
        # get the image from the net
        urlopen_result = urllib2.urlopen(memory_text)
        urlopen_result_io = io.BytesIO(urlopen_result.read())
    
        # open and tweak the image
        tweaked_image = Image.open(urlopen_result_io)
        tweaked_image.thumbnail([app.config['THUMB_MAX_WIDTH'], app.config['THUMB_MAX_HEIGHT']])
        tweaked_image = tweaked_image.convert(mode='P', palette=Image.ADAPTIVE, colors=random.randint(2, 10))
    
        # save the image as base64 HTML image
        base64_image = StringIO()
        tweaked_image.save(base64_image, "PNG", colors=1)
        base64_string = base64.b64encode(base64_image.getvalue())
    
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
    app.run()
