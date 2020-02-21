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
import logging
from typing import Tuple, List

from PIL import Image
from PIL.Image import NONE

from ordered_set import OrderedSet

from skytemple_tilequant.palette_merger import PaletteMerger

logging.basicConfig()
logger = logging.getLogger('skytemple_tilequant')
Color = Tuple[int, int, int]


class ImageConverter:
    """
    Converts any image into a indexed image containing a number of smaller sub-palettes, each with a fixed
    color length. The conversion will assign each tile in the image one of these sub-palettes
    to use (single-palette-per-tile constraint).
    To meet this constraint the converter will continue to reduce the overall image colors using color
    quantization until each tile can be assigned a palette.
    """

    def __init__(self, img: Image.Image, tile_width=8, tile_height=8):
        """
        Init.
        :param img:         Input image
        :param tile_width:  The width of each tile in img. img must be divisible by this.
        :param tile_height: The height of each tile in img. img must be divisible by this.
        """
        assert img.width % tile_width == 0, f"The image width must be divisible by {tile_width}"
        assert img.height % tile_height == 0, f"The image height must be divisible by {tile_height}"
        self._img = img.convert('RGB')
        self._tile_width = tile_width
        self._tile_height = tile_height
        self._reset(0, 0, 0, 0, NONE, 0, False)
        # TODO: Flag --transparency-color
        # TODO: Flag --without-transparency (currently implemented!)
        logger.info("[%s] Initialized. tile_width=%d, tile_height=%d", id(self), self._tile_width, self._tile_height)

    # noinspection PyAttributeOutsideInit
    def _reset(self, num_palettes, colors_per_palette, color_steps,
               current_color_count, dither, color_limit_per_tile, mosaic_limiting):
        # Number of colors per palette. Minimum is 1, the first color is always transparency.
        self._colors_per_palette = colors_per_palette
        # Maximum number of palettes to generate
        self._num_palettes = num_palettes
        # How many colors to subtract with each attempt of quantization
        self._color_steps = color_steps
        # The number of colors in the current image
        self._current_color_count = current_color_count
        # Which dithering algorithm to use
        self._dither = dither
        # The number of colors the tiles are initially limited to by the first simple tile quanting:
        self._color_limit_per_tile = color_limit_per_tile
        # See doc of convert for description of this flag
        self._mosaic_limiting = mosaic_limiting
        # List of all possible palettes
        # In the end this will contain any number of palettes, but they will be merged by self._merge_palettes
        # and only up to self._num_palettes entries in this list will not be None.
        self._palettes: List[Union[None, OrderedSet[Color]]] = []
        # Whether or not self._check_num_palette_constraint needs to perform a deep/hard merge check
        self._deep_merge_check_needed_for_run = False
        # A list where each entry is one image tile and the values are lists of possible indices from self._palettes,
        # that the tile could use
        self._palettes_for_tiles = []
        # All the colors that are currently in self._quantized_img
        self._current_colors = []
        # Version of self._img with it's colors reduced using PIL convert to palette image.
        # Based on this image tilequant tries to fullfill the single-palette-per-tile constraint.
        self._quantized_img = self._img.copy()
        # For debugging:
        self._dbg_last_tile_quantized_img = None
        # Object that builds merge strategies for palettes
        self._merger = None
        # The indices of this map are the real final palette indices and the entries themselves
        # reference an entry in self._palette which may contain fair more palettes due to the way things
        # may be merged.
        self._real_palette_indices = list(range(0, self._num_palettes))

    def convert(self, num_palettes=16, colors_per_palette=16,
                color_steps=4, start_colors=None, dither=NONE,
                color_limit_per_tile=None, mosaic_limiting=True) -> Image.Image:
        """
        Perform the conversion, returns the converted indexed image.

        It's highly recommended you pre-quantize the input image (=reduce the colors), because PIL (the used
        library) isn't very good at it. Use num_palettes*colors_per_palette colors for this.

        :param dither:                  Which dithering mechanism to use. Possible values: NONE, FLOYDSTEINBERG.
        :param num_palettes:            Number of palettes in the output
        :param colors_per_palette:      Number of colors per palette
        :param color_steps:             Step interval for reducing the color count on conversion failures
        :param start_colors:            Number of colors to start with, None means num_palettes*colors_per_palette
        :param color_limit_per_tile:    Limit the tiles to a specifc amount of colors they should use. Setting this
                                        lower than colors_per_palette may help increase the number of
                                        total colors in the image.
        :param mosaic_limiting:         Enables or disables "mosaic limiting": If enabled, not only limit tiles like
                                        described in color_limit_per_tile, but also apply those limitations to larger
                                        areas of the image.
                                        Example for 8x8 tiles:
                                        [Always]:
                                            All 8x8 blocks   are limited to color_limit_per_tile      colors
                                        [If mosaic_limiting]:
                                            All 16x16 blocks are limited to color_limit_per_tile * 2  colors
                                            All 32x32 blocks are limited to color_limit_per_tile * 4  colors
                                            ... until the block size is the entire image

        :return: The converted image. It will contain a palette that consists of all generated sub-palettes, one
                 after the other.
        """
        if start_colors is None:
            start_colors = num_palettes * colors_per_palette
        if color_limit_per_tile is None:
            color_limit_per_tile = colors_per_palette
        self._reset(num_palettes, colors_per_palette, color_steps, start_colors,
                    dither, color_limit_per_tile, mosaic_limiting)
        logger.info("[%s] Started converting. "
                    "num_palettes=%d, colors_per_palette=%d, "
                    "color_steps=%d, start_colors=%d, color_limit_per_tile=%d, mosaic_limiting=%s, dither=%s",
                    id(self), self._num_palettes, self._colors_per_palette,
                    self._color_steps, start_colors, color_limit_per_tile, mosaic_limiting, dither)

        # TODO: If transparency, collect transparent tiles

        # TODO: With transparency subtract number of palettes
        if self._current_color_count <= 1:
            raise ValueError("The requested palette specs don't contain any colors.")
        # First do a tiled quantize: Reduce the colors of all tiles to their best self._color_limit_per_tile colors.
        # This will hopefully lead to better results.
        self._tiled_quantize(self._tile_width, self._tile_height, self._color_limit_per_tile)
        # If mosaic limiting is enabled, also apply these rules to larger portions of the image, see docstring:
        if mosaic_limiting:
            block_width = self._tile_width * 2
            block_height = self._tile_height * 2
            block_colors = self._color_limit_per_tile * 2
            while block_width < self._img.width and block_height < self._img.height:
                self._tiled_quantize(block_width, block_height, block_colors)
                block_width *= 2
                block_height *= 2
                block_colors *= 2

        # Do full first color limitation
        self._quantize()

        while not self._try_to_fit_palettes():
            self._current_color_count -= self._color_steps
            if self._current_color_count <= 1:
                raise RuntimeError("Was unable to quantize image: Had no colors left.")
            self._quantize()

        # If the palette count is > num_palettes, we need to merge palettes
        if len(self._palettes) > num_palettes:
            self._merge_palettes()

        # Iterate one last time and assign the final pixel colors and then build the image from it
        return self._build_image(self._index_pixels())

    def color_count(self):
        """The count of colors in the last converted image"""
        return self._current_color_count

    def _try_to_fit_palettes(self):
        """
        Goes over all pixels and builds local tile palettes from the current image colors.

        Fails if more full palettes than num_palettes would be required or if a tile contains more
        colors than colors_per_palette.

        On failure returns False, True otherwise. If no failure occurred, the _palettes
        field contains the palettes and the _palettes_for_tiles field the possible palette idxs the tiles could use

        Please note, that the number of palettes can be bigger than _num_palettes,
        because palettes might be able to be merged. If for example colors_per_palette is 8
        the end result may contain (num_palettes - 1) 8-color palettes and two 4-color
        palettes that could be merged.
        """
        # Reset _palettes and _out_img_data
        self._palettes = []
        self._palettes_for_tiles = [[] for _ in range(0, int(
            (self._img.width * self._img.height) / (self._tile_width * self._tile_height)
        ))]
        self._deep_merge_check_needed_for_run = False

        logger.info("[%s] Trying to fit palettes with %d total colors.",
                    id(self), self._current_color_count)

        # Iterate tiles:
        for ty in self._iterate_tiles_y():
            for tx in self._iterate_tiles_x():
                success = self._index_tile(tx, ty)
                if not success:
                    return False
        return self._check_num_palette_constraint()

    def _index_tile(self, tx, ty):
        current_local_tile_palette = OrderedSet()
        logger.debug("[%s] Processing tile %d x %d", id(self), tx, ty)

        # Collect all colors and try to fit them in palettes
        for y in range(ty * self._tile_height, (ty + 1) * self._tile_height):
            for x in range(tx * self._tile_width, (tx + 1) * self._tile_width):
                # TODO: With transparency, make sure cc_idx is still correct!
                cc_idx = self._quantized_img.getpixel((x, y))
                cc = self._current_colors[cc_idx]
                current_local_tile_palette.append(cc)

        if len(current_local_tile_palette) > self._colors_per_palette:
            # We don't even have to continue... This single tile already has to many colors
            logger.info("[%s] Tile %d x %d contains to many colors, aborting...", id(self), tx, ty)
            return False

        # Get possible palettes of the tile
        possible_palettes = self._get_suitable_palettes(
            current_local_tile_palette
        )
        if len(possible_palettes) < 1:
            # For performance reasons, the check here was removed. If the complex merge check is required, this
            # just takes too long here, do it at the end instead (end of _try_to_fit_palettes).
            # noinspection PyUnreachableCode
            if True:  # self._check_num_palette_constraint(self._tile_coord(tx, ty)):
                # No palette contains all colors... We need to create a new one
                possible_palettes = [len(self._palettes)]
                self._palettes.append(OrderedSet(current_local_tile_palette))
            else:
                # We can't add new palettes anymore because we would exceed num_palettes even when merging. Abort.
                logger.info("[%s] Impossible to limit image to %d palettes, aborting...", id(self), self._num_palettes)
                return False

        logger.debug("[%s] Tile %d x %d can use palettes %s", id(self), tx, ty, possible_palettes)
        self._palettes_for_tiles[self._tile_coord(tx, ty)] = possible_palettes
        return True

    def _tiled_quantize(self, block_width, block_height, color_limit):
        """
        Reduces the colors in each block of the image down to color_limit.
        Input: self._quantized_img
        Output: self._quantized_img
        """
        for tx in range(0, int(self._img.width / block_width)):
            for ty in range(0, int(self._img.height / block_height)):
                box = (
                    tx * block_width, ty * block_height,
                    (tx + 1) * block_width, (ty + 1) * block_height
                )
                img_tile = self._quantized_img.crop(box).convert(
                    'P', palette=Image.ADAPTIVE, colors=color_limit, dither=self._dither
                )
                self._quantized_img.paste(img_tile, box)
        self._dbg_last_tile_quantized_img = self._quantized_img.copy()

    def _quantize(self):
        """
        Reduces the colors in the entire image down to self._current_color_count
        Input: self._quantized_img
        Output: self._quantized_img
        :return:
        """
        logger.debug("[%s] Quantizing down to %d total colors.", id(self), self._current_color_count)
        # PIL is a bit broken, so convert to RGB again first.
        self._quantized_img = self._quantized_img.convert('RGB').convert(
            'P', palette=Image.ADAPTIVE, colors=self._current_color_count, dither=self._dither
        )
        it = iter(self._quantized_img.getpalette()[:self._current_color_count*3])
        # zip converts the palette into rgb tuples: [(r,g,b),(r,g,b)...]
        self._current_colors = list(zip(it, it, it))

    def _iterate_tiles_x(self):
        return range(0, int(self._img.width / self._tile_width))

    def _iterate_tiles_y(self):
        return range(0, int(self._img.height / self._tile_height))

    def _tile_coord(self, tx, ty):
        return int(self._img.width / self._tile_width) * ty + tx

    def _get_suitable_palettes(
            self, tile_pal: OrderedSet
    ) -> List[int]:
        """
        Check which palettes contain all colors of tile_pal.
        If tile_pal is instead a superset of any of the palettes, those palettes are updated with the colors
        from tile_pal.
        """
        possible = []
        for p_idx, p in enumerate(self._palettes):
            if tile_pal.issubset(p):
                possible.append(p_idx)
            elif tile_pal.issuperset(p):
                self._palettes[p_idx] = p.union(tile_pal)
                possible.append(p_idx)
        return possible

    def _check_num_palette_constraint(self):
        """
        Check if it's still possible with the palettes in self._palettes to get them down to
        a total of self._num_palettes of less, by merging
        :return:
        """

        palette_color_counts = [len(p) for p in self._palettes]
        logger.debug("[%s] Updating pal list... Currently have palettes with col counts: %s",
                     id(self), palette_color_counts)

        if not self._deep_merge_check_needed_for_run:

            # Easy case: We still have open slots
            if len(self._palettes) < self._num_palettes:
                return True

            # Slightly harder case:
            # Try and see if we could still easily merge to get under self._num_palettes
            if PaletteMerger.try_fast_merge(self._palettes.copy(), self._colors_per_palette, self._num_palettes):
                return True

        self._deep_merge_check_needed_for_run = True

        # Hardest case:
        # Try to find a way to merge by actually trying to find a merge path
        logger.debug("[%s] Have to do full merge find for palettes, please stand by...", id(self))
        self._merger = self._create_new_merger()
        return self._merger.try_to_merge()

    def _merge_palettes(self):
        """
        Merges the palettes and updates self._palette_for_tiles and self._real_palette_indices.
        self._real_palette_indices will contain a list of maximum self.number_palettes entries,
        that contains indices for the list self._palettes.
        Fills all palette slots removed during the merge in self._palettes with None, these are then skipped
        later for self._build_image.
        """
        # We can just re-use the information from last merger we used, if we already had to use one.
        logger.info("[%s] Merging palettes, please stand by...", id(self))
        if self._merger is None:
            self._merger = self._create_new_merger()
            assert self._merger.try_to_merge()

        palettes_to_delete = []
        for merge_step in self._merger.get_merge_operations():
            logger.debug("[%s] Performing merge step %s", id(self), merge_step)
            self._palettes[merge_step[0]] = self._palettes[merge_step[0]].union(self._palettes[merge_step[1]])
            # Set the other palette at this place to None
            self._palettes[merge_step[1]] = None
            assert len(self._palettes[merge_step[0]]) <= self._colors_per_palette
            for tile in self._palettes_for_tiles:
                try:
                    tile.remove(merge_step[1])
                    if merge_step[0] not in tile:
                        tile.append(merge_step[0])
                except ValueError:
                    pass  # Faster this way, than to check if in list first.

        # Now assign the real final indices (between 0 and num_palettes) of the palettes
        self._real_palette_indices = []
        for p_idx, p in enumerate(self._palettes):
            if p is not None:
                self._real_palette_indices.append(p_idx)
        assert len(self._real_palette_indices) <= self._num_palettes

    def _index_pixels(self):
        """
        Find the color value for the final palettes for each tile, with the single-palette-per-tile constraint
        in mind.
        """
        logger.debug("[%s] Building pixel data...", id(self))

        pxs = [0 for _ in range(0, self._img.width * self._img.height)]
        for tx in self._iterate_tiles_x():
            for ty in self._iterate_tiles_y():
                palette_for_tile = self._palettes_for_tiles[self._tile_coord(tx, ty)][0]
                real_final_index = self._real_palette_indices.index(palette_for_tile)
                index_first_col = real_final_index * self._colors_per_palette
                for x in range(tx * self._tile_width, (tx + 1) * self._tile_width):
                    for y in range(ty * self._tile_height, (ty + 1) * self._tile_height):
                        col = self._current_colors[self._quantized_img.getpixel((x, y))]
                        pxs[y * self._img.width + x] = index_first_col + self._palettes[palette_for_tile].index(col)
        return pxs

    def _build_image(self, indexed_pixels):
        """
        Build the final image from the provided pixel data and the palettes in self._palettes. None entries
        in self._palettes are skipped.
        """
        logger.debug("[%s] Building image...", id(self))

        im = Image.frombuffer('P', (self._img.width, self._img.height), bytearray(indexed_pixels), 'raw', 'P', 0, 1)
        cols = []
        processed_palette_count = 0
        for p in self._palettes:
            if p is None:
                continue
            processed_palette_count += 1
            # Fill rest of palette
            p = list(p)
            p.extend([(0, 0, 0)]*(self._colors_per_palette - len(p)))
            for r, g, b in p:
                cols.append(r)
                cols.append(g)
                cols.append(b)
        for i in range(processed_palette_count, self._num_palettes):
            cols += [0] * 3 * self._colors_per_palette
        im.putpalette(cols)
        return im

    def _create_new_merger(self):
        return PaletteMerger(
            self._palettes.copy(),
            self._num_palettes,
            self._colors_per_palette
        )
