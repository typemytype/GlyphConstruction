import weakref
import re
from math import cos, sin, radians

from fontTools.misc.transform import Transform
from robofab.pens.boundsPen import BoundsPen

# splitters

glyphNameSplit = "="
unicodeSplit = "|"
baseGlyphSplit = "_"
markGlyphSplit = "+"
positionSplit = "@"
positionXYSplit = ","
positionBaseSplit = ":"
glyphSuffixSplit = "."
metricsSuffixSplit = "^"
glyphCommentSuffixSplit = "#"
glyphMarkSuffixSplit = "!"

glyphNameEscape = "/"
escapeReplacment = "((ligatureEscape))"


"""

Laringacute = L _ a + ring@center,top + acute@center,top | 159AFFF * 1, 0, 0, 1 # this is an example

"""

# legal positions

legalFontInfoAttributes = set("descender xHeight capHeight ascender".split(" "))
legalGlyphMetricHorizontalPositions = set("origin width".split(" "))
legalGlyphMetricVerticalPositions = set("origin height".split(" "))
legalBoundsPositions = set("left innerLeft right innerRight top innerTop bottom innerBottom".split(" "))
legalCalculatablePositions = legalBoundsPositions | set(["center"])

### math 

def _intersectAngles(point1, angle1, point2, angle2):
    point1A = point1
    point2A = point2
    point1B = point1[0] + cos(radians(angle1)), point1[1] + sin(radians(angle1))
    point2B = point2[0] + cos(radians(angle2)), point2[1] + sin(radians(angle2))
    intersection = _intesectLines((point1A, point1B), (point2A, point2B))
    return intersection

def _intesectLines((pt1, pt2), (pt3, pt4)):
    denom = (pt1[0] - pt2[0]) * (pt3[1] - pt4[1]) - (pt1[1] - pt2[1]) * (pt3[0] - pt4[0])
    if _roundFloat(denom) == 0:
        return None
    x = (pt1[0] * pt2[1] - pt1[1] * pt2[0]) * (pt3[0] - pt4[0]) - (pt1[0] - pt2[0]) * (pt3[0] * pt4[1] - pt3[1] * pt4[0])
    x /= denom
    y = (pt1[0] * pt2[1] - pt1[1] * pt2[0]) * (pt3[1] - pt4[1]) - (pt1[1] - pt2[1]) * (pt3[0] * pt4[1] - pt3[1] * pt4[0])
    y /= denom
    return (x, y)

def _roundFloat(f, error=10000.0):
    return round(f * error) / error

def _diffPoint((x1, y1), (x2, y2)):
    return (x1 - x2, y1 - y2)

## errors

class GlyphBuilderError(Exception): 
    pass

## glyph object

class ConstructionGlyph(object):
        
    def __init__(self, parent):
        self.getParent = weakref.ref(parent)
        self.name = None
        self.width = 0
        self.unicode = None
        self.components = []
        self.note = ""
        self.mark = None
        self._bounds = None
    
    def addComponent(self, glyphName, transformation):
        self.components.append((glyphName, transformation))
    
    def __len__(self):
        return 0
    
    def __iter__(self):
        while 0:
            yield
    
    def _get_bounds(self):
        if self._bounds is None:
            pen = BoundsPen(self.getParent())
            self.draw(pen)
            self._bounds = pen.bounds
        return self._bounds
    
    bounds = property(_get_bounds)
    
    def draw(self, pen):
        for glyphName, transformation in self.components:
            pen.addComponent(glyphName, transformation)
    
    def drawPoints(self, pen):
        self.draw(pen)
    
        
        


