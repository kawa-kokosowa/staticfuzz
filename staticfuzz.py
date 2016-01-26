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

import mimetypes
import random
import json
import os

import flask
import docopt
import gevent
import requests
from flask_limiter import Limiter
from flask_sqlalchemy import SQLAlchemy
from gevent.pywsgi import WSGIServer
from gevent import monkey

import glitch


monkey.patch_all()  # NOTE: totally cargo culting this one

# Create and init the staticfuzz
app = flask.Flask(__name__)
app.config.from_object("config")
limiter = Limiter(app)

db = SQLAlchemy(app)


class Memory(db.Model):
    """SQLAlchemy/database abstraction of a memory.

    Memories are aptly kept in the "memories" table.

    Fields/attributes:
        id (int): Unique identifier, never resets.
        text (str): String, the text of the memory, the
            memory itself.
        base64_image str): if `text` is a URI to an image,
            then this is the base64 encoding of said
            image. Used as thumbnail.

    """

    __tablename__ = "memories"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Unicode(140), unique=True)
    base64_image = db.Column(db.String())

    def __init__(self, text, base64_image=None):
        """Create a new memory with text and optionally base64
        representation of the image content found at the URI in
        the text argument.

        Args:
            text (str): This is required for all memories. If this
                is a link to an image, a base64_image thumbnail will
                be generated for said image.
            base64_image (str): Base 64 thumbnail for an image linked
                in the text field. This field is used for base64 encoded
                data URI (image src for thumbnails).

        """

        self.text = text
        self.base64_image = None

        if base64_image:
            self.base64_image = base64_image
        elif uri_valid_image(text):  # valid uri to image?
            self.base64_image = glitch.glitch_from_url(text)

    def __repr__(self):

        return "<Memory #%d: %s>" % (self.id, self.text)

    @classmethod
    def from_dict(cls, memory_dict):
        """Create a new memory based on a dictionary.

        Args:
            memory_dict (dict): Keys are the fields for
                a memory. It looks like this:

                >>> {'text': "foo", "base64_image": None}

        Returns:
            Memory: Created from a dictionary, for you to
                save in a database!

        """

        return cls(text=memory_dict["text"],
                   base64_image=memory_dict.get("base64_image"))

    def to_dict(self):
        """Return a dictionary representation of this Memory.

        Returns:
            dict: Looks something like this:

                >>> {'text': "foo", "base64_image": None}

        """

        return {"text": self.text,
                "base64_image": self.base64_image,
                "id": self.id}


class SlashCommandResponse(object):
    """All SlashCommand.callback() methods must return this.

    See Also:
        SlashCommand

    """

    def __init__(self, to_database, value):
        """The result of a slash command.

        Args:
            to_database (bool): If True the response is
                carried to the database, otherwise it
                is returned to the enduser.
            value (any): Any data returned from the slash
                command.

        """

        self.to_database = to_database
        self.value = value


class SlashCommand(object):
    """/something to be executed instead of posted.

    When a piece of text is sent, it is compared against
    all SlashCommands to possibly trigger those commands.

    The callback() static method must return a boolean as
    the first index value of the result, e.g.:

    >>> add(1, 1,)
    True, 2

    The boolean represents if we return out (drop return
    to page).

    """

    NAME = str()

    @classmethod
    def attempt(cls, text):
        """Return either None or the SlashCommandResponse
        associated with running the command.

        Returns:
            SlashCommandResponse|None: Returns None if
                `text` is not even this command. Otherwise
                return the result of executing this command.

        """

        text = text.lower().strip()
        pattern = "/" + cls.NAME

        if not (text.startswith(pattern + " ") or
                text == pattern):

            return None

        text = text.replace(pattern, u"")
        args = [arg.strip() for arg in text.split(" ") if arg.strip()]

        try:

            return cls.callback(*args)

        except TypeError:

            return SlashCommandResponse(False, ("%s incorrect args" %
                                                cls.NAME, 400))

    @staticmethod
    def callback(*args):
        """Ovverride this with another staticmethod; do something
        with the args, return a SlashCommandResponse.

        """

        pass


class SlashLogin(SlashCommand):
    """Login as deity if the secret is correct.

    Note:
        You have to refresh the page for this to work.

    """

    NAME = u"login"

    @staticmethod
    def callback(secret_attempt):
        """Attempt to use secret_attempt to login.

        Args:
            secret_attempt (str): Password/whisper secret
                being attempted.

        """

        if secret_attempt == app.config['WHISPER_SECRET']:
            flask.session['logged_in'] = True
            flask.flash(app.config["GOD_GREET"])
            redirect = flask.redirect(flask.url_for('show_memories'))

            return SlashCommandResponse(False, redirect)

        else:

            return SlashCommandResponse(False, (app.config["LOGIN_FAIL"], 401))


class SlashLogout(SlashCommand):
    """Stop being a deity.

    Note:
        You have to refresh the page for this to work.

    """

    NAME = u"logout"

    @staticmethod
    def callback():
        """User who sent this will no longer be a deity."""

        flask.session.pop('logged_in', None)
        flask.flash(app.config["GOD_GOODBYE"])
        redirect = flask.redirect(flask.url_for('show_memories'))

        return SlashCommandResponse(False, redirect)


