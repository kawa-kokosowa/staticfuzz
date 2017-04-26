"""staticfuzz: memories that vanish.

Async server-sent event (SSE) text+board.

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
import datetime
import random
import urllib
import time
import json
import os
import re

import flask
import docopt
import requests
import markupsafe
from flask_sse import sse
from flask_limiter import Limiter
from celery import Celery

import glitch


# Create and init the staticfuzz
app = flask.Flask(__name__)
app.config.from_object("config")
app.config["REDIS_URL"] = "redis://localhost"
app.register_blueprint(sse, url_prefix='/stream')
limiter = Limiter(app)
celery = Celery(
    'staticfuzz',
    broker='redis://localhost',
    backend='redis://localhost',
)


memories_counter = 0
"""The total number of memories having been created since launch."""

memories = []
"""The memories list structure stores ten memories in memory like this:

[
    (
        numberth memory created since staticfuzz launched (int),
        timestamp/unix epoch (int),
        memory text (str),
        base64 image (str|None),
    ),
]

Note that if "base64 image" isn't None, then "memory text" is a URI
pointing to image.

numberth memory created since... is set/determined by the memories_counter...

"""


@celery.task
def memory_structure_list_pop_oldest():
    """At position 0 of our ten item list."""

    # we don't subtract from counter cuz...
    global memories

    if len(memories) >= 10:
        return memories.pop(0)


@celery.task
def memory_structure_list_append(memory_structure):
    global memories
    global memories_counter
    memories.append(memory_structure)
    memories_counter += 1
    return True


def memory_to_dict(memory_structure):
    """Take a memory structure and make a dictionary.

    Arguments:
        memory_structure (tuple): Related to the memories
            module-level variable, which contains all ten
            of the memories in... memory. To see what
            this argument should look like, please see
            the memories module level attribute's docstring.

    Returns:
        dict: Looks something like this:

            >>> {'text': "foo", "base64_image": None}

    """

    timestamp = datetime.datetime.fromtimestamp(memory_structure[1]).isoformat()
    return {
        'id': memory_structure[0],
        'timestamp': timestamp,
        'text': memory_structure[2],
        'base64_image': memory_structure[3],
    }


    # FIXME: this is for create...
    def __init__(self, text):
        """Create a new memory with text and optionally base64
        representation of the image content found at the URI in
        the text argument.

        Args:
            text (str): This is required for all memories. If this
                is a link to an image, a base64_image thumbnail will
                be generated for said image.

        """

        self.text = text


class SlashCommandResponse(object):
    """All SlashCommand.callback() methods must return this.

    Attributes:
        create_memory (bool): If True create a memory using
            value attribute. Otherwise serve value as a
            response.
        value (tuple[str, int]|str): Either a tuple which
            holds a status message and an HTTP error code,
            or a string to create a memory. Example values:

                >>> "some memory text"
                >>> ("Bad ID", 400)

    See Also:
        SlashCommand

    """

    def __init__(self, create_memory, value):
        """The result of a slash command.

        Args:
            create_memory (bool): If True the value will be
                used to create a memory. If False value will be
                sent as a response, e.g., "Invalid URI," 400.
            value (any): A string to be used for creating a
                memory, or a response to be sent like:

                >>> ("Invalid Shipping Address", 400)

        Examples:

            >>> SlashCommandResponse(False, ("Bad thing!", 400))
            >>> SlashCommandResponse(True, "some kinda memory text")

        """

        self.create_memory = create_memory
        self.value = value


class SlashCommand(object):
    """IRC-like command; a more complicated memory.

    When input text is received, it is also sent to each
    slash command's attempt() method. The first attempt
    to return a SlashCommandResponse gets used either to
    create a memory or serve a response (like a 400).

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

        # NOTE: what if typeerror is raised because of something
        # in the callback. Seems like a bad approach... could
        # cause debugging headaches.
        except TypeError:

            return SlashCommandResponse(False, ("%s incorrect args" %
                                                cls.NAME, 400))

    @staticmethod
    def callback(*args):
        """Ovverride this with another staticmethod; do something
        with the args, return a SlashCommandResponse.

        Use any number of args you please (including 0) or *args
        (variable length).

        """

        pass


class SlashLogin(SlashCommand):
    """Login as deity if the secret is correct.

    Note:
        You have to refresh the page for this to work.

    See Also:
        SlashLogout

    """

    NAME = u"login"

    @staticmethod
    def callback(secret_attempt):
        """Attempt to use secret_attempt to identify as a deity.

        Args:
            secret_attempt (str): Password/whisper secret
                being attempted. If the secret corresponds
                to the one set in the config file, the
                session's "deity" key is set to True.

        Returns:
            SlashCommandResponse: Either a login failure 401, or
                redirect to the show_memories page after success.

        """

        if secret_attempt == app.config['WHISPER_SECRET']:
            flask.session['deity'] = True
            flask.flash(app.config["DEITY_GREET"])
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
        """User who sent this will no longer be a deity.

        Returns:
            SlashCommandResponse: redirect to show_memories.

        """

        flask.session.pop('deity', None)
        flask.flash(app.config["DEITY_GOODBYE"])
        redirect = flask.redirect(flask.url_for('show_memories'))

        return SlashCommandResponse(False, redirect)


