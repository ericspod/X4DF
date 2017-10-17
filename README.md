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
`order` is `1` for linear, `2` for quadratic, etc., and `basis` is always `NL`. An extended description can be found here: 
https://github.com/ericspod/Eidolon/wiki/Element-Type-Definition
Custom element type definitions can be given but it is then incumbent on the reader of the file to understand what they mean.

## Image Definition

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
values in the depth or time dimention get stored first.

### Binary Array

Binary data is stored as described above in rightmost index first order, and can be compressed and/or encoded in base64.
If the format is `binary` or `binary_gz` then the final output is a byte stream which likely isn't valid text therefore
not valid in an XML document so must be stored in a separate file named in the `filename` attribute. 

To store array data, the array is first converted to a byte stream. If the format is `binary_gz` or `base64_gz` the gzip 
algorithm (RFC 1952) is applied to produce a compresed byte stream. Subsequently if the format is `base64` or `base64_gz`
then the byte stream is encoded as a base64 string with trailing `=` pad characters. 

