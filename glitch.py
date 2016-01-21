"""Glitch an image and make it look all cool. :3

"""

import io
import urllib2
import random
import base64

from flask import current_app as app
from PIL import Image, ImageOps
from cStringIO import StringIO


def glitch_from_url(url_string):
    # get the image from the net
    urlopen_result = urllib2.urlopen(url_string)
    urlopen_result_io = io.BytesIO(urlopen_result.read())

    # open and tweak the image
    # open, resize...
    tweaked_image = Image.open(urlopen_result_io)
    tweaked_image.thumbnail([app.config['THUMB_MAX_WIDTH'],
                             app.config['THUMB_MAX_HEIGHT']])

    # save as low quality jpg
    tweaked_image_io = StringIO()
    tweaked_image.save(tweaked_image_io, format="JPEG", quality=10)
    tweaked_image = Image.open(tweaked_image_io)

    # autocontrast
    tweaked_image = ImageOps.autocontrast(tweaked_image)
    tweaked_image = ImageOps.equalize(tweaked_image)

    # solarize
    tweaked_image = ImageOps.solarize(tweaked_image,
                                      random.randint(1, 200))

    # random chance to flip
    if random.randint(0, 4):
        tweaked_image = ImageOps.mirror(tweaked_image)

    if random.randint(0, 4):
        tweaked_image = ImageOps.equalize(tweaked_image)

    # random chance to invert
    if random.randint(0, 2):
        tweaked_image = ImageOps.invert(tweaked_image)

    max_colors = random.randint(app.config['MIN_COLORS'],
    app.config['MAX_COLORS'])
    tweaked_image = tweaked_image.convert(mode='P',
                                          palette=Image.ADAPTIVE,
                                          colors=max_colors)

    # save the image as base64 HTML image
    glitch_image = StringIO()
    tweaked_image.save(glitch_image, "PNG", optimize=True)
    glitch_string = glitch_image.getvalue()

    # glitch right before encoding
    for i in range(1, random.randint(2, 3)):
        start_point = random.randint(len(glitch_string) / 2, len(glitch_string))
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
