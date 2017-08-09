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
  1 0 3
 </array>
</x4df>
```


## Array Definition

The `array` XML elements specify and/or store arbitrary array data which can be stored as text or as binary data, either 
in the XML document or in separate data files. In the XML text data is stored directly, binary data (compressed or 
uncompressed) must be encoded in base64 to ensure the file remains a valid text document otherwise it must be stored in 
a separate file. 

The `array` XML element uses these attributes:
 * `name` - name of the array, used to reference the array data in other parts of the document
 * `shape` (optional for text only) - shape of the array, a space separated tuple of positive integer values
 * `dimorder` (optional) - a text specifier indicating the order dimensions (unused for now)
 * `type` (optional) - type of the array elements, defaults to `float32`
 * `format` (optional) - states the data format, defaults to `ASCII`
 * `offset` (optional) - states the offset in characters (if `format` is `ASCII`) or bytes (if `format` is not `ASCII`) 
   the array starts from when reading from a file, default is 0
 * `filename` (optional) - file to read data from, otherwise data must be stored in the body of the element
 * `sep` (optional) - separator character between elements in `ASCII` format, default is `,`

Array type is specified using the format `[><=]('uint','int','float')('8','16','32','64')` which states endianness, base
type, and size. For example, an unsigned little endian 16-bit number has type `<uint16`. Endianness is meaningful for binary
representation only, where `<` is little endian, `>` is big endian, and `=` is current platform endianness (the default).
The base types are respectively unsigned integer, signed integer, and floating point. The size is in bits and can be 
combined with any base type except for `float8`.

The shape attribute defines the shape of the array, eg. an array with 3 rows and 2 columns is specified as `3 2`. If the
data is text then the shape for a 2D array can be inferred by how many lines there are and how many components per line,
otherwise this attribute is mandatory.

The valid formats for array data are as follows:
 * `ASCII` - data is stored as the textual representation of the array, with elements formatted for the specified type 
 * `BASE64` - data is stored in binary representation and then encoded in base64
 * `BASE64_GZ` - data is stored in binary representation, compressed with the gzip algorithm (RFC 1952), and then encoded in base64
 * `BINARY` - data is stored in binary representation directly, this must be in a separate binary file 
 * `BINARY_GZ` - data is stored in binary representation directly, compressed with the gzip algorithm (RFC 1952), this must be in a separate binary file 

Data in any format can be stored in a file, for `BINARY` or `BINARY_GZ` data it is mandatory to be stored as such. When 
reading data from a file, reading starts from the `offset` line if text or from the `offset` byte otherwise. The use of
offsets allows multiple arrays to be stored in the same file. If `shape` is not given for text then all the file from 
the offset will be read. The name of the file is given in `filename` which is typically a path relative to the XML 
document. 

For the compressed formats the whole file is compressed together, which can be done with the `gzip` command line tool. 
To read from such a file, it first must be decompressed in its entirety then read from an offset in the resulting data.

Creating base64 data is done by converting the array into its binary representation, compressing if `BASE64_GZ` is used,
then encoding as base64 text. This allows compressed data to be stored in the text body of a `array` element.

### Array Ordering

As text or binary array values are stored in rightmost index first order, that is to say the rightmost index is the least
significant. This implies that a text or binary array is flattened to a 1D list of values. Given an n-dimensional 
array of dimensions `D=(d1,d2...,dn)`, a value at index `I=(i1,i2,....,in)` will be stored in the 1D list at index
`Sigma(I[i]*Pi(D[i+1:]) for 1<=i<=n)`.

For example, the array `[[0,1],[2,3]]` with dimensions `(2,2)` is flattened out to the list `(0,1,2,3,4,5,6,7)`. These
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

