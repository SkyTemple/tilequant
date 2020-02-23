from setuptools import setup, find_packages

# README read-in
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# END README read-in

setup(
    name='tilequant',
    version='0.0.1',
    packages=find_packages(),
    description='Tool for quantizing image colors using tile-based palette restrictions',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/SkyTemple/skytemple-tilequant/',
    install_requires=[
        "Pillow-SIMD>=6.0.0",
        "ordered-set>=3.1.0",
        "sortedcollections>=1.1.0",
        "click>=7.0"
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Topic :: Multimedia :: Graphics',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    entry_points='''
        [console_scripts]
        tilequant=skytemple_tilequant.cli:main
    ''',
)
