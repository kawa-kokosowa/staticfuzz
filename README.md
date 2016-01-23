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
object. That's it!

## Built with love

Free for commercial or any purpose (MIT license).

Crafted by [Hypatia Software Organization](http://hypatia.software/).
