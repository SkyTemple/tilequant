"""Converts any image to an image using the color restrictions of PMD2 tiled images"""
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

import os
import shutil
import subprocess
import sys
import tempfile
from ctypes import cdll, c_int, POINTER, c_uint8, c_int32, memmove, byref, c_float
from enum import Enum, auto
from typing import List, Optional
import platform

from skytemple_tilequant.util import get_package_dir

try:
    from PIL import Image
except ImportError:
    from pil import Image

from skytemple_tilequant import logger, Color
from skytemple_tilequant.transparency_handler import TransparencyHandler


class TilequantError(RuntimeError):
    def __init__(self, message: str, error_out: str, error_err: str):
        self.message = message
        self.error_out = error_out
        self.error_err = error_err

    def __str__(self):
        return self.message + '\n' + self.error_out + '\n' + self.error_err


class DitheringMode(Enum):
    NONE = 0
    ORDERED = 3
    FLOYDSTEINBERG = -1


class AikkuImageConverter:
    """
    Converts any image into a indexed image containing a number of smaller sub-palettes, each with a fixed
    color length. 
    This is done using Aikku93's Tilequant.
    """

    def __init__(self, img: Image.Image, transparent_color: Color=None, tile_width=8, tile_height=8, dl_name=None):
        """
        Init.
        :param img:                 Input image. Is converted to RGB, alpha channel ist removed.
        :param transparent_color:   A single RGB color value that should be treated as transparent, when doing
                                    the conversion with transparency enabled.
        :param tile_width:          Width of a tile
        :param tile_height:          Height of a tile
        :param dl_name:             Path to the DLL or SO file for Tilequant, if not given, will auto-detect.
        """
        assert img.width % tile_width == 0, f"The image width must be divisible by {tile_width}"
        assert img.height % tile_height == 0, f"The image height must be divisible by {tile_height}"
        self._img = img.convert('RGBA').convert('RGBa')
        self._transparent_color = None
        if transparent_color is not None:
            self._transparent_color = (transparent_color[0], transparent_color[1], transparent_color[2], 255)
        self.tile_width = tile_width
        self.tile_height = tile_height
        # The created image
        self._out_img: Optional[Image.Image] = None
        self._reset(0, 0)

        # Init the library
        if dl_name is None:
            # Try autodetect / CWD
            try:
                if platform.system().lower().startswith('windows'):
                    dl_name = "libtilequant.dll"
                    os.add_dll_directory(os.getcwd())
                elif platform.system().lower().startswith('linux'):
                    dl_name = "libtilequant.so"
                elif platform.system().lower().startswith('darwin'):
                    dl_name = "libtilequant.so"
                else:
                    RuntimeError(f"Unknown platform {platform.system()}, can't autodetect DLL to load.")

                self.lib = cdll.LoadLibrary(dl_name)
            except OSError:
                # Okay now try the package directory
                dl_name = os.path.dirname(os.path.realpath(__file__))
                if platform.system().lower().startswith('windows'):
                    os.add_dll_directory(dl_name)
                    dl_name = os.path.join(dl_name, "libtilequant.dll")
                elif platform.system().lower().startswith('linux'):
                    dl_name = os.path.join(dl_name, "libtilequant.so")
                elif platform.system().lower().startswith('darwin'):
                    dl_name = os.path.join(dl_name, "libtilequant.so")

                self.lib = cdll.LoadLibrary(dl_name)
        else:
            if platform.system().lower().startswith('windows'):
                os.add_dll_directory(os.path.dirname(dl_name))
                dl_name = os.path.basename(dl_name)

            self.lib = cdll.LoadLibrary(dl_name)

        self.lib.QualetizeFromRawImage.argtypes = (
            c_int, c_int, POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8), POINTER(c_uint8), c_int, c_int,
            c_int, c_int, c_int, c_int, POINTER(c_int32), c_uint8 * 4, c_int, c_float
        )
        self.lib.QualetizeFromRawImage.restype = c_int

        logger.info("[%s] Initialized.", id(self))

    # noinspection PyAttributeOutsideInit
    def _reset(self, num_palettes, colors_per_palette):
        # Number of colors per palette. Minimum is 1, the first color is always transparency.
        self._colors_per_palette = colors_per_palette
        # Maximum number of palettes to generate
        self._num_palettes = num_palettes
        # Transparency handler object or None if transparency is disabled
        self._transparency = TransparencyHandler(self._transparent_color)

    def convert(
            self, num_palettes=16, colors_per_palette=16, dithering_mode: DitheringMode = DitheringMode.ORDERED,
            dithering_level = 1.0
    ) -> Image.Image:
        """
        Perform the conversion, returns the converted indexed image.

        It's highly recommended you pre-quantize the input image (=reduce the colors), because PIL (the used
        library) isn't very good at it. Use num_palettes*colors_per_palette colors for this.

        :param num_palettes:            Number of palettes in the output
        :param colors_per_palette:      Number of colors per palette. If transparency is enabled, the first color in
                                        each palette is reserved for it.
        :param dithering_mode:          Dithering mode to use.
        :param dithering_level:         Scale of the dither (0.0 = No dither, 1.0 = Full dither).

        :return: The converted image. It will contain a palette that consists of all generated sub-palettes, one
                 after the other.
        """
        self._reset(num_palettes, colors_per_palette)
        logger.info("[%s] Started converting. "
                    "num_palettes=%d, colors_per_palette=%d",
                    id(self), self._num_palettes, self._colors_per_palette)

        # Collect transparent tiles
        self._transparency.collect_and_remove_transparency(self._img, True)

        # Execute Aikku's Tilequant
        self._out_img = self._execute_tilequant(dithering_mode, dithering_level)

        # Iterate one last time and assign the final pixel colors and then build the image from it
        return self._out_img

    def _execute_tilequant(self, dithering_mode: DitheringMode, dithering_level: float) -> Image.Image:
        dst_px_idx = (c_uint8 * (self._img.width * self._img.height))()
        dst_pal = (c_uint8 * (self._num_palettes * self._colors_per_palette * 4 * 4))()

        img_data_bytes = self._img.tobytes('raw', 'BGRa')
        img_data = (c_uint8 * len(img_data_bytes))()
        memmove(byref(img_data), img_data_bytes, len(img_data_bytes))

        self.lib.QualetizeFromRawImage(
            self._img.width, self._img.height,
            img_data, None, dst_px_idx, dst_pal, 1, True,
            self._num_palettes, self._colors_per_palette,
            self.tile_width, self.tile_height, None,
            (c_uint8 * 4)(*[31, 31, 31, 1]), dithering_mode.value, dithering_level
        )

        out = Image.frombuffer('P', (self._img.width, self._img.height), dst_px_idx, 'raw', 'P', 0, 1)
        out.putpalette(dst_pal[:3 * 256])

        return out
