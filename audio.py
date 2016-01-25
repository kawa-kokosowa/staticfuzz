"""Glitch a wav file


"""

import io
import base64
import random
import urllib2
import mimetypes
from cStringIO import StringIO

import pydub


def glitch_audio(url_string):
    # get the image from the net
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib2.Request(url_string, None, headers)
    urlopen_result = urllib2.urlopen(req)
    urlopen_result_io = io.BytesIO(urlopen_result.read())

    sound = pydub.AudioSegment.from_file(urlopen_result_io, format="wav")

    # Glitch
    for n in range(1, 10):
        ms = random.randint(500, 1000)

        end_start = random.randint(ms, len(sound) - ms)
        start_end = end_start - ms

        beginning = sound[:start_end]
        ending = sound[end_start:]
        middle = sound[start_end:end_start]

        # now we glitch!
        new_segments = []

        for segment in (beginning, middle, ending):

            if range(0, 1):
                segment = segment.reverse()

            if range(0, 1):
                segment = segment.fade_out(ms)

            if range(0, 1):
                segment = segment.fade_in(ms)

            new_segments.append(segment)

        # chance to make segment backwards
        sound = new_segments[0] + new_segments[1] + new_segments[2]

    # Save
    sound_handle = sound.export(io.BytesIO(), format="wav")
    sound_handle.seek(0)
    sound_stringio = StringIO(sound_handle.read())
    sound_stringio.seek(0)

    base64_audio = base64.b64encode(sound_stringio.read())

    return base64_audio