class SlashDanbooru(SlashCommand):
    """Get a random image from the first page of a search
    for specific tags on danbooru.donmai.us.

    See Also:
        http://danbooru.donmai.us/wiki_pages/43568 

    """

    NAME = u"danbooru"

    @staticmethod
    def callback(*args):
        """Each arg is a Danbooru tag.

        Args:
          *args (list[str]): Each element is a string/tag
            to search for, e.g., "goo_girl"

        Returns:
            SlashCommandResponse: Either the random image found,
                or a 400 for whatever error encountered while
                attempting to get a random image.

        """

        tags = urllib.quote_plus(' '.join(args))
        endpoint = ('http://danbooru.donmai.us/posts.json?'
                    'tags=%s&limit=10&page1' % tags)
        results = requests.get(endpoint).json()

        try:
            selected_image = ("http://danbooru.donmai.us" +
                              random.choice(results)["file_url"])

            return SlashCommandResponse(True, selected_image)

        except IndexError:

            # There were no results!
            return SlashCommandResponse(False,
                                        (app.config["ERROR_DANBOORU"], 400))


@app.template_filter('number_links')
def number_links(string_being_filtered):
    escaped_string = markupsafe.escape(string_being_filtered)
    unicode_escaped_string = unicode(escaped_string)
    pattern = re.compile("(?<!&)(#\d+)")
    final_string = pattern.subn(r'<a href="\1">\1</a>',
                                unicode_escaped_string)[0]

    return final_string


def uri_valid_image(uri):
    """Check if provided `uri` is a valid URI to
    an image, as allowed by the extension whitelist.

    Returns:
        bool: True if `uri` is both an accessible
            URI without any errors *and* the file
            extension is in the whitelist.

    """

    image_extension_whitelist = (".jpg", ".jpeg", ".png", ".gif")

    if not uri.lower().endswith(image_extension_whitelist):

        return False

    # actually fetch the resource to see if it's real or not
    try:
        request = requests.get(uri)
        assert request.status_code == 200

    except (requests.exceptions.InvalidSchema,
            requests.exceptions.MissingSchema,
            requests.exceptions.ConnectionError,
            AssertionError):

        return False

    return True


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

    # FIXME
    memory_text = "lol this should be config"
    memory_structure = (
        memories_counter,
        int(time.time()),
        memory_text,
        # uri valid image can be better, just see urlink... should
        # make that a sep package... also y not using b64 pkg i made?!
        # FIXME
        glitch.glitch_from_url(memory_text) if uri_valid_image(memory_text) else None,
    )
    memory_structure_list_append(memory_structure)


@app.route('/')
@limiter.limit("2/second")
def show_memories():
    """Show the memories.

    """

    # i don't believe this is necessary now?
    memories_sorted = sorted(memories, key=lambda x: x[0])
    memories_for_jinja = [memory_to_dict(memory) for memory in memories_sorted]

    return flask.render_template('show_memories.html',
                                 memories=memories_for_jinja)


@celery.task
# you cannot repost something already in the memories
def original(text):
    global memories

    for memory in memories:
        if memory[3] == text:
            return app.config["ERROR_UNORIGINAL"], 400


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
    # success!
    return original(memory_text)


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

            # only happens if it is a non-match
            continue

        elif result.create_memory is True:
            memory_text = result.value

            break

        elif result.create_memory is False:

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

    # XXX: may wanna look at this again... refactored!
    # what if use slots based approach? replace oldest...
    # If there are ten memories already, delete the oldest
    # to make room!
    memory_structure_list_pop_oldest()
    if len(memories) >= 10:
        del memories[0]

    # XXX: make this function?
    memory_structure = (
        (
            memories_counter,
            int(time.time()),
            memory_text,
            # uri valid image can be better, just see urlink... should
            # make that a sep package... also y not using b64 pkg i made?!
            # FIXME
            glitch.glitch_from_url(memory_text) if uri_valid_image(memory_text) else None,
        )
    )
    memory_structure_list_append(memory_structure)
    sse.publish(memory_to_dict(memory_structure), type='greeting')  # XXX

    return flask.redirect(flask.url_for('show_memories'))







@app.route('/forget', methods=['POST'])
def forget():
    """Deities can make us all forget.

    Delete a memory.

    Returns:
        flask redirect to show_memories or send a 401
            unauthorized HTTP error.

    """

    if not flask.session.get('deity'):
        flask.abort(401)

    for i, memory in enumerate(memories):
        if memory[0] == flask.request.form['id']:
            del memories[i]

    return flask.redirect(flask.url_for('show_memories'))


# FIXME: delete later?
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
        app.run()
        #WSGIServer(('', app.config["PORT"]), app).serve_forever()
