"""Module with a companion class for handling the use transparent colors."""
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
from typing import List, Union

from PIL import Image
from ordered_set import OrderedSet


class TransparencyHandler:
    def __init__(self, transparent_color):
        self.transparent_color = transparent_color
        self.transparency_map = []

    def collect_and_remove_transparency(self, img: Image.Image):
        """
        Get all pixels in img that match the transparent color. It must be a RGB mode image.
        The pixels are replaced with the last read non-transparent color, black if none was found.
        """
        if self.transparent_color is None:
            return
        last_color = (0, 0, 0)
        for i, px in enumerate(img.getdata()):
            y = math.floor(i / img.width)
            x = i % img.width
            if px == self.transparent_color:
                self.transparency_map.append(True)
                img.putpixel((x, y), last_color)
            else:
                self.transparency_map.append(False)
                last_color = px

    def update_palettes(self, palettes: List[Union[None, OrderedSet]]) -> List[Union[None, OrderedSet]]:
        """
        Add the index for this transparent color to all palettes that are not None.
        The index is not filled with a color yet, this is done in set_transparent_color_in_palettes.
        """
        new_palettes = []
        for p in palettes:
            if p is not None:
                new_palettes.append(OrderedSet([None] + list(p)))
            else:
                new_palettes.append(None)
        return new_palettes

    def set_transparent_color_in_palettes(self, palettes: List[Union[None, OrderedSet]]) -> List[Union[None, List]]:
        """
        Set the first color in all None palettes to self.transparent_color or (0, 0, 0) if not defined
        """
        tc = self.transparent_color if self.transparent_color is not None else (0, 0, 0)
        new_palettes = []
        for p in palettes:
            if p is not None:
                new_palettes.append([tc] + list(p[1:]))
            else:
                new_palettes.append(None)
        return new_palettes

    def update_pixels(self, img_width, w_in_tiles, h_in_tiles, colors_per_palettes,
                      tile_width, tile_height, indexed_pixels):
        """
        Update indexed_pixels by setting the pixels in all tiles, that were originally self.transparent_color
        back to this color (their local color 0).
        """
        if self.transparent_color is None:
            return

        for tx in range(0, w_in_tiles):
            for ty in range(0, h_in_tiles):
                palette_for_tile = math.floor(indexed_pixels[
                                                  (ty * tile_height * img_width) + (tx * tile_width)
                                              ] / colors_per_palettes)
                print(palette_for_tile)
                for x in range(tx * tile_width, (tx + 1) * tile_width):
                    for y in range(ty * tile_height, (ty + 1) * tile_height):
                        if self.transparency_map[y * img_width + x]:
                            indexed_pixels[y * img_width + x] = palette_for_tile * colors_per_palettes