def parsePosition(markGlyph, font, positionName, direction, prefix="", isBase=False):        
    position = (0, 0)
    fixedPosition = False
    
    if direction == "x":
        italicAngle = getattr(font.info, "italicAngle", 0)
        if italicAngle is None:
            italicAngle = 0
        angle = 90 + italicAngle
    else:
        angle = 0
    
    if markGlyph not in font:
        return position, angle, fixedPosition
        
    glyph = font[markGlyph]
    
    bounds = glyph.bounds
    left = bottom = right = top = width = height = 0
    if bounds:
        left, bottom, right, top = bounds
        width = right - left
        height = top - bottom
    
    while 1:
        
        # try to convert to float
        
        try:
            value = float(positionName)            
            if direction == "x":
                position = (value-left, 0)
            elif direction == "y":
                position = (0, value-bottom)
            fixedPosition = True
            break
        except:
            pass
            
        # glyph anchor + prefix
        found = _findAnchor(glyph.anchors, "%s%s" %(prefix, positionName))
        if found is not None:
            position = found
            break
            
        # glyph anchor
        found = _findAnchor(glyph.anchors, positionName)
        if found is not None:
            position = found
            break
        
        # glyph guide + prefix
        found = _findGuide(glyph.guides, "%s%s" %(prefix, positionName))
        if found is not None:
            position, angle = found
            break
        
        # glyph guide
        found = _findGuide(glyph.guides, positionName)
        if found is not None:
            position, angle = found
            break
                            
        # font guide
        found = _findGuide(font.guides, positionName)
        if found is not None:
            if isBase:
                if direction == "x":
                    positionName = "center"
                elif direction == "y":
                    positionName = "top"
            else:
                position, angle = found
                break
            
        # glyph metrics
        if direction == "x" and positionName in legalGlyphMetricHorizontalPositions:
            if positionName == "origin":
                position = (0, 0)
            elif positionName == "width":
                position = (glyph.width, 0)
            fixedPosition = True
            break
        if direction == "y" and positionName in legalGlyphMetricVerticalPositions:
            if positionName == "origin":
                position = (0, 0)
            elif positionName == "height":
                position = (0, getattr(glyph, "height", height))
            fixedPosition = True
            break
            
        # font metrics
        if positionName in legalFontInfoAttributes:
            found = _findFontInfoValue(font, positionName)
            if found is not None:
                if isBase:
                    position = _diffPoint(found, (0, top))
                else:
                    position = _diffPoint(found, (0, bottom))
                fixedPosition = True
                break

        
        # calculate
        centerValue = .5    
        if positionName.endswith("%"):
            try:
                centerValue = float(positionName[:-1]) * 0.01
                positionName = "center"
            except:
                pass
        
        if positionName in legalCalculatablePositions:

            if positionName == "center":
                if isBase:
                    position = (left + width * centerValue, bottom + height * centerValue)
                else:
                    position = (left + width * centerValue + width - width * centerValue * 2,  
                                bottom + height * centerValue + height - height * centerValue * 2)
                    
            elif positionName in legalBoundsPositions:
                
                if direction == "y" and positionName == "top":
                    if isBase:
                        position = (0, top)
                    else:
                        position = (0, bottom)
                if direction == "y" and positionName == "innerTop":
                    position = (0, top)
                elif direction == "y" and positionName == "bottom":
                    if isBase:
                        position = (0, bottom)
                    else:
                        position = (0, top)
                elif direction == "y" and positionName == "innerBottom":
                    position = (0, bottom)
                elif direction == "x" and positionName == "left":
                    if isBase:
                        position = (left, 0)
                    else:
                        position = (right, 0)
                elif direction == "x" and positionName == "innerLeft":
                    position = (left, 0)
                elif direction == "x" and positionName == "right":
                    if isBase:
                        position = (right, 0)
                    else:
                        position = (left, 0)                                         
                elif direction == "x" and positionName == "innerRight":
                    position = (right, 0)
        break
    return position, angle, fixedPosition

def _findAnchor(anchors, name):
    for anchor in anchors:
        if anchor.name == name:
            return (anchor.x, anchor.y)
    return None

def _findGuide(guides, name):
    for guide in guides:
        if guide.name == name:
            return (guide.x, guide.y), guide.angle
    return None

