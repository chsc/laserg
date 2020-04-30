LaserG
======

_Experimental Software_

This script was originally written for exposing photosensitive dry film coated copper boards to uv laser light using *KiCad* plot files.

It can also be used to convert regular images to gcode.

To setup the process, you have to configure the parameters in the laserg.py file. It's somewhere at the end. Sorry, no funky user interface.

Process for PCBs
----------------

* USe the plotting dialog to export the layers of your KiCad board to SVG.

  Select at least the follwing outputs:
  * Edge cuts (used to calculate the board size)
  * Copper F or B

  Silk, Mask, and Paste are optional.
* Edit the script parameters and run the script. This may take a while. Inkscape must be installed! It will be used to convert the SVGs to PNGs.
* Verify the generated output files using a gcode processor like Candle.

TODO?!
------

* Make the script more user friendly and handy. Expose the parameters as command line arguments.
* Code is a quite a bit hacky. Clean up!
* Better test file.