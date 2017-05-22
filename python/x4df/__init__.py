
# X4DF
# Copyright (C) 2017 Eric Kerfoot, King's College London, all rights reserved

from .x4df import readFile, writeFile, idTransform, validFormats, validFieldTypes
from .x4df import x4df, meta, nodes, topology, field, imagedata, mesh, image, transform,array

__appname__='x4df'
__version_info__=(0,1,0) # global application version, major/minor/patch
__version__='%i.%i.%i'%__version_info__
