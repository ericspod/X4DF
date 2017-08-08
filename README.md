# X4DF
X4DF: Extensible 4D Data Fields

This is an XML data format for representing mesh and image data. It's intension is to provide a common mechanism for storing
3D/4D mesh and 2D/3D/4D image data with spatiotemporal parameters. The format for mesh and image data is designed to be 
general to permit custom data types to be stored while still being defined in a common manner. Arbitrary secondary data
can be stored using metadata tags to associate information with mesh, image, and array components. 

## Array Definition

Array data can be stored as text or as binary data. In the XML text data is stored directly but binary data (compressed
or uncompressed) must be encoded in base64 to ensure the file remains a valid text document.

In either case array values are stored in rightmost index order, that is to say the rightmost index is the least
significant. This implies that a text or binary array is flattened out to a 1D list of values. Given an n-dimensional 
array of dimensions `D=(d1,d2...,dn)` a value at index `I=(i1,i2,....,in)` will be stored in the 1D list at position
`Sigma(I[i]*Pi(D[i+1:]) for 1<=i<=n)`.

For example, the array `[[0,1],[2,3]]` with dimensions `(2,2)` is flattened out to the list `(0,1,2,3,4,5,6,7)`. These
values would then be stored in a chosen data format in binary or as text. 

The valid formats for array data are as follows:
 * ASCII - data is stored as the textual representation of the array, with elements formatted for the specified type 
 * BASE64 - data is stored in binary representation and then encoded in base64
 * BASE64_GZ - data is stored in binary representation, compressed with the gzip algorithm (RFC 1952), and then encoded in base64
 * BINARY - data is stored in binary representation directly, this must be in a separate binary file 
 * BINARY_GZ - data is stored in binary representation directly, compressed with the gzip algorithm (RFC 1952), this must be in a separate binary file 

### Text Array Order

In textual array format, values are stored in rightmost index first order, typically with rows of an array being printed
to one text row separated by newline characters. For a 2D array whose indices are (row, column), each row is printed on 
separate lines, eg. the array `[[0,1],[2,3]]` has rows `[0,1]` and `[2,3]` thus would be stored textually as `0 1\n2 3\n`.

For arrays above 2 dimensions, the rightmost index first ordering implies that the last two dimensions are interpreted as
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