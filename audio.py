"""sample: https://upload.wikimedia.org/wikipedia/commons/c/c8/Example.ogg"""

import base64
import random
import urllib2
import mimetypes

from cStringIO import StringIO


def glitch_audio(url_string):
    """Downsample, convert to ogg in future"""

    # get the image from the net
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib2.Request(url_string, None, headers)
    urlopen_result = urllib2.urlopen(req)
    urlopen_result_io = StringIO(urlopen_result.read())

    audio_string = urlopen_result_io.read()
    base64_audio = base64.b64encode(audio_string)

    return base64_audio
