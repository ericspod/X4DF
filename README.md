# X4DF
X4DF: Extensible 4D Data Fields

This is an XML data format for representing mesh and image data. It's intended to provide a common mechanism for storing
3D/4D mesh and 2D/3D/4D image data with spatiotemporal parameters. The format for mesh and image data is designed to be 
general to permit custom data types to be stored while still being defined in a common manner. Arbitrary secondary data
can be stored using metadata tags to associate information with mesh, image, and array components. A single document can
be used to store any number of meshes and images together, allowing for example an mesh to be stored with the image it was
generated from. 

Example storing a mesh with a single triangle:

```xml
<?xml version="1.0" encoding="UTF-8"?>
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
```

This repository contains the definition of X4DF in terms of semantics in this document, XML definition in the
`x4df.(rnc,rng,xsd)` files, and basic code library for reading and writing the format. Currently the Python code for IO
is present but other languages will be added.

An X4DF document is composed of three main elements: mesh elements defining a mesh comprised of node, topology and field 
information, image elements defining position in space and dimensions, and array elements storing the actual mesh and image
data. Metadata is used to store arbitrary hierarchical text or XML data, and can be stored in an X4DF element as well as 
every other element except image elements. The following sections will explain the meaning of the X4DF elements.

## Mesh Definition

A mesh is composed of a set of spatial nodes, possibly a topology index which nodes define geometric elements, and fields
defining data for each node or each element. The above example defines a mesh with one node array `nodesmat` storing three
nodes, and one topology array `trismat` defining one triangle using nodes 1, 0, and 2 in that order. A mesh can have multiple
node arrays if it is time-dependent in which case each array defines node positions at a given point in time. Multiple
topologies can also be present if a field uses a different topology from mesh itself, in which case the field topology
must have the same geometry as the mesh topology.

The `mesh` XML element has a single attribute `name` which gives that mesh its name, and the following elements:
 * `timescheme` (optional) - defines the start time of a time-dependent mesh and the step (interval) between timesteps, 
 these are stored as `start` and `step` attributes containing floating point numbers.
 * `nodes` (one or more) - defines a node array and its properties. Attributes:
   * `src` - states the name of the array storing the data
   * `initialnodes` (optional) - names an array storing initial node positions if those given in `src` are offsets from these
   * `timestep` (optional) - states the floating point timestep these nodes are defined at
 * `topology` (zero or more) - defines a topology which is an array of node indices. Attributes:
   * `name` - gives the topology a name
   * `src`  - states which array stores the index data
   * `elemtype` (optional) - gives the element type definition
   * `spatial` (optional) - stores `true` if this topology defines spatial geometry or `false` if it is a field topology.
 * `field` (zero or more) - defines data fields for nodes or topologies. Attributes:
   * `name` - gives the field a name which may be shared by multiple fields at different timesteps
   * `src` - names the source data array which must have as many rows as the field's topology, each row is a data element
   * `timestep` (optional) - defines what floating point timestep this field is defined for
   * `toponame` (optional) - states the name of the topology the field uses (default is the spatial topology)
   * `spatial` (optional) - states the name of the spatial topology if there are multiples
   * `fieldtype` (optional) - states the type of field (`node`, `elem`, or `index`)
 
A time-dependent mesh must have either multiple node definitions, multiple fields with the same name, or both. In these
cases the nodes/fields are defined for different points in time. If the `timescheme` is present this defines the start time
and time between each step, in which case the node/field definitions are treated as ordered lists and assigned to timesteps
starting from the given start and incrementing by the step value. If `timescheme` is not given then each node/field element
must explicitly state what time they are assigned to in the `timestep` attribute.  

