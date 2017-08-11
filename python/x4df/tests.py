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

import os,sys,nose
from StringIO import StringIO

import numpy as np

scriptdir=os.path.dirname(os.path.abspath(__file__))
rootdir=os.path.join(scriptdir,'..','..')
testdir=os.path.join(rootdir,'testdata')

sys.path.append(rootdir)
from x4df import nodes,topology,mesh,array,dataset,BASE64_GZ,BASE64, writeFile,readFile


def testWrite1():
    nodespec=nodes('nodesmat')
    topo=topology('tris','trismat','Tri1NL')
    meshobj=mesh('triangle',None,[nodespec],[topo])
    
    nodear=array('nodesmat',format=BASE64_GZ,data=np.asarray([(0,0,0),(1,0,0),(0,1,0)]))
    indar=array('trismat',format=BASE64,shape='1 3',type='uint8',data=np.asarray([(1,0,2)]))
    
    ds=dataset([meshobj],None,[nodear,indar])
    
    s=StringIO()
    writeFile(ds,s)
    
    
def testWrite2():
    nodespec=nodes('nodesmat')
    topo=topology('tris','trismat','Tri1NL')
    meshobj=mesh('triangle',None,[nodespec],[topo])
    
    nodear=array('nodesmat',format=BASE64_GZ,data=np.asarray([(0,0,0),(1,0,0),(0,1,0)]))
    indar=array('trismat',format=BASE64,shape='1 3',type='uint8',data=np.asarray([(1,0,2)]))
    
    ds=dataset([meshobj],None,[nodear,indar])
    
    s=StringIO()
    writeFile(ds,s)
    s.seek(0)
    readFile(s)
    
    
nose.runmodule() 