class SlashDanbooru(SlashCommand):
    """Get a random image from Danbooru from tags.

    """

    NAME = u"danbooru"

    @staticmethod
    def callback(*args):
        """

        Args:
          *args (list[str]): Each element is a string/tag
            to search for, e.g., "goo_girl"

        """

        tags = "%20".join(args)
        endpoint = ('http://danbooru.donmai.us/posts.json?tags=%s&limit=10&page1' % tags)
        results = requests.get(endpoint).json()

        try:
            selected_image = ("http://danbooru.donmai.us" +
                              random.choice(results)["file_url"])

            return SlashCommandResponse(True, selected_image)

        except IndexError:

            # There were no results!
            return SlashCommandResponse(False,
                                        (app.config["ERROR_DANBOORU"], 400))


def uri_valid_image(uri):
    """Check if provided `uri` is a valid URI to
    an image, as allowed by the extension whitelist.

    Returns:
        bool: True if `uri` is both an accessible
            URI without any errors *and* the file
            extension is in the whitelist.

    """

    image_extension_whitelist = (".jpg", ".jpeg", ".png", ".gif")

    # actually fetch the resource to see if it's real or not
    try:
        request = requests.get(uri)
        assert request.status_code == 200

    except (requests.exceptions.InvalidSchema,
            requests.exceptions.MissingSchema,
            requests.exceptions.ConnectionError,
            AssertionError):

        return False

    return uri.lower().endswith(image_extension_whitelist)


@app.errorhandler(429)
def ratelimit_handler(error):
    """Handle rate exceeding error message.

    Args:
        error (?): automagically provided

    """

    return app.config["ERROR_RATE_EXCEEDED"], 429


@app.route('/random_image', methods=['GET', 'POST'])
@limiter.limit("2/second")
def random_image():
    # NOTE: should be a config var
    image_directory = app.config["RANDOM_IMAGE_DIRECTORY"]
    image_path = os.path.join(image_directory,
                              random.choice(os.listdir(image_directory)))
            
    return flask.send_file(image_path, mimetypes.guess_type(image_path)[0])


def init_db():
    """For use on command line for setting up
    the database.

    """

    db.drop_all()
    db.create_all()

    test_memory = Memory(text=app.config["FIRST_MESSAGE"])
    db.session.add(test_memory)
    db.session.commit()


def event():
    """EventSource stream; server side events. Used for
    sending out new memories.

    Returns:
        json event (str): --

    See Also:
        stream()

    """

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

    See Also:
        event()

    """

    return flask.Response(event(), mimetype="text/event-stream")


@app.route('/')
@limiter.limit("2/second")
def show_memories():
    """Show the memories.

    """

    memories = Memory.query.order_by(Memory.id.asc()).all()
    memories_for_jinja = [memory.to_dict() for memory in memories]

    return flask.render_template('show_memories.html',
                                 memories=memories_for_jinja)


def validate(memory_text):
    """Return None if validation successful, else
    return 400 + status message.

    """

    # memory must be at least 1 char
    if len(memory_text) == 0:

        return u"Too short!", 400

    # memomry text may not exceed MAX_CHARACTERS
    if len(memory_text) > app.config['MAX_CHARACTERS']:

        return app.config["ERROR_TOO_LONG"], 400

    # you cannot repost something already in the memories
    if Memory.query.filter_by(text=memory_text).all():

        return app.config["ERROR_UNORIGINAL"], 400

    # success!
    return None


@app.route('/new_memory', methods=['POST'])
@limiter.limit("1/second")
def new_memory():
    """Attempt to add a new memory.

    Forget the 11th oldest memory.

    The memory must meet these requirements:

      * At least 1 character long
      * 140 characters or less
      * Cannot already exist in the database

    The memory is checked for possible SlashCommand(s).

    """

    memory_text = flask.request.form['text'].strip()
    original_memory_text = memory_text
    validation_payload = validate(memory_text)

    if validation_payload:

        return validation_payload

    # commands
    slash_commands = [SlashLogin, SlashLogout, SlashDanbooru]

    for slash_command in slash_commands:
        result = slash_command.attempt(memory_text)

        if result is None:

            continue

        elif result.to_database is True:
            memory_text = result.value

            break

        elif result.to_database is False:

            return result.value

    # We do not want to submit anything that didn't execute
    # a slash command, but starts with a slash! This is in
    # case of an event like "/logni password", so it's not
    # broadcasted to the entire world.
    #
    # At this point, either we have made a change to the
    # database and return'd out, or we modified the memory
    # text, in which it'll differ from original_memory.
    if memory_text[0] == '/' and memory_text == original_memory_text:

        return "Invalid Slash Command", 400

    # If there are ten memories already, delete the oldest
    # to make room!
    if Memory.query.count() == 10:
        memory_to_delete = Memory.query.order_by(Memory.id.asc()).first()
        db.session.delete(memory_to_delete)

    new_memory = Memory(text=memory_text)
    db.session.add(new_memory)
    db.session.commit()

    return flask.redirect(flask.url_for('show_memories'))


@app.route('/forget', methods=['POST'])
def forget():
    """Deities can make us all forget.

    Delete a memory.

    """

    if not flask.session.get('logged_in'):
        flask.abort(401)

    Memory.query.filter_by(id=flask.request.form["id"]).delete()
    db.session.commit()

    return flask.redirect(flask.url_for('show_memories'))


# NOTE: this is all the way at the bottom so we can use init_db!
if app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:":
    # Use memory SQLITE database! Meaning the HDD is never touched!
    # Since this database will be in the memory, we have to create
    # it at the beginning of every app run.
    init_db()

if __name__ == '__main__':
    arguments = docopt.docopt(__doc__)

    if arguments["init_db"]:
        init_db()

    if arguments["serve"]:
        WSGIServer(('', 5000), app).serve_forever()
