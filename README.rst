tilequant
=========

|build| |pypi-version| |pypi-downloads| |pypi-license| |pypi-pyversions|

.. |build| image:: https://img.shields.io/github/workflow/status/SkyTemple/tilequant/Build,%20test%20and%20publish
    :target: https://pypi.org/project/tilequant/
    :alt: Build Status

.. |pypi-version| image:: https://img.shields.io/pypi/v/tilequant
    :target: https://pypi.org/project/tilequant/
    :alt: Version

.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/tilequant
    :target: https://pypi.org/project/tilequant/
    :alt: Downloads

.. |pypi-license| image:: https://img.shields.io/pypi/l/tilequant
    :alt: License (MIT)

.. |pypi-pyversions| image:: https://img.shields.io/pypi/pyversions/tilequant
    :alt: Supported Python versions

Tilequant is a utility to reduce the colors in an image (quantizing). The current version
is based on `Tilequant by Aikku93`_ (the same name is coincidental)).

It does so by limiting each tile (by default an area of 8x8 pixels) of the image
to a subset of colors (a palette). The whole image has one big palette that consists of
those smaller palettes.

This tool is a standalone part of SkyTemple, the ROM editor for
Pokémon Mystery Dungeon Explorers of Sky.
By default it produces images that can be used by SkyTemple.
However the images are probably also useful
for use with other games that have similar restrictions for backgrounds.

Make sure the input image is a RGB image without an alpha channel. The image library used
has some problems with converting other image types to RGB in some cases.

The output is an image with a palettes as shown in the example.

.. image:: https://github.com/SkyTemple/tilequant/raw/master/examples/export_example2.png

(This example is based on the old legacy version).

This tool is not affiliated with Nintendo, Spike Chunsoft or any of the parties involved in
creating Pokémon Mystery Dungeon Explorers of Sky. This is a fan-project.

Installation
------------
Python 3 is required.

Via pip3::

    pip3 install -U tilequant

Usage
-----

.. code::

    Usage: tilequant [OPTIONS] INPUT_IMAGE OUTPUT_IMAGE

      Converts any image into a indexed image containing a number of smaller
      sub-palettes (--num-palettes), each with a fixed color length (--colors-
      per-palette). The conversion will assign each tile in the image one of
      these sub-palettes to use (single-palette-per-tile constraint).

      INPUT_IMAGE is the path of the image to convert and OUTPUT_IMAGE is where
      to save the converted image. All image types supported by PIL (the Python
      image library) can be used. :return:

    Options:
      -n, --num-palettes INTEGER      [Default: 16] Number of palettes in the
                                      output.
      -c, --colors-per-palette INTEGER
                                      [Default: 16] Number of colors per palette.
                                      If transparency is enabled, the first color
                                      in each palette is reserved for it.
      -t, --transparent-color TEXT    A single color value (hex style, eg. 12ab56)
                                      that should be treated as transparent, when
                                      doingthe conversion with transparency
                                      enabled.
      -v, --loglevel [DEBUG|INFO|WARNING|ERROR|FATAL|CRITICAL]
                                      [Default: INFO] Log level.
      --help                          Show this message and exit.


Examples
--------
For the new version no examples exist yet. However to get a general idea, you can view
the examples of the old version in "examples".

Transparency
------------
The actual amount of colors per palette is one lower than specified
and a "transparency color" is added at index 0 of all palettes. If ``transparent-color`` is
specified, the image is scanned for pixels with this color first and in the end, those pixels
will be assigned their local "transparent color" index.

Legacy version
--------------
Originally (before integrating the new and much better newer version based on
`Tilequant by Aikku93`_) there was a pretty bad pure-Python
based version of this tool. It is still available and it's README can be found in the
``README_LEGAXY.rst``.

.. _Tilequant by Aikku93: https://github.com/Aikku93/tilequant

Package structure
-----------------
The ``skytemple_tilequant`` package contains the code for the legacy version and the
``skytemple_tilequant.aikku`` package contains the new one.

Special Thanks
--------------

- Aikku93
- Nerketur
- AntyMew
- psy_commando
