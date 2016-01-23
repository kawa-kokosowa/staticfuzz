# STATICFUZZ

http://staticfuzz.com/

A board for ten anonymous memories. Each new memory replaces the oldest. 

## Why use?

  * Efficient: asynchronous, server sent event (SEE/EventSource)
  * Easy to configure: `config.py`
  * Great notification system

## Running

  1. `pip install -r requirements.txt`
  2. `python staticfuzz.py initdb`
  2. `python staticfuzz.py serve`

Then you open http://localhost:5000/ in a web browser.

God is `lain` and password is `bear`.

## Creating your own SlashCommand

Create a class which inherits from `SlashCommand`, has a class constant
`NAME` which is the command used to execute the command, without the slash.

Add a `@staticmethod` called `callback` which returns a `SlashCommandResponse`
object. That's it! Example:

```python
class AddCouple(SlashCommand):
    NAME = 'add`

    @staticmethod
    def callback(a, b):

        return SlashCommandResponse(True, a + b)
```

The above will add the two arguments supplied when the user
types something like `/add 4 9`. You can also do things like:

```python
class Sum(SlashCommand):
    NAME = 'sum`

    @staticmethod
    def callback(*args):

        return SlashCommandResponse(True, sum(args))
```

The above will save the sum of all arguments passed to the
database. So if you supply `/sum 1 2 3` it'd put 6 in the DB.

`callback()` does not need to take any arguments at all.

## Built with love

Free for commercial or any purpose (MIT license).

Crafted by [Hypatia Software Organization](http://hypatia.software/).
