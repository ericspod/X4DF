# X4DF
# Copyright (C) 2017 Eric Kerfoot, King's College London, all rights reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
This module implements the X4DF IO routines and simple data structures. This is
all that's necessary to read and write X4DF files. The two important functions
for the user are:

readFile(obj_or_path):
    Read a X4DF file and return its data structure. The single argument
    is either a path to a file, a string containing the file data, or
    a file-like object which can be read to create the data structure.

writeFile(obj,obj_or_path,overwriteFiles=True):
    Write the data structure `obj' to `obj_or_path' which is either a
    path to a file or a file-like object the data is to be written into.
    If `overwriteFiles' is True then array files will be overwritten if
    necessary, otherwise array files are left untouched.

The data structure readFile() returns and writeFile() accepts is defined
by a set of record types with these mutable members:

    dataset   -- meshes images arrays meta
    meta      -- name val text children
    nodes     -- src initialnodes timestep meta
    topology  -- name src elemtype spatial meta
    field     -- name src timestep topology spatial fieldtype meta
    imagedata -- src timestep transform meta
    mesh      -- name timescheme nodes topologies fields meta
    image     -- name timescheme transform imagedata meta
    transform -- position rmatrix scale
    array     -- name shape dimorder type format offset filename data

The members of these types correspond to attributes and elements of the XML
definition for X4DF files. Optional attributes/elements will be None if not
present when reading and omitted if None when writing. Elements which occur
multiple times will always be represented by a list (which may be empty). The
value the non-list members store is either a single number of a string storing
the value for that attribute/element, with the exception of "timescheme" which
is a tuple of 2 numbers (start, step) and the members of "transform" which are
numpy arrays representing 3-vectors or a 3x3 matrix.

For example, "readFile('foo.x4df')" will return a dataset instance which `meshes'
contains a list of mesh instances, an `images' member containing a list of
`image' instance, an `arrays' member containing a list of `array' instances,
and a `metas' member containing a list of `meta' instances.

'''


import xml.etree.ElementTree as ET
from collections import OrderedDict
from StringIO import StringIO
import os
import base64
import gzip
import contextlib
import numpy as np

### Types and Definitions

def namedrecord(name,members):
    '''Returns a type with the given name and members like namedtuple but mutable and less efficient.'''
    members=[m.strip() for m in members.split(',' if ',' in members else None)]

    def _init(obj,*values,**kwvalues):
        for name,value in zip(members,values)+kwvalues.items():
            setattr(obj,name,value)

    def _str(obj):
        attrs=', '.join('%s=%r'%(m,getattr(obj,m)) for m in members)
        return '%s(%s)'%(name,attrs)

    tmembers={m:None for m in members}
    tmembers['__init__']=_init
    tmembers['__repr__']=_str
    tmembers['__iter__']=lambda obj:(getattr(obj,m) for m in members)

    return type(name,(),tmembers)


dataset=namedrecord('dataset','meshes images arrays metas')
meta=namedrecord('meta','name val text children')
nodes=namedrecord('nodes','src initialnodes timestep metas')
topology=namedrecord('topology','name src elemtype spatial metas')
field=namedrecord('field','name src timestep topology spatial fieldtype metas')
imagedata=namedrecord('imagedata','src timestep transform metas')
mesh=namedrecord('mesh','name timescheme nodes topologies fields metas')
image=namedrecord('image','name timescheme transform imagedata metas')
transform=namedrecord('transform','position rmatrix scale')
array=namedrecord('array','name shape dimorder type format offset filename data')

# valid array format names
ASCII='ascii' # ascii text containing whitespace-separated numbers
BASE64='base64' # base64 encoding of array binary data
BASE64_GZ='base64_gz' # base64 encoding of gzip compressed array binary data
BINARY='binary' # array binary data
BINARY_GZ='binary_gz' # gzip compressed array binary data

# valid array formats
validFormats=(ASCII, BASE64, BASE64_GZ, BINARY, BINARY_GZ)

# valid field type names
NODE='node' # per node field
ELEM='elem' # per element field
INDEX='index' # per topology index field

# valid field types
validFieldTypes=(NODE, ELEM, INDEX)

# identity transform object
idTransform=transform(np.array([0,0,0]),np.eye(3),np.array([1,1,1]))


def isIDTransform(obj):
    '''Returns True if `obj' is a transform object equivalent to the identity.'''
    return obj and np.all(obj.position==idTransform.position) and np.all(obj.scale==idTransform.scale) and np.all(obj.rmatrix==idTransform.rmatrix)


### Reading XML Functions

def parseNumString(val,dtype=float,sep=' '):
    '''Convert `val' into a numpy array of numbers.'''
    dtype=np.dtype(dtype)
    return np.fromstring(val.replace('\n',' '),dtype,sep=sep)


