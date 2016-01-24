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

FIRST_MESSAGE = u'scream into the void'

THUMB_MAX_HEIGHT = 360
THUMB_MAX_WIDTH = 360
MIN_COLORS = 2
MAX_COLORS = 10

SLEEP_RATE = 0.2
RETRY_TIME_MS = 3000

# God/admin
WHISPER_SECRET = 'lain'

# Maximum number of characters for memories.
MAX_CHARACTERS = 140

# If this is enabled an HTML audio player will
# appear in the footer and loop an MP3.
# BACKGROUND_MP3 = '/static/background.mp3'

# If this is enabled the specified MP3 is used
# as a notification for new messages.
NOTIFICATION_SOUND = '/static/notification.ogg'

ERROR_SOUND = '/static/error.ogg'

# Localization, Text, Messages
# A bunch of string values.
GOD_GREET = "Make everyone forget"
LOGIN_FAIL = "I don't think so."
GOD_GOODBYE = "Memory is your mistress."

# ERRORS
ERROR_TOO_LONG = u"Too long!"
ERROR_UNORIGINAL = u"Unoriginal!"
ERROR_RATE_EXCEEDED = u"Not so fast!"
ERROR_DANBOORU = u"No matches!"