def _findFontInfoValue(font, name):
    value = getattr(font.info, name)
    if value is None:
        value = 0
    return (0, value)

def parseMarks(baseGlyph, markGlyph, font, markTransformMap, advanceWidth, advanceHeight):
    xx, xy, yx, yy, x, y = 1, 0, 0, 1, advanceWidth, advanceHeight
    
    baseGlyphX = baseGlyphY = baseGlyph
    markFixedX = markFixedY = False
    
    if positionSplit in markGlyph:
        markGlyph, position = markGlyph.split(positionSplit)
        
        if positionXYSplit in position:
            positions = position.split(positionXYSplit)
            if len(positions) == 6:
                xx, xy, yx, yy, positionX, positionY = positions
                xx = float(xx)
                xy = float(xy)
                yx = float(yx)
                yy = float(yy)
            elif len(positions) == 2:
                positionX, positionY = positions
            else:
                raise GlyphBuilderError, "mark positions should have 6 or 2 options"
        else:
            positionX = positionY = position
        
        if positionBaseSplit in positionX:
            baseGlyphX, positionX = positionX.split(positionBaseSplit)
        
        if positionBaseSplit in positionY:
            baseGlyphY, positionY = positionY.split(positionBaseSplit)
                
        baseX = baseY = 0
        markX = markY = 0
        
        if markGlyph not in font:
            if glyphSuffixSplit in markGlyph:
                markGlyph = markGlyph.split(glyphSuffixSplit)[0]
        
        markPoint1, markAngle1, markFixedX = parsePosition(markGlyph, font, positionX, direction="x", prefix="_")
        markPoint2, markAngle2, markFixedY = parsePosition(markGlyph, font, positionY, direction="y", prefix="_")
        intersection = _intersectAngles(markPoint1, markAngle1, markPoint2, markAngle2)
        if intersection is not None:
            markX, markY = intersection
        
        if baseGlyphX in font and baseGlyphY in font:
            basePoint1, baseAngle1, _ = parsePosition(baseGlyphX, font, positionX, direction="x", isBase=True)
            basePoint2, baseAngle2, _ = parsePosition(baseGlyphY, font, positionY, direction="y", isBase=True)
            intersection = _intersectAngles(basePoint1, baseAngle1, basePoint2, baseAngle2)
            if intersection is not None:
                baseX, baseY = intersection

        # calculate the offset
    
        if not markFixedX:
            x += baseX - markX
        else:
            x += markX
        
        if not markFixedY:            
            y += baseY - markY
        else:
            y += markY
        
    if not markFixedX:
        baseTransform = markTransformMap.get(baseGlyphX)
        if baseTransform:
            x += baseTransform[4] - advanceWidth
    
    if not markFixedY:
        baseTransform = markTransformMap.get(baseGlyphY)
        if baseTransform:
            y += baseTransform[5] - advanceHeight
        
    
    transformMatrix = (xx, xy, yx, yy, x, y)
    return markGlyph, transformMatrix

reGlyphName = re.compile(r'([a-zA-Z_][a-zA-Z0-9_.]*|.notdef)')

def parseWidth(construction, font):
    widthValue = None
    if metricsSuffixSplit in construction:
        construction, widthValue = construction.split(metricsSuffixSplit)
        try:
            widthValue = float(widthValue)
        except:
            if widthValue in font:
                width = font[widthValue].width            
            else:
                lastIndex = 0
                newText = "widthValue="
                for i in reGlyphName.finditer(widthValue):
                    newText += widthValue[lastIndex:i.start()]
                    glyphName = i.group()
                    if glyphName in font:
                        newText += "%s" % font[glyphName].width
                    lastIndex = i.end()
                newText += widthValue[lastIndex:]
                try:
                    exec(newText)
                except:
                    widthValue = None
    return widthValue, construction

def parseUnicode(construction, font=None):
    unicode = None
    if unicodeSplit in construction:
        construction, unicode = construction.split(unicodeSplit)
        try:
            unicode = int(unicode, 16)
        except:
            unicode = None
    return unicode, construction

