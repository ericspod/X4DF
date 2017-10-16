
# X4DF
# Copyright (C) 2017 Eric Kerfoot, King's College London, all rights reserved

from .x4df import readFile, writeFile, idTransform, validFieldTypes, ASCII, BASE64, BASE64_GZ, BINARY, BINARY_GZ, NODE, ELEM, INDEX
from .x4df import dataset, meta, nodes, topology, field, imagedata, mesh, image, transform, array

__appname__='x4df'
__version_info__=(0,1,0) # global application version, major/minor/patch
__version__='%i.%i.%i'%__version_info__
__author__='Eric Kerfoot'
__copyright__="Copyright (c) 2016-7 Eric Kerfoot, King's College London, all rights reserved. Licensed under the GPL (see LICENSE.txt)."
__website__="https://ericspod.github.io/X4DF"
