# STATICFUZZ

[![Code Climate](https://img.shields.io/codeclimate/github/hypatia-software-org/staticfuzz.svg)]()
[![Travis](https://img.shields.io/travis/hypatia-software-org/staticfuzz.svg)]()

http://staticfuzz.com/

A board for ten anonymous memories. Each new memory replaces the oldest. 

## Why use?

  * Efficient: asynchronous, server sent event (SEE/EventSource)
  * Easy to configure: `config.py`
  * Great notification system
  * Easy to extend, add commands
  * Nothing is ever written to disk! If you want, STATICFUZZ *can*
    use just about any database system. All user data is temporary
    text, or base64 representations of images and sounds.

## Running

  1. `pip install -r requirements.txt`
  2. `cp config-example.py config.py`
  2. `python staticfuzz.py serve`

Then you open http://localhost:5000/ in a web browser.

## Creating your own SlashCommand

Create a class which inherits from `SlashCommand`, has a class constant
`NAME` which is the command used to execute the command, without the slash.

Add a `@staticmethod` called `callback` which returns a `SlashCommandResponse`
object. That's it! Example:

```python
class Sum(SlashCommand):
    NAME = 'sum`

    @staticmethod
    def callback(*args):

        for arg in args:
            
            try:
                __ = int(arg)
            except ValueError:

                return SlashCommandResponse(False, ("%s is not a number!" % arg, 400))

        return SlashCommandResponse(True, sum(args))
```

The above saves the sum of arguments to the database. The first arg of
`SlashCommandResponse` is a `bool`: if `True`, the result is saved to
the database, otherwise it's sent to the visitor as a response. If any
of the supplied arguments aren't a number, response is HTTP error 400.
If you supply `/sum 1 2 3` it will write `6` to the database. If you
input `/sum a b c` a 400 will be served.

`callback()` does not need to take any arguments at all. It can take any
number of arguments, something like `def callback(only_one):` works!

### Included

  * `/login secret`: login so you can delete memories. sadly, you need to
    manually refresh after logging in. Try `/login lain` (default).
  * `/logout`: if you are logged in, this will log you out. again, you need
    manually refresh after.
  * `/danbooru search some tags`: Get a random image from
    [Danbooru](http://danbooru.donmai.us/) which matches the supplied tags.

## Other features

  * Images: post a link to an image.
  * Audio: post a link to a `.wav` audio file.

Both images and audio are stylistically randomly glitched, but you can
have audio and images handled however you want!

## Built with love

Free for commercial or any purpose (MIT license).

Crafted by [Hypatia Software Organization](http://hypatia.software/).
