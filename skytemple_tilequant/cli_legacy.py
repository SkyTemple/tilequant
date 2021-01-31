#  Copyright 2020-2021 Parakoopa and the SkyTemple Contributors
#
#  This file is part of SkyTemple.
#
#  SkyTemple is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SkyTemple is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.
import logging
import os

import click
from PIL.Image import FLOYDSTEINBERG, NONE
try:
    from PIL import Image
except ImportError:
    from pil import Image
from click import echo, ClickException

from skytemple_tilequant import logger
from skytemple_tilequant.image_converter import ImageConverter
from skytemple_tilequant.util import convert_hex_str_color_to_tuple


@click.command()
@click.argument('input_image', required=True)
@click.argument('output_image', required=True)
@click.option('-w', '--tile-width', required=False, type=int, default=8,
              help="[Default: 8] The width of each tile in the image, it must be divisible by this.")
@click.option('-h', '--tile-height', required=False, type=int, default=8,
              help="[Default: 8] The height of each tile in the image, it must be divisible by this.")
@click.option('-n', '--num-palettes', required=False, type=int, default=16,
              help="[Default: 16] Number of palettes in the output.")
@click.option('-c', '--colors-per-palette', required=False, type=int, default=16,
              help="[Default: 16] Number of colors per palette. If transparency is enabled, the first color in each "
                   "palette is reserved for it.")
@click.option('-C', '--max-colors', required=False, type=int,
              help="[Default: (-c)*(-n)] Highest overall amount of colors to test.")
@click.option('-s', '--color-steps', required=False, type=int, default=4,
              help="[Default: 4] By how much to reduce the number of colors in the image, until a valid image is found.")
@click.option('-d', '--direction', 'low_to_high', type=click.Choice(['DOWN', 'UP']),
              default='UP',
              help="[Default: UP] Either start with the lowest amount of colors and go up to max-colors (UP), or"
                   "the other way around (DOWN). See README for more info.")
@click.option('-D', '--dither', required=False, type=click.Choice(['NONE', 'FLOYDSTEINBERG']),
              default='NONE',
              help="[Default: NONE] Which dither to use.")
@click.option('-l', '--color-limit-per-tile', required=False, type=int, default=15,
              help="[Default: 15] Limit the tiles to a specific amount of colors they should use before starting. "
                   "Setting this lower than --colors-per-palette may help increase the number of total colors in the image.")
@click.option('--mosaic-limiting/--no-mosaic-limiting', '-M/-m', default=True,
              help="[Default: Enabled] Toggle mosaic limiting, enabling it will limit increasingly bigger sections of "
                   "the image to a limited amount of colors, based on --color-limit-per-tile. See README.")
@click.option('-t', '--transparent-color', type=str, required=False,
              help="A single color value (hex style, eg. 12ab56) that should be treated as transparent, when doing"
                   "the conversion with transparency enabled.")
@click.option('--transparency/--no-transparency', '-A/-a', default=True,
              help="[Default: Enabled] Toggle transparency. If on, reserve the first color of each palette for transparency"
                   "and import pixels with the color code specified by transparent-color as transparency (if given).")
@click.option('-v', '--loglevel', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL', 'CRITICAL']),
              default='INFO',
              help="[Default: INFO] Log level.")
def main(input_image, output_image, loglevel, transparent_color,
         tile_width, tile_height, low_to_high, dither, **kwargs):
    """
    Converts any image into a indexed image containing a number of smaller sub-palettes (--num-palettes), each with a
    fixed color length (--colors-per-palette). The conversion will assign each tile in the image one of
    these sub-palettes to use (single-palette-per-tile constraint).
    To meet this constraint the converter will continue to reduce the overall image colors using color
    quantization until each tile can be assigned a palette.

    INPUT_IMAGE is the path of the image to convert and OUTPUT_IMAGE is where to save the converted image. All image
    types supported by PIL (the Python image library) can be used.
    :return:
    """
    if low_to_high == 'UP':
        low_to_high = True
    else:
        low_to_high = False
    if dither == 'FLOYDSTEINBERG':
        dither = FLOYDSTEINBERG
    else:
        dither = NONE
    logger.setLevel(logging.getLevelName(loglevel))
    echo("Converting...")
    if not os.path.exists(input_image):
        raise ClickException("The input image doesn't exist.")
    with open(input_image, 'rb') as input_file:
        try:
            image = Image.open(input_file)
        except OSError:
            raise ClickException("The input image is not a supported image file.")
        try:
            print(kwargs)
            converter = ImageConverter(image, tile_width, tile_height,
                                       convert_hex_str_color_to_tuple(transparent_color))
            img = converter.convert(low_to_high=low_to_high, dither=dither, **kwargs)
        except RuntimeError as err:
            raise ClickException("The image could not be converted: " + str(err))
    echo(f"Saving image to {output_image}...")
    try:
        img.save(output_image)
    except OSError as err:
        raise ClickException("Error saving the image: " + str(err))


if __name__ == '__main__':
    main()
