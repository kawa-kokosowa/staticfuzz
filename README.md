# staticfuzz

[![Travis](https://img.shields.io/travis/hypatia-software-org/staticfuzz.svg?style=flat-square)](https://travis-ci.org/hypatia-software-org/staticfuzz)
[![Code Climate](https://img.shields.io/codeclimate/github/hypatia-software-org/staticfuzz.svg?style=flat-square)](https://codeclimate.com/github/hypatia-software-org/staticfuzz)

See it live: http://staticfuzz.com/

Memories which vanish. Live message board, in the spirit of
early anonymous message boards, like http://www.2ch.net/ and
[Kareha](https://wakaba.c3.cx/s/web/wakaba_kareha).

## Why use?

  * Memories only ever exist in memory (RAM)
  * Optionally, you can easily use a persistent database
  * Memories streamed live, asynchronously, with server-sent events
  * Easy to configure
  * Notification system
  * Easy-to-create "slash comamnds"
  * Miscellaneous mood settings (e.g., random backgrounds)
  * Easily config

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

Above will create a memory which text is the sum of the arguments, e.g.,
`/sum 1 2 3` would create a memory with the text `6`. If the user enters
something like `/sum 1 a 3` an HTTP error 400 is sent.

The first argument of `SlashCommandResponse` is a `bool`, if `True` it will
create a memory with the second argument, otherwise, the second arugment is
sent as a response.

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

Try posting a link to an image!

## Built with love

Free for commercial or any purpose (MIT license).

Crafted by [Hypatia Software Organization](http://hypatia.software/).