def parseType(type_):
    '''Convert type string into a numpy type with byte ordering.'''
    if type_[0] in ('>','<','='):
        return np.dtype(type_[1:]).newbyteorder(type_[0])
    else:
        return np.dtype(type_)


def readMeta(metas):
    '''Read the metadata list into a list of recursive meta objects.'''
    result=[]
    for m in metas:
        children=[]

        for mm in m:
            if mm.tag == 'meta':
                children+=readMeta([mm])
            else:
                children.append(mm)

            if mm.tail is not None:
                children.append(mm.tail)

        result.append(meta(m.get('name'),m.get('val'),m.text,children))

    return result


def readTimescheme(tree):
    '''Read a timescheme element into a (start,step) pair.'''
    if tree is not None:
        return (float(tree.get('start')),float(tree.get('step')))


def readTransform(tree):
    '''Read a transform element into a transform object.'''
    if tree is None:
        return None

#   pos,mat,scl=idTransform
#   if tree is not None:
    pos=parseNumString(tree.findtext('position','0 0 0'))
    mat=parseNumString(tree.findtext('rmatrix','1 0 0 0 1 0 0 0 1'))
    scl=parseNumString(tree.findtext('scale','1 1 1'))

    return transform(pos,mat,scl)


def readNodes(tree):
    '''Read a node element into a node object.'''
    return nodes(tree.get('src'),tree.get('initialnodes'),tree.get('timestep'),readMeta(tree.findall('meta')))


def readTopology(tree):
    '''Read a topology element into a topology object.'''
    return topology(tree.get('name'),tree.get('src'),tree.get('elemtype'),tree.get('spatial'),readMeta(tree.findall('meta')))


def readField(tree):
    '''Read a field element into a field object.'''
    return field(tree.get('name'),tree.get('src'),tree.get('timestep'),tree.get('topology'),tree.get('spatial'),tree.get('fieldtype'),readMeta(tree.findall('meta')))


def readImageData(tree):
    '''Read an imagedata element into an imagedata object.'''
    return imagedata(tree.get('src'),tree.get('timestep'),readTransform(tree.find('transform')),readMeta(tree.findall('meta')))


def readMesh(tree):
    '''Read a mesh element into a mesh object.'''
    name=tree.get('name')
    timescheme=readTimescheme(tree.find('timescheme'))
    nodes=map(readNodes,tree.findall('nodes'))
    topologies=map(readTopology,tree.findall('topology'))
    fields=map(readField,tree.findall('field'))
    metas=readMeta(tree.findall('meta'))

    return mesh(name,timescheme,nodes,topologies,fields,metas)


def readImage(tree):
    '''Read an image element into an image object.'''
    name=tree.get('name')
    timescheme=readTimescheme(tree.find('timescheme'))
    transform_=readTransform(tree.find('transform'))
    imagedata=map(readImageData,tree.findall('imagedata'))
    metas=readMeta(tree.findall('meta'))

    return image(name,timescheme,transform_,imagedata,metas)


def readArrayData(shape,dimorder,type_,format_,offset, fullfilename,sep,text):
    '''Read the data for an array from the file `fullfilename' if given otherwise from the `text' string value.'''
    assert format_ in validFormats
    assert fullfilename or text
    assert fullfilename or format_ not in validFormats[3:5], 'Binary data can only be stored in separate files'

    dtype_=parseType(type_)

    if format_==ASCII:
        arr=np.loadtxt(fullfilename or StringIO(text),dtype_,skiprows=offset,delimiter=sep)
    else:
        # read the data from the file or refer to the text
        dat=open(fullfilename,'rb').read() if fullfilename else text

        if offset:
            dat=dat[offset:]

        # decode the base64 data stored in the file or the text
        if format_ in (BASE64,BASE64_GZ):
            dat=base64.decodestring(dat)

        # decompress the data using gzip
        if format_ in (BASE64_GZ,BINARY_GZ):
            dat=gzip.GzipFile(fileobj=StringIO(dat)).read() # RFC 1952

        arr=np.frombuffer(dat,dtype=dtype_)

    if shape:
        shape=parseNumString(shape,int)
        arr=arr.reshape(shape)

    return arr


