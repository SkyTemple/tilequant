"""Converts any image to an image using the color restrictions of PMD2 tiled images"""
#  Copyright 2020 Parakoopa
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
import math
import os
import shutil
import subprocess
import sys
import tempfile
from itertools import chain
from typing import List, Optional

from skytemple_tilequant.util import get_package_dir

try:
    from PIL import Image
except ImportError:
    from pil import Image

from skytemple_tilequant import logger, Color
from skytemple_tilequant.transparency_handler import TransparencyHandler


TILE_WIDTH = TILE_HEIGHT = 8


class TilequantError(RuntimeError):
    def __init__(self, message: str, error_out: str, error_err: str):
        self.message = message
        self.error_out = error_out
        self.error_err = error_err

    def __str__(self):
        return self.message + '\n' + self.error_out + '\n' + self.error_err


class AikkuImageConverter:
    """
    Converts any image into a indexed image containing a number of smaller sub-palettes, each with a fixed
    color length. 
    This is done using Aikku93's Tilequant.
    """

    def __init__(self, img: Image.Image, transparent_color: Color=None):
        """
        Init.
        :param img:                 Input image. Is converted to RGB, alpha channel ist removed.
        :param transparent_color:   A single color value that should be treated as transparent, when doing
                                    the conversion with transparency enabled.
        """
        assert img.width % TILE_WIDTH == 0, f"The image width must be divisible by {TILE_WIDTH}"
        assert img.height % TILE_HEIGHT == 0, f"The image height must be divisible by {TILE_HEIGHT}"
        self._img = img.convert('RGB')
        self._transparent_color = transparent_color
        # The created image
        self._out_img: Optional[Image.Image] = None
        self._fh = None
        self._td = None
        self._reset(0, 0)
        logger.info("[%s] Initialized.", id(self))

    # noinspection PyAttributeOutsideInit
    def _reset(self, num_palettes, colors_per_palette):
        # Number of colors per palette. Minimum is 1, the first color is always transparency.
        self._colors_per_palette = colors_per_palette
        # Maximum number of palettes to generate
        self._num_palettes = num_palettes
        # Transparency handler object or None if transparency is disabled
        self._transparency = TransparencyHandler(self._transparent_color)
        if self._fh is not None:
            self._fh.close()
        if self._td is not None:
            shutil.rmtree(self._td)

    def __del__(self):
        if self._fh is not None:
            self._fh.close()
        try:
            if self._td is not None:
                shutil.rmtree(self._td)
        except OSError:
            pass

    def convert(self, num_palettes=16, colors_per_palette=16) -> Image.Image:
        """
        Perform the conversion, returns the converted indexed image.

        It's highly recommended you pre-quantize the input image (=reduce the colors), because PIL (the used
        library) isn't very good at it. Use num_palettes*colors_per_palette colors for this.

        :param num_palettes:            Number of palettes in the output
        :param colors_per_palette:      Number of colors per palette. If transparency is enabled, the first color in
                                        each palette is reserved for it.

        :return: The converted image. It will contain a palette that consists of all generated sub-palettes, one
                 after the other.
        """
        self._reset(num_palettes, colors_per_palette)
        logger.info("[%s] Started converting. "
                    "num_palettes=%d, colors_per_palette=%d",
                    id(self), self._num_palettes, self._colors_per_palette)

        # Collect transparent tiles
        self._transparency.collect_and_remove_transparency(self._img)

        # Execute Aikku's Tilequant
        self._out_img = self._execute_tilequant(self._img, self._num_palettes, colors_per_palette)

        # If transparency is enabled, update the palettes to include the transparent colors
        # and reindex the colors, including replacing colors that were originally the transparent
        # color with transparency.
        original_palettes = self._extract_palette(colors_per_palette)
        self._update_palette(
            self._transparency.set_transparent_color_in_palettes(
                original_palettes
            )
        )
        self._transparency.update_pixels(
            self._img.width,
            int(self._img.width / TILE_WIDTH),
            int(self._img.height / TILE_HEIGHT),
            self._colors_per_palette,
            TILE_WIDTH, TILE_HEIGHT,
            image=self._out_img
        )

        # Iterate one last time and assign the final pixel colors and then build the image from it
        return self._out_img

    def _execute_tilequant(self, orig_image: Image.Image, num_palettes, colors_per_palette) -> Image.Image:
        try:
            self._td = tmp = tempfile.mkdtemp(None, None, None)
            # Convert input image to bmp
            input_name = os.path.normpath(os.path.join(tmp, 'in.bmp'))
            output_name = os.path.normpath(os.path.join(tmp, 'out.bmp'))
            orig_image.save(input_name)

            # Run Tilequant
            try:
                prefix = os.path.join(get_package_dir(), '')
                if os.path.exists(f'{prefix}tilequant') and not sys.platform.startswith('win'):
                    import stat
                    st = os.stat(f'{prefix}tilequant')
                    if not st.st_mode & stat.S_IEXEC:
                        os.chmod(f'{prefix}tilequant', st.st_mode | stat.S_IEXEC)
                result = subprocess.Popen([f'{prefix}tilequant', input_name, output_name,
                                           str(num_palettes), str(colors_per_palette)],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT)
                retcode = result.wait()
            except FileNotFoundError as ex:
                raise FileNotFoundError("Tilequant could not be found. Something may have gone "
                                        "wrong during the installation.") from ex

            if retcode != 0:
                raise TilequantError("Aikku's Tilequant reported an error.",
                                     str(result.stdout.read(), 'utf-8'), str(result.stderr.read(), 'utf-8') if result.stderr else '')
            # Read output image
            self._fh = open(output_name, 'rb')
            return Image.open(self._fh)
        except (FileNotFoundError, TilequantError):
            raise
        except BaseException as ex:
            raise RuntimeError(f"Error while converting the colors: {ex}") from ex

    def _extract_palette(self, number_colors) -> List[List[Color]]:
        pal = memoryview(self._out_img.palette.palette)
        palettes: List[List[Color]] = []
        cur_palette = []
        for i in range(0, len(pal), 4):
            if i % (number_colors * 4) == 0:
                cur_palette = []
                palettes.append(cur_palette)
            cur_palette.append((pal[i + 2], pal[i + 1], pal[i + 0]))
        return palettes

    def _update_palette(self, new_palette: List[List[Color]]):
        out: List[int] = []
        for p in new_palette:
            for r, g, b in p:
                out.append(r)
                out.append(g)
                out.append(b)
        self._out_img.putpalette(out)
