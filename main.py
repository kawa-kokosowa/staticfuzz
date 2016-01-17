import sqlite3
from flask import *
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


@app.route('/')
def show_memories():
    """Show the memories.

    """

    cur = g.db.execute('select id, memory from memories order by id asc')
    memories = [dict(id=row[0], memory=row[1]) for row in cur.fetchall()]

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

    # if memory is longer than MAX_CHARACTERS
    # then we send a bad request
    if len(request.form['memory']) > app.config['MAX_CHARACTERS']:
        abort(400)

    g.db.execute('''
                 DELETE FROM memories
                 WHERE id NOT IN
                   (SELECT id FROM memories
                    ORDER BY id DESC LIMIT 9)
                 ''')
    g.db.execute('insert into memories (memory) values (?)',
                 [request.form['memory']])
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