def readArray(arr,basepath='.'):
    '''Read an array from the array XML element `arr', loading files starting from directory `basepath'.'''
    name=arr.get('name')
    shape=arr.get('shape')
    dimorder=arr.get('dimorder','')
    type_=arr.get('type','float')
    format_=arr.get('format','ascii')
    offset=arr.get('offset',0)
    filename=arr.get('filename')
    sep=arr.get('sep')
    text=arr.text
    fullfilename=None

    if filename:
        fullfilename=os.path.join(basepath,filename)

    arr=readArrayData(shape,dimorder,type_,format_,int(offset),fullfilename,sep,text)

    return array(name, shape, dimorder, type_, format_, offset, filename, arr)


def readFile(obj_or_path):
    '''Read the file path or file-like object `obj_or_path' into a dataset object.'''
    basepath='.'
    if isinstance(obj_or_path,str):
        if os.path.isfile(obj_or_path):
            basepath=os.path.dirname(obj_or_path)
        else:
            obj_or_path=StringIO(obj_or_path)

    root=ET.parse(obj_or_path)
    meshes=map(readMesh,root.findall('mesh'))
    images=map(readImage,root.findall('image'))
    arrays=[readArray(a,basepath) for a in root.findall('array')]
    metas=readMeta(root.findall('meta'))

    return dataset(meshes, images, arrays, metas)

### Writing XML Functions

class XMLStream(object):
    '''This type wraps a file-like object to provide XML-writing methods. It is used with the `tag' context.'''
    def __init__(self,stream,sep=' '):
        self.stream=stream
        self.write=stream.write
        self.sep=sep
        self.names=[]

    def startTag(self,name,attrs={},newlines=True):
        values=[name]+['%s="%s"'%(k,v) for k,v in attrs.items()]
        spacing=self.sep*len(self.names)
        self.names.append(name)
        self.write('%s<%s>%s'%(spacing,' '.join(values),'\n' if newlines else ''))

    def endTag(self,newlines=True):
        name=self.names.pop(-1)
        spacing=self.sep*len(self.names)
        self.write('%s</%s>\n'%(spacing if newlines else '',name))

    def element(self,name,attrs={}):
        values=[name]+['%s="%s"'%(k,v) for k,v in attrs.items()]
        spacing=self.sep*len(self.names)
        self.write('%s<%s/>\n'%(spacing,' '.join(values)))

    def writeline(self,val):
        spacing=self.sep*len(self.names)
        self.write(spacing+val+'\n')

    @staticmethod
    @contextlib.contextmanager
    def tag(stream,name,attrs={},newlines=True):
        if not isinstance(stream,XMLStream):
            stream=XMLStream(stream)

        stream.startTag(name,attrs,newlines)
        yield stream
        stream.endTag(newlines)


def toNumString(arr,dtype=float):
    '''Convert the array of numbers `arr' into a space-separated string list with values of type `dtype'.'''
    dtype=np.dtype(dtype)
    return ' '.join(map(str,arr.astype(dtype)))


def reshape2D(arr):
    shape=arr.shape
    if len(shape)==1:
        return arr.reshape((arr.shape,1))
    elif len(shape)>2:
        return arr.reshape((np.prod(shape)/shape[1],shape[1]))
    else:
        return arr


def writeMeta(obj,stream):
    '''Write a meta object tree to XML.'''
    attrs=OrderedDict(name=obj.name)

    if obj.val:
        attrs['val']=obj.val
        stream.element('meta',attrs)
    else:
        with XMLStream.tag(stream,'meta',attrs) as o:
            for child in obj.children:
                if isinstance(child,meta):
                    writeMeta(child,o)
                elif isinstance(child,str):
                    for line in child.strip().split('\n'):
                        o.writeline(line.strip())
                else:
                    ET.ElementTree(child).write(stream)


def writeTransform(obj,stream):
    '''Write a transform object to XML.'''
    if obj:
        with XMLStream.tag(stream,'transform') as o:
            with XMLStream.tag(o,'position',newlines=False):
                o.write(toNumString(obj.position))
            with XMLStream.tag(o,'rmatrix',newlines=False):
                o.write(toNumString(obj.rmatrix.flatten()))
            with XMLStream.tag(o,'scale',newlines=False):
                o.write(toNumString(obj.scale))


