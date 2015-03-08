Glyph Construction
==================

[This is a draft]

- A language to describe how a shape is constructed.
- Doesnt contain any design.
- A *.glyphConstruction file should be interchangable between fonts.
- Must be readable.

A line starting with or anything after a `#` is a comment and will not be used during execution.


### Assigning a construction to a glyph

    <destGlyphName> = <glyphName> + <glyphName>  

Add one or more component to a glyph with a name `<destGlyphName>`

Example:

    Aacute = A + acute
 
### Unicodes

    <destGlyphName> = <glyphName> + <glyphName> | <unicode>

Example:

    Aacute = A + acute | 00C1
   
### Positioning

Will position the added component related to the current glyph.

#### By Numbers

Example:

    Aacute = A + acute@100

Example:
    
    Aacute = A + acute@100,100

#### By Percentages   

Example:

    Aacute = A + acute@50%,50%
    
#### By Reference  

A reference could be (in this order):

* double anchor (with the _<anchorName> quotation)
* a single anchor name
* a guide name
* a calculated word: **top**, **bottom**, **left**, **right**, **innerLeft**, **innerRight**, **center**

Example:

    Aacute = A + acute@center,top

#### By Transformation Matrix

`@` followed by a transfromation matrix: 6 values `xx, xy, yx, yy, x, y`

Example:

    Aacute = A + acute@1, 0, 0, 1, 100, 100

#### Change the current glyph

The current glyph is always the last component added. `Aacute = A + acute` Will first add component with name `A` there is no current glyph. Adding component with name `acute`, the current glyph is `A`. Force the current glyph with `@<glyphName>:<pos>`

Example:

    Ocircumflexdotaccent =  O + circumflex@center,top + dotaccent@O:center,bottom

### Stacking Vertically

Example:

    Aringacute = A + ring@center,top + acute@center,top
   
### Stacking Horizontally

Example:

    ffi = f _ f _ i

### Variables

Variables are possible, the have to be decleared at the top of the document.

Declaration:
	
	$name = something
	
Usage:

	{name}	

Example:

	$myColorMark = 1, 0, 0, 1
	
	agrave = a + grave@center,top ! {myColorMark}