def parseMark(construction, font=None):
    mark = None
    if glyphMarkSuffixSplit in construction:
        construction, markString = construction.split(glyphMarkSuffixSplit)
        markString = markString.split(positionXYSplit)
        if len(markString) == 4:
            try:
                r = float(markString[0])
                g = float(markString[1])
                b = float(markString[2])
                a = float(markString[3])
                mark = r, g, b, a
            except:
               mark = None
    return mark, construction

glyphAttrFuncMap = {
        "unicode" : parseUnicode,
        "mark" : parseMark,
        "width" : parseWidth 
    }

def parseGlyphattributes(construction, font):
    attrs = {}
    currentKey = None
    currentValue = ""
    newConstruction = ""
    for c in construction:
        if c == metricsSuffixSplit:
            currentKey = "width"
            currentValue = ""
        elif c == glyphMarkSuffixSplit:
            currentKey = "mark"
            currentValue = ""
        elif c == unicodeSplit:
            currentKey = "unicode"
            currentValue = ""
        if currentKey:
            currentValue += c
            attrs[currentKey] = currentValue
        else:
            newConstruction += c
    values = {}
    for attr, value in attrs.items():
        func = glyphAttrFuncMap[attr]
        value, _ = func(value, font)
        values[attr] = value
    return values, newConstruction
    
def parseNote(construction):
    note = ""
    if glyphCommentSuffixSplit in construction:
        construction, note = construction.split(glyphCommentSuffixSplit)
        # remove trailing spaces
        note = note.strip()
    return note, construction

def parseGlyphName(construction):
    return construction.split(glyphNameSplit)

def GlyphConstructionBuilder(construction, font):
    destination = ConstructionGlyph(font)
    
    try:
        construction = str(construction)
    except:
        return destination
    
    destination.note, construction = parseNote(construction)
    
    if glyphNameSplit not in construction:
        return destination
        
    construction = construction.replace(" ", "").replace("\t", "")
    
    destination.name, construction = parseGlyphName(construction)
    
    glyphAttributes, construction = parseGlyphattributes(construction, font)
    
    #destination.mark, construction = parseMarkColor(construction)
    
    #destination.unicode, construction = parseUnicode(construction)
    
    #metrics, construction = parseMetrics(construction, font)
    
    construction = construction.replace("%s%s" %(glyphNameEscape, baseGlyphSplit), escapeReplacment)
    
    baseGlyphs = construction.split(baseGlyphSplit)
    
    
    advanceWidth = 0
    
    for baseGlyph in baseGlyphs:
        markGlyphs = baseGlyph.split(markGlyphSplit)
        baseGlyph = None    
        baseMarkGlyph = None
        baseTransformMatrix = [1, 0, 0, 1, 0, 0]
        markTransformMap = {}
        
        advanceHeight = 0
        
        for markGlyph in markGlyphs:
            
            component, transformMatrix = parseMarks(baseMarkGlyph, markGlyph, font, markTransformMap, advanceWidth, advanceHeight)
            destination.addComponent(component, transformMatrix)
            
            markTransformMap[component] = transformMatrix
            
            baseMarkGlyph = component
            
            if baseGlyph is None:
                baseGlyph = component
                baseTransformMatrix = transformMatrix
            
        if baseGlyph in font:
            width = font[baseGlyph].width
            t = Transform(*baseTransformMatrix)
            width, y = t.transformPoint((width-advanceWidth, 0))
            advanceWidth += width
            
    destination.width = advanceWidth
    
    for key, value in glyphAttributes.items():
        setattr(destination, key, value)
    
    return destination

def MakeGlyphConstructionListFromString(txt):
    lines = []
    for line in txt.split("\n"):
        line = line.strip()
        if line and line[0] == glyphCommentSuffixSplit:
            continue
        if not line and not lines:
            continue
        lines.append(line)
    # remove trailing empty lines
    while lines and not lines[-1]:
        lines.pop()
    return lines


    