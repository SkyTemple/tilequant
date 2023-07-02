#!/usr/bin/env python
import platform

from setuptools import find_packages
from setuptools_dso import DSO, setup
from setuptools_dso.probe import ProbeToolchain


def define_DSOs(cmd):
    probe = ProbeToolchain()
    assert probe.check_include('stdlib.h')
    assert probe.check_include('stdint.h')
    assert probe.check_include('stddef.h')

    macros = []
    if platform.system() == "Windows":
        macros.append(('DECLSPEC', '__declspec(dllexport)'))
    else:
        macros.append(('DECLSPEC', ''))

    dso = DSO('tilequant', [
            'aikku93-tilequant/Bitmap.c',
            'aikku93-tilequant/Quantize.c',
            'aikku93-tilequant/Dither.c',
            'aikku93-tilequant/Qualetize.c',
            'aikku93-tilequant/Tiles.c',
            'aikku93-tilequant/tilequantDLL.c',
        ],
        define_macros=macros,
        include_dirs=['aikku93-tilequant'],
    )

    return [dso]


setup(
    name="tilequant",
    packages=find_packages(),
    include_package_data=True,
    x_dsos=define_DSOs,
)
