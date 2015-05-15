![wYPeboard](http://www.power-xs.net/opcode/nop/software/external/wypeboard.jpg)

wYPeboard is a virtual whiteboard that is optimized for usability. In particular, it features the following:
 
- standard drawing functions (pen, eraser, geometric shapes, text, colour selection)
- indicators for the positions of the cursors of remote users, so you can conveniently point at things
- endless canvas, i.e. you can infinitely scroll the whiteboard in all directions 
- fully object-based editing, so you can easily move things around and partially delete content if need be.
- the state of the whiteboard can be saved and restored at any time, e.g. to continue the session at a later time 

The development of wYPeboard was spawned by a lackluster experience with existing virtual whiteboard software. Since wYPeboard was written in Python, a usable version could be developed within just a few days for my own use. Python was chosen because it is multi-platform and provides a good selection of libraries that could be used as a basis. wYPeboard was specifically optimized for use under Windows and Linux.

## Prerequisites ##

To run the source version of wYPeboard, you will need to have the following software installed:

- [Python 2.x](https://www.python.org/downloads/ "Python 2.x") version 2.7 or newer
- [wxPython](http://www.wxpython.org/ "wxPython")
- [pygame](http://www.pygame.org/download.shtml "pygame")

## Usage ##

To run wYPeboard, run the Python script `sync.py`. Additional information on usage will then be provided. One of the users is to run wYPeboard as a server, which the others can then connect to as clients. Naturally, for connections to be established, a port on the computer running the server must be reachable (which may necessitate changes to the home networks routing or firewall configuration).

To run wYPeboard without networking, run the Python script `whiteboard.py`.