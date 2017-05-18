
# X4DF
# Copyright (C) 2017 Eric Kerfoot, King's College London, all rights reserved

from x4df import __appname__,__version__
from setuptools import setup

setup(
	name = __appname__,
	version = __version__,
	packages=['x4df'],
	author='Eric Kerfoot',
	author_email="eric.kerfoot@kcl.ac.uk",
	url="http://github.com/ericspod/x4df",
	license="MIT",
	description='Extensible 4D Data Fields',
	keywords="python medical imaging mesh images",
)
