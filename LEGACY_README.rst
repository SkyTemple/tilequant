tilequant_legacy
================

This is the README for old legacy version of Tilequant. You can execute it via ``tilequant_legacy``.

Usage
-----

.. code::

    Usage: tilequant_legacy [OPTIONS] INPUT_IMAGE OUTPUT_IMAGE

      Converts any image into a indexed image containing a number of smaller
      sub-palettes (--num-palettes), each with a fixed color length (--colors-
      per-palette). The conversion will assign each tile in the image one of
      these sub-palettes to use (single-palette-per-tile constraint). To meet
      this constraint the converter will continue to reduce the overall image
      colors using color quantization until each tile can be assigned a palette.

      INPUT_IMAGE is the path of the image to convert and OUTPUT_IMAGE is where
      to save the converted image. All image types supported by PIL (the Python
      image library) can be used. :return:

    Options:
      -w, --tile-width INTEGER        [Default: 8] The width of each tile in the
                                      image, it must be divisible by this.
      -h, --tile-height INTEGER       [Default: 8] The height of each tile in the
                                      image, it must be divisible by this.
      -n, --num-palettes INTEGER      [Default: 16] Number of palettes in the
                                      output.
      -c, --colors-per-palette INTEGER
                                      [Default: 16] Number of colors per palette.
                                      If transparency is enabled, the first color
                                      in each palette is reserved for it.
      -C, --max-colors INTEGER        [Default: (-c)*(-n)] Highest overall amount
                                      of colors to test.
      -s, --color-steps INTEGER       [Default: 4] By how much to reduce the
                                      number of colors in the image, until a valid
                                      image is found.
      -d, --direction [DOWN|UP]       [Default: UP] Either start with the lowest
                                      amount of colors and go up to max-colors
                                      (UP), orthe other way around (DOWN). See
                                      README for more info.
      -D, --dither [NONE|FLOYDSTEINBERG]
                                      [Default: NONE] Which dither to use.
      -l, --color-limit-per-tile INTEGER
                                      [Default: 15] Limit the tiles to a specific
                                      amount of colors they should use before
                                      starting. Setting this lower than --colors-
                                      per-palette may help increase the number of
                                      total colors in the image.
      -M, --mosaic-limiting / -m, --no-mosaic-limiting
                                      [Default: Enabled] Toggle mosaic limiting,
                                      enabling it will limit increasingly bigger
                                      sections of the image to a limited amount of
                                      colors, based on --color-limit-per-tile. See
                                      README.
      -t, --transparent-color TEXT    A single color value (hex style, eg. 12ab56)
                                      that should be treated as transparent, when
                                      doingthe conversion with transparency
                                      enabled.
      -A, --transparency / -a, --no-transparency
                                      [Default: Enabled] Toggle transparency. If
                                      on, reserve the first color of each palette
                                      for transparencyand import pixels with the
                                      color code specified by transparent-color as
                                      transparency (if given).
      -v, --loglevel [DEBUG|INFO|WARNING|ERROR|FATAL|CRITICAL]
                                      [Default: INFO] Log level.
      --help                          Show this message and exit.


Examples
--------
The examples directory contains more examples. Most of the example images are taken from
https://github.com/haroldo-ok/RgbQuant-SMS.js.

Please note, that for the examples, the ``--transparency`` flag was enabled, so
the actual maximum of unique colors is 240 for those, since 16 colors are reserved
for transparency.

You can see, that in some cases there are still weird glitches (most notably the
``smb3`` example).


"Direction" of the algorithm
----------------------------
The algorithm tries to find any amount of total colors, that can be
arranged to produce a valid image with the tile based palette restrictions.

It does this (by default) by starting with a very low amount of colors and working
up to ``--max-colors`` until it is no longer possible to produce a valid image (``--direction UP``).

If ``--direction DOWN`` it will instead start with the highest amount of colors and work down,
until a valid image was found. This will take a significant amount of time longer to process
but has a higher chance of finding images with a high amount of colors (since it's possible
some numbers of colors in between 0 and the maximum might not be usable simply for reasons
related to how colors are changed in the quantizing process).

It's recommended to leave this to the default settings to get images in a sane amount of time.
Should you however work with images that already or almost follow the tile restrictions,
set this to ``DOWN`` for better results.

Color limit per tile
--------------------
Before starting the process, tilequant will quantize each tile separately to ``color-limit-per-tile``
colors, to reduce the amount of overall color noise per tile. Lowering this value may increase
the overall amount of colors possible.

Mosaic limiting
---------------
If enabled, the process described in "Color limit per tile" is repeated for each bigger
section of the image with an increasing amount of colors.

Example::

    [Always]:
        All 8x8 blocks   are limited to color_limit_per_tile      colors
    [If mosaic_limiting]:
        All 16x16 blocks are limited to color_limit_per_tile * 2  colors
        All 32x32 blocks are limited to color_limit_per_tile * 4  colors
        ... until the block size is the entire image

This may increase the total number of colors possible even more, but may lead to blocky
looking images.

Transparency
------------
If transparency is enabled, the actual amount of colors per palette is one lower than specified
and a "transparency color" is added at index 0 of all palettes. If ``transparent-color`` is
specified, the image is scanned for pixels with this color first and in the end, those pixels
will be assigned their local "transparent color" index.
