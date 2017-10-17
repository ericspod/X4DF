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
Unit tests to run with Nose. Use command "nosetests tests.py" or "python tests.py".
'''

from __future__ import print_function, division
import os,sys,glob,unittest,shutil,tempfile, base64, gzip
import xml.etree.ElementTree

from io import StringIO,BytesIO

import numpy as np


scriptdir=os.path.dirname(os.path.abspath(__file__))
rootdir=os.path.join(scriptdir,'..','..')
testdir=os.path.join(rootdir,'testdata')

sys.path.append(rootdir)
from x4df import nodes, topology, mesh, array, meta, dataset, image, transform, imagedata, writeFile, readFile
from x4df import BASE64_GZ, BASE64, BINARY, BINARY_GZ, B64LINELEN

trimeshxml=u'''<?xml version="1.0" encoding="UTF-8"?>
<x4df>
 <mesh name="triangle">
  <nodes src="nodesmat"/>
  <topology name="tris" src="trismat" elemtype="Tri1NL"/>
 </mesh>
 <array name="nodesmat">
  0.0 0.0 0.0
  1.0 0.0 0.0
  0.0 1.0 0.0
 </array>
 <array name="trismat" shape="1 3" type="uint8">
  1 0 2
 </array>
</x4df>
'''


def createTriMeshDS(matformat=None,nodefile=None,indsfile=None):
    nodespec=nodes('nodesmat')
    topo=topology('tris','trismat','Tri1NL')
    meshobj=mesh('triangle',None,[nodespec],[topo])
    
    nodedat=np.asarray([(0.0,0.0,0.0),(1.0,0.0,0.0),(0.0,1.0,0.0)])
    indsdat=np.asarray([(1,0,2)])
    
    nodear=array('nodesmat',format=matformat,filename=nodefile,data=nodedat)
    indar=array('trismat',format=matformat,filename=indsfile,shape='1 3',type='uint8',data=indsdat)
    
    return dataset([meshobj],None,[nodear,indar])


def createOctahedronDS(matformat=None,dataformat='float32',dim=12,imgfile=None):
    dim2=dim//2
    grid=np.sum(np.abs(np.ogrid[-dim2:dim2+1,-dim2:dim2+1,-dim2:dim2+1]))
    octa=(grid<dim2).astype(np.float32)
    
    trans=transform(np.zeros((3,)),np.eye(3),np.ones((3,)))

    imd=imagedata('image',None,None,[])
    im=image('octahedron',None,trans,[imd],[])

    imgarr=array('image',' '.join(map(str,octa.shape)),None,dataformat,matformat,None,imgfile,octa)

    return dataset(None,[im],[imgarr])
    

class TestIO(unittest.TestCase):
    def setUp(self):
        self.tempdir=tempfile.mkdtemp()
        
        self.trimesh=createTriMeshDS()
        self.trimeshB64=createTriMeshDS(BASE64)
        self.trimeshB64GZ=createTriMeshDS(BASE64_GZ)
        
        self.mfile=self.tempfile('trimesh.x4df')
        self.ifile=self.tempfile('octa.x4df')
        self.dfile=self.tempfile('dat')
        
    def tearDown(self):
        shutil.rmtree(self.tempdir)
        
    def tempfile(self,filename):
        return os.path.join(self.tempdir,filename)
        
### Basic tests    
    
    def testBasicWrite(self):
        '''Tests writeFile.'''
        s=StringIO()
        writeFile(self.trimesh,s)
        
    def testStringWrite(self):
        '''Test reading from an XML string and then writing an identical document.'''
        obj=readFile(StringIO(trimeshxml))
        s=StringIO()
        writeFile(obj,s)
        self.assertEqual(s.getvalue().strip(),trimeshxml.strip(),'Writer not writing XML identical to source')
        
    def testBadString(self):
        '''Test correct raise of ParseError on bad input to readFile().'''
        with self.assertRaises(xml.etree.ElementTree.ParseError):
            readFile('Not valid filename or XML data')
            
    def testWriteBadBinary(self):
        '''Tests attempting to write binary data into a single-file object.'''
        with self.assertRaises(ValueError):
            writeFile(createTriMeshDS(BINARY),self.mfile)
 
### Test writing to separate data file with text, binary, and compressed data
       
    def testWriteSeparateFile1(self):
        '''Test writing one array to a separate file.'''
        mesh=createTriMeshDS(nodefile=self.dfile)
        writeFile(mesh,self.mfile)
        
        self.assertEqual(mesh.arrays[0].size,3,'Bad node array size')
        self.assertEqual(mesh.arrays[0].offset,0,'Bad node array offset')
        
        with open(mesh.arrays[0].filename) as o:
            self.assertEqual(o.read(),'0.0 0.0 0.0\n1.0 0.0 0.0\n0.0 1.0 0.0\n','Bad separate file contents')
            
    def testWriteSeparateFile2(self):
        '''Test writing multiple arrays to a separate file.'''
        mesh=createTriMeshDS(nodefile=self.dfile,indsfile=self.dfile)
        writeFile(mesh,self.mfile)
        
        self.assertEqual(mesh.arrays[0].size,3,'Bad node array size')
        self.assertEqual(mesh.arrays[1].size,1,'Bad index array size')
        self.assertEqual(mesh.arrays[1].offset,3,'Bad index array offset')
        
        with open(mesh.arrays[0].filename) as o:
            self.assertEqual(o.read(),'0.0 0.0 0.0\n1.0 0.0 0.0\n0.0 1.0 0.0\n1 0 2\n','Bad separate file contents')
            
    def testWriteBinaryFile1(self):
        '''Test writing multiple binary arrays to a separate file.'''
        mesh=createTriMeshDS(BINARY,self.dfile,self.dfile)
        writeFile(mesh,self.mfile)
        
        meshtype=np.dtype('float32')
        indtype=np.dtype('uint8')
        
        binary=mesh.arrays[0].data.astype(meshtype).tobytes()
        binary+=mesh.arrays[1].data.astype(indtype).tobytes()
        
        self.assertEqual(mesh.arrays[0].size,meshtype.itemsize*9,'Bad node array size')
        self.assertEqual(mesh.arrays[0].offset,0,'Bad node array offset')
        self.assertEqual(mesh.arrays[1].size,indtype.itemsize*3,'Bad index array size')
        self.assertEqual(mesh.arrays[1].offset,meshtype.itemsize*9,'Bad index array offset')
        
        with open(mesh.arrays[0].filename,'rb') as o:
            self.assertEqual(o.read(),binary,'Bad binary file contents')        
            
    def testWriteB64File1(self):
        '''Test writing one array to a separate b64 file.'''
        mesh=createTriMeshDS(BASE64,self.dfile)
        writeFile(mesh,self.mfile)
        
        meshdata=mesh.arrays[0].data
        b64=base64.b64encode(meshdata.astype(np.dtype('float32')).tostring()).decode()
        lenwithnewlines=len(b64)+1+len(b64)//B64LINELEN
        
        self.assertEqual(mesh.arrays[0].size,lenwithnewlines,'Bad node array size')
        
        with open(mesh.arrays[0].filename) as o:
            filecontents=o.read().strip()
            self.assertEqual(filecontents,b64,'File contents length %i does not match expected contents of length %i'%(len(filecontents),len(b64)))

    def testWriteB64File2(self):
        '''Test writing multiple arrays to a separate b64 file.'''
        mesh=createTriMeshDS(BASE64,self.dfile,self.dfile)
        writeFile(mesh,self.mfile)
        
        meshdata=mesh.arrays[0].data
        indsdata=mesh.arrays[1].data
        b64=base64.b64encode(meshdata.astype(np.dtype('float32')).tostring()).decode()
        lenwithnewlines=len(b64)+1+len(b64)//B64LINELEN
        
        b64+='\n'+base64.b64encode(indsdata.astype(np.dtype('uint8')).tostring()).decode()
        lenwithnewlines1=len(b64)+1+len(b64)//B64LINELEN
        
        self.assertEqual(mesh.arrays[0].size,lenwithnewlines,'Bad node array size')
        self.assertEqual(mesh.arrays[0].offset,0,'Bad node array offset')
        self.assertEqual(mesh.arrays[1].size,lenwithnewlines1-lenwithnewlines,'Bad index array size')
        self.assertEqual(mesh.arrays[1].offset,lenwithnewlines,'Bad index array offset')
        
        with open(mesh.arrays[0].filename) as o:
            filecontents=o.read().strip()
            self.assertEqual(filecontents,b64,'File contents length %i does not match expected contents of length %i'%(len(filecontents),len(b64)))
        
    def testWriteCompressedFile1(self):
        '''Test writing to a .gz compressed separate file.'''
        mesh=createTriMeshDS(BINARY,self.dfile+'.gz',self.dfile+'.gz')
        writeFile(mesh,self.mfile)
        
        binary=mesh.arrays[0].data.astype(np.float32).tobytes()
        binary+=mesh.arrays[1].data.astype(np.uint8).tobytes()
        
        with gzip.open(mesh.arrays[0].filename) as o:
            self.assertEqual(o.read(),binary,'Compressed file does not contain same contents as original arrays')
            
    def testWriteBinaryGZFile1(self):
        '''Test writing single compressed binary arrays to a separate file.'''
        mesh=createTriMeshDS(BINARY_GZ,self.dfile,self.dfile)
        writeFile(mesh,self.mfile)
        
        meshtype=np.dtype('float32')
        indtype=np.dtype('uint8')
        
        binary=BytesIO()
        with gzip.GzipFile(fileobj=binary,mode='wb',compresslevel=6) as o:
            o.write(mesh.arrays[0].data.astype(meshtype).tobytes())
        
        nodesize=len(binary.getvalue())
        self.assertEqual(mesh.arrays[0].size,nodesize,'Bad node array size')
        self.assertEqual(mesh.arrays[0].offset,0,'Bad node array offset')
            
        with gzip.GzipFile(fileobj=binary,mode='ab',compresslevel=6) as o:
            o.write(mesh.arrays[1].data.astype(indtype).tobytes())
            
        self.assertEqual(mesh.arrays[1].size,len(binary.getvalue())-nodesize,'Bad index array size')
        self.assertEqual(mesh.arrays[1].offset,nodesize,'Bad index array offset')
            
    def testWriteB64GZFile1(self):
        '''Test writing single compressed base64 arrays to a separate file.'''
        mesh=createTriMeshDS(BASE64_GZ,self.dfile,self.dfile)
        writeFile(mesh,self.mfile)
        
        meshtype=np.dtype('float32')
        indtype=np.dtype('uint8')
        
        binary=BytesIO()
        with gzip.GzipFile(fileobj=binary,mode='wb',compresslevel=6) as o:
            o.write(mesh.arrays[0].data.astype(meshtype).tobytes())
        
        b64=base64.b64encode(binary.getvalue()).decode() # store node array
        lenwithnewlines=len(b64)+1+len(b64)//B64LINELEN
            
        binary=BytesIO()
        with gzip.GzipFile(fileobj=binary,mode='ab',compresslevel=6) as o:
            o.write(mesh.arrays[1].data.astype(indtype).tobytes())
            
        b64+='\n'+base64.b64encode(binary.getvalue()).decode() # append index array
        lenwithnewlines1=len(b64)+1+len(b64)//B64LINELEN
            
        self.assertEqual(mesh.arrays[0].size,lenwithnewlines,'Bad node array size')
        self.assertEqual(mesh.arrays[0].offset,0,'Bad node array offset')
        self.assertEqual(mesh.arrays[1].size,lenwithnewlines1-lenwithnewlines,'Bad index array size')
        self.assertEqual(mesh.arrays[1].offset,lenwithnewlines,'Bad index array offset')
 
### Test reading and writing identical objects    
       
    def testWriteRead1(self):
        '''Tests applying the results from writeFile() to readFile() using a StringIO buffer.'''
        s=StringIO()
        writeFile(self.trimesh,s)
        s.seek(0)
        readFile(s)
        
    def testWriteRead2(self):
        '''Tests writing a mesh to a file then reading it back.'''
        for m in (self.trimesh,self.trimeshB64,self.trimeshB64GZ):
            writeFile(m,self.mfile)
            readFile(self.mfile)
        
    def testWriteReadB64(self):
        '''Test reading and writing base64 and base64_gz formats, ensuring they are the same when read.'''
        s=StringIO()
        writeFile(self.trimeshB64,s)
        s.seek(0)
        ds=readFile(s)
        
        s1=StringIO()
        writeFile(self.trimeshB64GZ,s1)
        s1.seek(0)
        ds1=readFile(s1)
        
        self.assertEqual(self.trimeshB64.arrays[0].shape,'3 3')
        
        self.assertTrue(np.all(self.trimeshB64.arrays[0].data==ds.arrays[0].data),'Base64 data not the same as original')
        self.assertTrue(np.all(ds.arrays[0].data==ds1.arrays[0].data),'Base64 and Base64_gz data not the same')
    
    def testFileRead1(self):
        '''Tests reading from testdata files.'''    
        for f in glob.glob(os.path.join(testdir,'*.x4df')):
            obj=readFile(os.path.join(testdir,f))
            self.assertIsNotNone(obj,'Failed to read '+f)
    
    def testMetaWriteRead(self):
        '''Tests writing and read metadata to a file.'''
        child=meta('Child','I am a child')
        m=meta('metavalue',None,None,[child])
        tris=createTriMeshDS()
        tris.metas=[m]
        tris.meshes[0].metas=[m]
        
        writeFile(tris,self.mfile)
        readFile(self.mfile)
        
    
if __name__ == '__main__':
    print(sys.version)
    sys.stdout.flush()
    unittest.main()
    