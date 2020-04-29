LaserG
======

_Experimental_ image to gcode converter for laser engravers.

This script was originally written for exposing photosensitive dry film coated copper boards to uv laser light.

It can also be used to convert regular images to gcode.

To setup the process, you have to configure the parameters in the laserg.py file. It's somewhere at the end. Sorry no funky user interface.

Process for PCBs
----------------

* Export the layers of your board in KiCad to a SVG file using the Plotter dialog.
* Convert the SVG using Inkscape to a PNG. Make sure you have entered a good dpi value. I use at least 600 dpi.
* Edit the script parameters and run the script. This may take a while.
* Verify the generated output file using a gcode processor like Candle and click 'Send'.

TODO?!
------

* Align multiple masks.
* Make the script more user friendly and handy. Expose the parameters as command line arguments.