def writeMesh(obj,stream):
    '''Write a mesh object to XML.'''
    with XMLStream.tag(stream,'mesh',{'name':obj.name}) as o:
        def _writetag(name,attrs,meta):
            attrs=OrderedDict((k,v) for k,v in attrs.items() if v is not None)
            if meta:
                with XMLStream.tag(o,name,attrs):
                    for m in t.metas:
                        writeMeta(m,o)
            else:
                o.element(name,attrs)

        if obj.timescheme:
            o.element('timescheme',{'start':obj.timescheme[0],'step':obj.timescheme[1]})

        for n in obj.nodes:
            attrs=OrderedDict([('src',n.src),('initialnodes',n.initialnodes),('timestep',n.timestep)])
            _writetag('nodes',attrs,n.metas)

        for t in obj.topologies:
            attrs=OrderedDict([('name',t.name),('src',t.src),('elemtype',t.elemtype),('spatial',t.spatial)])
            _writetag('topology',attrs,t.metas)

        for f in obj.fields:
            attrs=OrderedDict([('name',f.name),('src',f.src),('timestep',f.timestep),('topology',f.topology),('spatial',f.spatial),('fieldtype',f.fieldtype)])
            _writetag('field',attrs,f.metas)

        for m in obj.metas:
            writeMeta(m,o)


def writeImage(obj,stream):
    '''Write an image object to XML.'''
    with XMLStream.tag(stream,'image',{'name':obj.name}) as o:
        if obj.timescheme:
            o.element('timescheme',{'start':obj.timescheme[0],'step':obj.timescheme[1]})

        writeTransform(obj.transform,o)

        for imd in obj.imagedata:
            attrs=OrderedDict(src=imd.src)
            if imd.timestep:
                attrs['timestep']=imd.timestep

            if not isIDTransform(imd.transform) or imd.metas:
                with XMLStream.tag(o,'imagedata',attrs):
                    writeTransform(imd.transform,o)

                    for m in imd.metas:
                        writeMeta(m,o)
            else:
                o.element('imagedata',attrs)


def writeArrayData(data,type_,format_):
    '''Returns a string with format `format_' for the numpy array `data' containing values of type `type_'.'''
    dtype_=parseType(type_)
    out=StringIO('')
    assert format_ in validFormats

    if format_==ASCII:
        np.savetxt(out,reshape2D(data),fmt='%s')
        dat=out.getvalue()
    else:
        dat=data.astype(dtype_).tostring()
        if format_ in (BINARY_GZ,BASE64_GZ):
            gzip.GzipFile(fileobj=out,mode='wb',compresslevel=6).write(dat)
            dat=out.getvalue()

        if format_ in (BASE64, BASE64_GZ):
            dat=base64.b64encode(dat)

    return dat


def writeArray(obj,stream,basepath='.',overwriteFile=True):
    '''Write an array to XML and store its data to file if necessary, overwriting existing if `overwriteFile.'''
    attrs=OrderedDict({'name':obj.name})

    if obj.shape is not None:
        attrs['shape']=obj.shape
    if obj.dimorder:
        attrs['dimorder']=obj.dimorder
    if obj.type:
        attrs['type']=obj.type
    if obj.format:
        attrs['format']=obj.format
    if obj.filename:
        attrs['filename']=obj.filename #os.path.relpath(obj.filename,basepath)

    dat=writeArrayData(obj.data,obj.type,obj.format)

    if obj.filename:
        filename=os.path.join(basepath,obj.filename)

        if overwriteFile or not os.path.isfile(filename):
            with open(filename,'wb' if obj.format in (BASE64_GZ,BINARY_GZ) else 'w') as o:
                o.write(dat)
        elif obj.offset:
            attrs['offset']=obj.offset # add the offset value for an existing file that isn't being overwritten

        stream.element('array',attrs)
    else:
        with XMLStream.tag(stream,'array',attrs) as o:
            for line in dat.strip().split('\n'):
                o.writeline(line.strip())


def writeFile(obj,obj_or_path,overwriteFiles=True):
    '''Write the x4df object to the path or file-like object `obj_or_path'. Data files are overwritten if `overwriteFiles'.'''
    basepath=os.path.dirname(obj_or_path) if isinstance(obj_or_path,str) else os.getcwd()
    stream=obj_or_path

    if isinstance(obj_or_path,str):
        stream=open(obj_or_path,'w')

    try:
        stream.write('<?xml version="1.0" encoding="UTF-8"?>\n')

        with XMLStream.tag(stream,'x4df') as ostream:
            for mesh in obj.meshes:
                writeMesh(mesh,ostream)

            for image in obj.images:
                writeImage(image,ostream)

            for array in obj.arrays:
                writeArray(array,ostream,basepath,overwriteFiles)

            for metav in obj.metas:
                writeMeta(metav,ostream)
    finally:
        if isinstance(obj_or_path,str):
            stream.close()
