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
Unit tests to run with Nose. Use command "nosetests test.py".
'''

import os,sys,nose,glob
from StringIO import StringIO

import numpy as np

import xml.etree.ElementTree

scriptdir=os.path.dirname(os.path.abspath(__file__))
rootdir=os.path.join(scriptdir,'..','..')
testdir=os.path.join(rootdir,'testdata')

sys.path.append(rootdir)
from x4df import nodes,topology,mesh,array,dataset,BASE64_GZ,BASE64, writeFile,readFile


trimeshxml='''<?xml version="1.0" encoding="UTF-8"?>
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


def getTriMeshDS():
    nodespec=nodes('nodesmat')
    topo=topology('tris','trismat','Tri1NL')
    meshobj=mesh('triangle',None,[nodespec],[topo])
    
    nodear=array('nodesmat',data=np.asarray([(0.0,0.0,0.0),(1.0,0.0,0.0),(0.0,1.0,0.0)]))
    indar=array('trismat',shape='1 3',type='uint8',data=np.asarray([(1,0,2)]))
    
    return dataset([meshobj],None,[nodear,indar])


def testWrite1():
    '''Tests writeFile.'''
    s=StringIO()
    writeFile(getTriMeshDS(),s)

    
def testWriteRead1():
    '''Tests applying the results from writeFile to readFile.'''
    s=StringIO()
    writeFile(getTriMeshDS(),s)
    s.seek(0)
    readFile(s)
    
    
def testReadWrite1():
    '''Test reading from an XML string and then writing an identical document.'''
    obj=readFile(StringIO(trimeshxml))
    s=StringIO()
    writeFile(obj,s)
    nose.tools.assert_equal(s.getvalue().strip(),trimeshxml.strip())
    
    
def testBadString():
    with nose.tools.assert_raises(xml.etree.ElementTree.ParseError):
        readFile('Not valid filename or XML data')
        

def testFileRead1():
    '''Tests reading from a testdata files.'''    
    for f in glob.glob(os.path.join(testdir,'*.x4df')):
        obj=readFile(os.path.join(testdir,f))
        nose.tools.assert_is_not_none(obj,'Failed to read '+f)
    
    
nose.runmodule() 