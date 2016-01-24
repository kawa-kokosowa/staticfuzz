# Where memories will be temporarily kept.
#SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/staticfuzz.db'

# Database for memories.
#
# Use a sqlite database file on disk:
#
#   SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/staticfuzz.db'
#   
# Use sqlite memory database (never touches disk):
SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

DEBUG = True
SECRET_KEY = 'BETTER CHANGE ME'

# If a database is fresh, this will be
# the first memory in it.
FIRST_MESSAGE = u'scream into the void'

# Images will be scaled down (maintaining
# aspect ratio) to fit inside these dimensions.
THUMB_MAX_HEIGHT = 360
THUMB_MAX_WIDTH = 360

# Images are indexed to a random number of colors
# between MIN_COLORS and MAX_COLORS.
MIN_COLORS = 2
MAX_COLORS = 10

# How long to wait before the server checks for new
# memories/sends an event. 
#
# The time to wait between each iteration in the
# server event loop. How long before the server
# checks for new memories and sends a new event.
SLEEP_RATE = 0.2

# When EventSource (javascript) is disconnected
# from the server, it will wait these many MS
# before trying to connect to it again.
RETRY_TIME_MS = 3000

# If you submit `/login lain` (or whatever your
# secret is) it will log you in (refresh to see)
# and you can delete memories.
WHISPER_SECRET = 'lain'

# Maximum number of characters for memories.
MAX_CHARACTERS = 140

# If this is enabled an HTML audio player will
# appear in the header and loop an MP3.
# BACKGROUND_MP3 = '/static/background.mp3'

# If this is enabled the specified file is used
# as a notification for new messages.
NOTIFICATION_SOUND = '/static/notification.ogg'

# If this is enabled, the specified file is used
# as a sound for errors.
ERROR_SOUND = '/static/error.ogg'

# Localization, Text, Messages
# A bunch of string values.
GOD_GREET = "Make everyone forget"
LOGIN_FAIL = "I don't think so."  # this should probably be ERROR_
GOD_GOODBYE = "Memory is your mistress."

# Error messages
ERROR_TOO_LONG = u"Too long!"
ERROR_UNORIGINAL = u"Unoriginal!"
ERROR_RATE_EXCEEDED = u"Not so fast!"
ERROR_DANBOORU = u"No matches!"
