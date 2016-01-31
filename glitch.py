"""Glitch an image and make it look all cool. :3

"""

import io
import sys
import urllib2
import random
import base64

from flask import current_app as app
from PIL import Image, ImageOps
from cStringIO import StringIO


def atkinson_dither(pil_image):
    """Classic Mac 1 bit dither.

    Credit goes to Michal Migurski.

    http://mike.teczno.com/notes/atkinson.html

    """

    img = pil_image.convert('L')

    threshold = 128*[0] + 128*[255]

    for y in range(img.size[1]):

        for x in range(img.size[0]):

            old = img.getpixel((x, y))
            new = threshold[old]
            err = (old - new) >> 3 # divide by 8

            img.putpixel((x, y), new)

            for nxy in [(x+1, y), (x+2, y), (x-1, y+1), (x, y+1), (x+1, y+1), (x, y+2)]:

                try:
                    img.putpixel(nxy, img.getpixel(nxy) + err)
                except IndexError:
                    pass

    return img


def glitch_from_url(url_string):
    """This is the thumbnail generating function.

    """

    # get the image from the net
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib2.Request(url_string, None, headers)
    urlopen_result = urllib2.urlopen(req)
    urlopen_result_io = io.BytesIO(urlopen_result.read())

    # open and tweak the image
    # open, resize...
    tweaked_image = Image.open(urlopen_result_io)
    tweaked_image.thumbnail([app.config['THUMB_MAX_WIDTH'],
                             app.config['THUMB_MAX_HEIGHT']])

    # add artifacts/save as low quality jpeg
    # save as low quality jpg
    tweaked_image_io = StringIO()
    tweaked_image.save(tweaked_image_io, format="JPEG",
                       quality=random.randint(5, 20))
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

    max_colors = random.randint(app.config['MIN_COLORS'],
    app.config['MAX_COLORS'])
    tweaked_image = tweaked_image.convert(mode='P',
                                          palette=Image.ADAPTIVE,
                                          colors=max_colors)
    tweaked_image = atkinson_dither(tweaked_image)

    # we have a 1-bit image because of the atkinson dither,
    # now we must generate a random color and get its inverse
    first_color = (random.randint(0, 255),
                   random.randint(0, 255),
                   random.randint(0, 255))
    inverse_color = (abs(first_color[0] - 255),
                     abs(first_color[1] - 255),
                     abs(first_color[2] - 255))
                       
    tweaked_image = ImageOps.colorize(tweaked_image,
                                      first_color,
                                      inverse_color)

    # save the image as base64 HTML image
    glitch_image = StringIO()
    tweaked_image.save(glitch_image, "PNG", optimize=True)
    glitch_string = glitch_image.getvalue()
    base64_string = base64.b64encode(glitch_string)

    return base64_string
