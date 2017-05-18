
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


x4df=namedrecord('x4df','meshes images arrays meta')
meta=namedrecord('meta','name val text children')
nodes=namedrecord('nodes','src initialnodes timestep meta')
topology=namedrecord('topology','name src elemtype spatial meta')
field=namedrecord('field','name src timestep topology spatial fieldtype meta')
imagedata=namedrecord('imagedata','src timestep transform meta')
mesh=namedrecord('mesh','name timescheme nodes topologies fields meta')
image=namedrecord('image','name timescheme transform imagedata meta')
transform=namedrecord('transform','position rmatrix scale')
array=namedrecord('array','name shape dimorder type format offset filename data')

# valid array formats
validFormats=('ascii', 'base64', 'base64_gz', 'binary', 'binary_gz')

# valid field types: node=per node, elem=per element, index=per index in topology
validFieldTypes=('node','elem','index')

# identity transform object
idTransform=transform(np.array([0,0,0]),np.eye(3),np.array([1,1,1]))


def isIDTransform(obj):
	'''Returns True if `obj' is a transform object equivalent to the identity.'''
	return np.all(obj.position==idTransform.position) and np.all(obj.scale==idTransform.scale) and np.all(obj.rmatrix==idTransform.rmatrix)


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
	pos,mat,scl=idTransform

	if tree is not None:
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

	if format_==validFormats[0]: # ascii
		arr=np.loadtxt(fullfilename or StringIO(text),dtype_,skiprows=offset,delimiter=sep)
	else:
		# read the data from the file or refer to the text
		dat=open(fullfilename,'rb').read() if fullfilename else text

		if offset:
			dat=dat[offset:]

		# decode the base64 data stored in the file or the text
		if format_ in validFormats[1:3]:
			dat=base64.decodestring(dat)

		# decompress the data using gzip
		if format_ in (validFormats[2],validFormats[4]):
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
	'''Read the file path or file-like object `obj_or_path' into a x4df object.'''
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

	return x4df(meshes, images, arrays, metas)

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
	if len(shape)>2:
		return arr.reshape((sum(shape)/shape[1],shape[1]))
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
	if not isIDTransform(obj):
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
					for m in t.meta:
						writeMeta(m,o)
			else:
				o.element(name,attrs)


		if obj.timescheme:
			o.element('timescheme',{'start':obj.timescheme[0],'step':obj.timescheme[1]})

		for n in obj.nodes:
			attrs=OrderedDict([('src',n.src),('initialnodes',n.initialnodes),('timestep',n.timestep)])
			_writetag('nodes',attrs,n.meta)

		for t in obj.topologies:
			attrs=OrderedDict([('name',t.name),('src',t.src),('elemtype',t.elemtype),('spatial',t.spatial)])
			_writetag('topology',attrs,t.meta)

		for f in obj.fields:
			attrs=OrderedDict([('name',f.name),('src',f.src),('timestep',f.timestep),('topology',f.topology),('spatial',f.spatial),('fieldtype',f.fieldtype)])
			_writetag('field',attrs,f.meta)

		for m in obj.meta:
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

			if not isIDTransform(imd.transform) or imd.meta:
				with XMLStream.tag(o,'imagedata',attrs):
					if imd.transform:
						writeTransform(imd.transform,o)

					for m in imd.meta:
						writeMeta(m,o)
			else:
				o.element('imagedata',attrs)


def writeArrayData(data,type_,format_):
	'''Returns a formatted string for the numpy array `data' containing values of type `type_' with format `format_'.'''
	dtype_=parseType(type_)
	out=StringIO('')

	if format_==validFormats[0]:
		isfloat=np.issubdtype(dtype_,np.float)
		fmt='%s'#'%.10f' if isfloat else '%i'
		np.savetxt(out,reshape2D(data),fmt=fmt)
		dat=out.getvalue()
	else:
		dat=data.astype(dtype_).tostring()
		if format_ in (validFormats[2],validFormats[4]):
			gzip.GzipFile(fileobj=out,mode='wb').write(dat)
			dat=out.getvalue()

		if format_ in validFormats[1:3]:
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
			with open(filename,'wb' if obj.format in validFormats[3:] else 'w') as o:
				o.write(dat)
		elif obj.offset:
			attrs['offset']=obj.offset # add the offset value for an existing file that isn't being overwritten

		stream.element('array',attrs)
	else:
		with XMLStream.tag(stream,'array',attrs) as o:
			for line in dat.strip().split('\n'):
				o.writeline(line.strip())


def writeFile(obj,obj_or_path=None,overwriteFiles=True):
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

			for metav in obj.meta:
				writeMeta(metav,ostream)
	finally:
		if isinstance(obj_or_path,str):
			stream.close()


if __name__=='__main__':
	#print readFile('./cube1.4df')
	#print readFile('./cube2.4df')
	#print readFile('./smile.4df')
	print readFile('<?xml version="1.0" encoding="UTF-8"?><x4df></x4df>')

	import sys
	writeFile(readFile('./cube2.4df'),'cube2_test.4df')

	df= readFile('cube2_test.4df')
	print df

	writeFile(readFile('./smile.4df'),sys.stdout)
