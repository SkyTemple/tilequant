__version__ = '0.4.1.post0'
import platform

from setuptools import setup, find_packages

from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
from setuptools.command.develop import develop

import os
import shutil
import subprocess
import sys
from distutils.dist import Distribution


# README read-in
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# END README read-in


is_installed_develop = False
class BinaryDistribution(Distribution):
    def is_pure(self):
        return False

    def has_ext_modules(self):
        return True


# Bug in distutils; see https://github.com/google/or-tools/issues/616#issuecomment-371480314
class InstallPlatlib(install):
    def finalize_options(self):
        install.finalize_options(self)
        if self.distribution.has_ext_modules():
            self.install_lib = self.install_platlib


class Develop(develop):
    def run(self):
        global is_installed_develop
        is_installed_develop = True
        super().run()


class BuildExt(build_ext):
    """Compiles Aikku's tilequant."""
    def run(self):
        # Don't build in develop
        global is_installed_develop
        if is_installed_develop:
            return

        this_path = os.getcwd()
        path_repo = os.path.join(this_path, 'aikku93-tilequant')
        # Run the build script
        exes = self.build(path_repo)
        if not exes:
            print("Could not compile Tilequant.")
            print("")
            sys.exit(1)
        os.chdir(this_path)

        # Copy the libraries to the correct place
        for exe in exes:
            build_target = os.path.join(
                self.build_lib, 'skytemple_tilequant', 'aikku',
                os.path.basename(exe)
            )
            print(f"Copying {exe} -> {build_target}")
            shutil.copyfile(exe, build_target)

    def build(self, p):
        os.chdir(p)
        print(f"BUILDING - make")
        if platform.system() != "Windows":
            retcode = subprocess.call(["make", "dll"])
        else:
            retcode = subprocess.call(["make", "dll", "DDECLSPEC=__declspec(dllexport)"])
        if retcode:
            return False
        exes = []
        without_exe_path = os.path.abspath(os.path.join(p, 'release', 'libtilequant.so'))
        with_exe_path = os.path.abspath(os.path.join(p, 'release', 'libtilequant.dll'))
        if os.path.exists(without_exe_path):
            exes.append(without_exe_path)
        if os.path.exists(with_exe_path):
            exes.append(with_exe_path)
        return exes

setup(
    name='tilequant',
    version=__version__,
    packages=find_packages(),
    description='Tool for quantizing image colors using tile-based palette restrictions',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/SkyTemple/tilequant/',
    install_requires=[
        'Pillow >= 6.1.0',
        "ordered-set>=3.1.0",
        "sortedcollections>=1.2.1",
        "click>=7.0"
    ],
    package_data={'skytemple_tilequant.aikku': ['libtilequant*']},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Topic :: Multimedia :: Graphics',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    entry_points='''
        [console_scripts]
        tilequant=skytemple_tilequant.aikku.cli:main
        tilequant_legacy=skytemple_tilequant.cli_legacy:main
    ''',
    distclass=BinaryDistribution,
    cmdclass={'build_ext': BuildExt, 'install': InstallPlatlib, 'develop': Develop}
)