A topology's element type definition, given in `elemtype`, defines its geometry, order, and basis function, in the above 
example `Tri1NL` defines triangles using linear nodal lagrange as the basis (ie. a simple triangle). 
The definitions follow the pattern `[geom][order][basis]` where `geom` is one of `Line`, `Tri`, `Quad`, `Tet`, or `Hex`, 
`order` is `1` for linear, `2` for quadratic, etc., and `basis` is always `NL`. An extended description can be found 
[here](https://github.com/ericspod/Eidolon/wiki/Element-Type-Definition).
Custom element type definitions can be given but it is then incumbent on the reader of the file to understand what they mean.

Fields define values for each node of the mesh (if `fieldtype` is `node`), for each element in the spatial topology (`elem`),
or for each individual index value in a spatial topology (`index`). If there is multiple node arrays but only one field with
a given name then this field is assigned to the nodes for each timestep. If there is multiple fields with the same name, they
are treated as an order list of fields assigned to successive timesteps, so if there is a single node field then the mesh is
time-dependent in that the nodes do not move over time but the field changes, otherwise each field array is associated with the
nodes at the equivalent timestep. Like the nodes element, the `timestep` attribute can be set to explicitly define what timestep
a field is defined for. 

Fields require a topology and basis function to allow interpolation between values. Typically this is the same topology as
that used by the mesh (the spatial topology), but a field can have its own called a field topology whose `spatial` attribute
is `false`. A field topology must have the same geometry type as the field's spatial topology since there is a one-to-one
correspondence between spatial and field topology elements. For the example triangle mesh above, a field with a `Tri2NL` 
topology would define a quadratic triangle having 6 field values.

## Image Definition

Image are defined a one or more planes or volumes of values with specific spatial positions and timesteps.
An image element has a single `name` attribute giving it a name and the following elements:
 * `timescheme` (optional) - defines the start time of a time-dependent image sequence and the step (interval) between timesteps, 
 these are stored as `start` and `step` attributes containing floating point numbers. If this is present then there must be
 an ordered list of `imagedata` elements in the image or a single `imagedata` element defined with a 4D array.
 * `transform` (optional) - a transform defining the position, orientation, and size of every image component
 * `imagedata` (one or more) - a definition of an 2/3/4D array of pixel values as an image in space and time
 
The `transform` element defines a spatial transform with these elements, each of which is optional but given in this order:
 * `position` - text contains three floating point values defining the coordinate in 3D space of the image's minimal corner, 
 default is '0 0 0'.
 * `rmatrix` - text contains nine floating point values defining a 3-by-3 rotation matrix in row-major order, this defines
 the rotation of the image around its minimal corner, default is `1 0 0 0 1 0 0 0 1`.
 * `scale` - text contains three floating point values defining the dimensions of the image, default is `1 1 1`.

If a transform is defined for an image then it is applied to every `imagedata` element, otherwise each `imagedata` should
define their own.

The `imagedata` element defines what array represents image data and where in space/time it is. The `src` attribute states
which array defines the image data, and the optional `timestep` attribute states what timestep the image is defined at. 
An optional `transform` element can be included to position the image in space, if not present then the transform for 
the whole image element is used. The source arrays are treated as image planes or volumes, such that their dimensions are
interpreted to be the X, Y, Z, and time dimensions of a 4D image volume. If the image is a 2D plane then the Z dimension is
1, if the image is not time dependent then the time dimension is 1. A source array thus must have at least 4 dimensions,
further dimensions beyond this are interpreted as pixel components or channels.

If an image has multiple `imagedata` elements then each must have a `timestep` attribute and the `timescheme` element is
ignored, this ensure that each image component has a placement in time. Typically multiple `imagedata` elements are present
when multiple arrays are used to define images which intersect in space but at different times, so each array is a separate
timestep of the same image. It is however possible to define an image composed of disjoint 2D or 3D images which are not
necessarily evenly spaced in time. 

## Array Definition

The `array` XML elements specify and optionally contain arbitrary array data which can be stored as text or as binary data, either 
in the XML document or in separate data files. In the XML text data is stored directly, binary data (compressed or 
uncompressed) must be encoded in base64 to ensure the file remains a valid text document, otherwise it must be stored in 
a separate file. 

The `array` XML element uses these attributes:
 * `name` - name of the array, used to reference the array data in other parts of the document
 * `shape` (optional for ascii only) - shape of the array, a space separated tuple of positive integer values
 * `dimorder` (optional) - a text specifier indicating the order dimensions (unused for now)
 * `type` (optional) - type of the array elements, defaults to `float32`
 * `format` (optional) - states the data format, defaults to `ascii`
 * `offset` (optional) - states the offset in characters (if `format` is `ascii`) or bytes (if `format` is not `ascii`) 
   the array starts from when reading from a separate file, default is 0 and is ignored if not reading from a file
 * `size` (optional) - states the number of lines (if `format` is `ascii`) or bytes (if `format` is not `ascii`) of the array
   as stored in a file, this is needed to allow reading an array segment from the middle of a file so is ignored if not reading from a file
 * `filename` (optional if format not `binary` or `binary_gz`) - file storing data, otherwise data must be stored in the body of the element
 * `sep` (optional) - separator character between elements in `ascii` format, default is space

Array type is specified using the format `[><=]('uint','int','float')('8','16','32','64')` which states endianness, base
type, and size. For example, an unsigned little endian 16-bit integer has type `<uint16`. Endianness is meaningful for binary
representation only, where `<` is little endian, `>` is big endian, and `=` is current platform endianness (the default).
The base types are respectively unsigned integer, signed integer, and floating point. The size is in bits and can be 
combined with any base type except for `float8`.

The shape attribute defines the shape of the array, eg. an array with 3 rows and 2 columns is specified as `3 2`. If the
data is text then the shape for a 2D array can be inferred by how many lines there are and how many components per line,
otherwise this attribute is mandatory.

The valid formats for array data are as follows:
 * `ascii` - data is stored as the textual representation of the array, with elements formatted for the specified type 
 * `base64` - data is stored in binary representation and then encoded in base64
 * `base64_gz` - data is stored in binary representation, compressed with gzip, and then encoded in base64
 * `binary` - data is stored in binary representation directly, this must be in a separate binary file 
 * `binary_gz` - data is stored in binary representation directly, compressed with gzip, this must be in a separate binary file 

Data in any format can be stored in a file, it is mandatory for `binary` or `binary_gz` data to be stored as such. When 
reading data from a file, reading starts from the `offset` line if text or from the `offset` byte of data
otherwise, and read for `size` number of lines if text or `size` number of bytes. The use of offsets allows multiple arrays 
to be stored in the same file. If `shape` is not given for text then all the data from the offset will be read. The name 
of the file is given in `filename` which is typically a path relative to the XML document. 

When storing multiple arrays in one file each array is encoded and/or compressed independently and appended to the file.
The `offset` and `size` values are used to read a subsection of the file without having to decode/decompress other arrays.

A whole file can be compressed as a single unit using the `gzip` command line tool, in which case the filename will be 
appended with `.gz` and the names stored in the XML document must likewise be changed. When reading or writing to a file
ending with `.gz` the library is expected to compress/decompress the byte stream as appropriate, in which case the `offset`
and `size` parameters refer the uncompressed bytes.

Creating base64 data is done by converting the array into its binary representation, compressing if `base64_gz` is used,
then encoding as base64 text. This allows compressed data to be stored in the text body of a `array` element.

### Array Ordering

All text or binary array values are stored in rightmost index first order, that is to say the rightmost index is the least
significant. 
Given an n-dimensional  array of dimensions `D=(d1,d2...,dn)`, a value at index `I=(i1,i2,....,in)` will be stored at the 
address `Sigma(I[i]*Pi(D[i+1:]) for 1<=i<=n)` where `Sigma` is the sum operator and `Pi` the product operator. 
This is also called C or row-major ordering.

For example, the array `[[0,1],[2,3]]` with dimensions `(2,2)` is flattened out to the list `(0,1,2,3)`. These
values would then be stored in a chosen data format in binary or as text. 

### Text Array

In textual array format, values are stored in rightmost index first order, typically with rows of an array being printed
to one text row separated by a newline character. For a 2D array whose indices are (row, column), each row is printed on 
separate lines, eg. the array `[[0,1],[2,3]]` has rows `[0,1]` and `[2,3]` thus would be stored textually as `0 1\n2 3\n`.

For arrays beyond 2 dimensions, the rightmost index first ordering implies that the last two dimensions are interpreted as
(row, column) values as in the above, with 2D subarrays stored as the next significant indices are incremented from right
to left. For example, an array of dimensions `(2,2,2)` would be represented first by storing the 2D array `(0,:,:)` 
followed by `(1,:,:)` together in a single text block.  

Values are separated by spaces as default, the array element can specify a different separator. The array type determines
how values are stored, with integers represented as Python `int` literals and floating point numbers represented as
Python `float` literals. 

For mesh data whose arrays are typically lists of vectors indexed as (row,component) arrays, topology definitions indexed
as (element,index) arrays, or data vectors indexed as (row,value) arrays, this implies that each component (vector, element,
or field element) is stored on its own line. A vector array for example would be stored as `x0 y0 z0\nx1 y1 z1\n...`.

For 2D images indexed as (width,height) arrays, this implies the image will be stored in a transposed manner if the text
data is viewed as an ASCII-art type image. Pixel values that run down the left-hand side of the image will instead be
stored as the first row. For 3D/4D images indexed as (width,height,depth) or (width,height,depth,time), this implies that
values in the depth or time dimension get stored first.

### Binary Array

Binary data is stored as described above in rightmost index first order, and can be compressed and/or encoded in base64.
If the format is `binary` or `binary_gz` then the final output is a byte stream which likely isn't valid text therefore
not valid in an XML document so must be stored in a separate file named in the `filename` attribute. 

To store array data, the array is first converted to a byte stream. If the format is `binary_gz` or `base64_gz` the gzip 
algorithm (RFC 1952) is applied to produce a compresed byte stream. Subsequently if the format is `base64` or `base64_gz`
then the byte stream is encoded as a base64 string with trailing `=` pad characters. Binary data can only be stored in an
XML document as base64 encoded data.

### Multi-Array Files

Data files can contain multiple arrays which can be read using the `offset` and `size` attributes of `array` elements.
All arrays stored in a file must be one of the text formats (`ascii`, `base64`, `base64_gz`) or one of the binary formats
(`binary_gz`, `base64_gz`), mixing text and binary formats is not allowed. When reading an array from such a file, the
`offset` and `size` values are in lines if the data is text, and bytes if binary. 

### Array Interpretation

The data stored in an array can be interpreted as lists of vectors, lists of topology element indices, lists of field values,
or n-dimensional images. Mesh and image definitions as described above rely on these array types for their own representations,
however the used can include any array data they choose which can be referred to in custom code or metadata.

Below is the interpretation of the standard array types as used by `mesh` and `image` elements:

 * *Vector list*: arrays with dimensions `(row,component)` are interpreted as lists of n-dimensional vectors, where `row` is
 each vector and `component` is the dimension of the vector (eg. 2 for 2D vectors and 3 for 3D vectors). 
 
 * *Topology*: arrays with dimensions `(row,index)` are interpreted as lists of elements definiting a mesh topology, 
 where each row is an element containing the indices of vertices stored in a separate vector or field array.
 
 * *Field*: arrays with dimensions `(row,component)` are interpreted as lists of n-dimensional field values, where each
 row is a single field value which has `component` number of values. A vector list is essentially a field list which is
 interpreted as spatial values.
 
 * *Image volume*: arrays with dimensions `(row,column)`, `(depth,row,column)`, or `(time,depth,row,column)` are interpreted
 respectively as 2D, 3D, or 4D images. Given a 2D image, the `row` index increases in the image's downward or Y direction
 and `column` in the rightward or X direction, such that an index `(i,j)` is the `j`'th pixel at row `i`. A 3/4D image
 adds extra dimensions `depth` for volume images and `time` for time-varying images. Typically a 3D array would define a
 volume and not a time-dependent 2D image, which instead should be stored as 4D array wher the `depth` dimension is 1.


## Image Transform

A transform defines three components: an translation or offset vector in 3D space (`tx`, `ty`, `tz`), a scale vector in
3D space (`sx`, `sy`, `sz`), and a rotation 3x3 matrix (`a`,`b`,`c`,`d`,`e`,`f`,`g`,`h`,`i`). A 4x4 matrix defining the
transform for these components is 

```
sx*a sy*b sz*c tx
sx*d sy*e sz*f ty
sx*g sy*h sz*i tz
0    0    0    1
```

This represents the transformation from a reference space to world space, in this case from image space to world space. 
The reference 2D image is a 1x1 quad on the XY plane from `(0,0,0)` to `(1,1,0)`, whereas the reference 3D volume is the
unit cube from `(0,0,0)` to `(1,1,1)`. This transform therefore represents the transformation of the unit quad/cube to the
actual image in world space, consequently a voxel's world space position is obtained by multiplying its relative position
vector in the image by the above transform matrix. 

On a per-component basis, the translation value defines where in space the image's minimal corner is located (the minimal 
corner being where the untransformed image's first voxel is located), the rotation matrix defining how the image is rotated 
around the minimal corner, and the scale value defining the size of the whole image. 
