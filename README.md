# STATICFUZZ

http://staticfuzz.com/

A board for ten anonymous memories. Each new memory replaces the oldest. 

## Why use?

  * Efficient: asynchronous, server sent event (SEE/EventSource)
  * Easy to configure: `config.py`
  * Great notification system
  * Easy to extend, add commands

## Running

  1. `pip install -r requirements.txt`
  2. `python staticfuzz.py initdb`
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

The above example saves the sum of the arguments (to the database), if
any of the arguments aren't a number, HTTP error 400 "x is not a number!"
is sent. If you supply `/sum 1 2 3` it will write `6` to the database. If
you supply `/sum a b c` a 400 (and the error message) will be returned back.

`callback()` does not need to take any arguments at all. It can take any
number of arguments, something like `def callback(only_one):` works!

### Included

  * `/login secret`: login so you can delete memories. sadly, you need to
    manually refresh after logging in. Try `/login lain` (default).
  * `/logout`: if you are logged in, this will log you out. again, you need
    manually refresh after.
  * `/danbooru search some tags`: Get a random image from
    [Danbooru](http://danbooru.donmai.us/) which matches the supplied tags.

## Built with love

Free for commercial or any purpose (MIT license).

Crafted by [Hypatia Software Organization](http://hypatia.software/).
