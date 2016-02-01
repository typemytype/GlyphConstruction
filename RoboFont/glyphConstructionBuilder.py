import weakref
import re
import os
from math import cos, sin, radians
import operator

from fontTools.misc.transform import Transform
from robofab.pens.boundsPen import BoundsPen

# splitters

glyphNameSplit = "="
unicodeSplit = "|"
baseGlyphSplit = "&"
markGlyphSplit = "+"
positionSplit = "@"
positionXYSplit = ","
positionBaseSplit = ":"
glyphSuffixSplit = "."
metricsSuffixSplit = "^"
glyphCommentSuffixSplit = "#"
glyphMarkSuffixSplit = "!"
flipMarkGlyphSplit = "~"
glyphCheckIfExists = "?"

variableDeclarationStart = "$"
variableDeclarationEnd = ""

explicitMathStart = '`'
explicitMathEnd = '`'

"""
$variableName = n
Laringacute = L & a + ring@~center,~`top+10` + acute.cap@height,top ^ 100, `l*2` | 159AFFF ! 1, 0, 0, 1 # this is an example, and this is a variable {variableName}
"""

# legal positions

legalFontInfoAttributes = set("descender xHeight capHeight ascender".split(" "))
legalGlyphMetricHorizontalPositions = set("origin width".split(" "))
legalGlyphMetricVerticalPositions = set("origin height".split(" "))
legalBoundsPositions = set("left innerLeft right innerRight top innerTop bottom innerBottom".split(" "))
legalCalculatablePositions = legalBoundsPositions | set(["center"])


# math

def _intersectAngles(point1, angle1, point2, angle2):
    """
    Intersect two rays, described by a point and an angle.

    >>> _intersectAngles((100, 100), 45, (100, 200), -45)
    (150.00000000000094, 150.00000000000094)
    >>> _intersectAngles((100, 100), 45, (100, 200), 45) is None
    True
    """
    point1A = point1
    point2A = point2
    point1B = point1[0] + cos(radians(angle1)), point1[1] + sin(radians(angle1))
    point2B = point2[0] + cos(radians(angle2)), point2[1] + sin(radians(angle2))
    intersection = _intesectLines((point1A, point1B), (point2A, point2B))
    return intersection


def _intesectLines((pt1, pt2), (pt3, pt4)):
    """
    Intersect two lines.

    >>> _intesectLines(((100, 100), (200, 200)), ((100, 200), (200, 100)))
    (150, 150)
    >>> _intesectLines(((200, 100), (200, 200)), ((300, 200), (300, 200))) is None
    True
    """
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


# regex

if variableDeclarationEnd:
    variableDeclarationEnd = "\%s" % variableDeclarationEnd
varialbesRE = re.compile(r"\%s\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\=\s*(?P<value>.*)%s" % (variableDeclarationStart, variableDeclarationEnd))

simpleVariableRe = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

percentageRe = re.compile(r"[0-9]*%")

glyphNameRe = re.compile(r'([a-zA-Z_][a-zA-Z0-9_.]*|.notdef)')

explicitMathRe = re.compile(r'\%s(?P<explicitMath>.*?)\%s' % (explicitMathStart, explicitMathEnd))


# error

class GlyphBuilderError(Exception):
    pass


# glyph object


class ConstructionGlyph(object):

    """
    A Glyph like object able set some basic attributes, add components and draw.
    """

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

    def _get_leftMargin(self):
        bounds = self.bounds
        if bounds is None:
            return None
        xMin, yMin, xMax, yMax = bounds
        return xMin

    def _set_leftMargin(self, value):
        if value is None:
            return
        bounds = self.bounds
        if bounds is None:
            return
        xMin, yMin, xMax, yMax = bounds
        diff = value - xMin
        self.move((diff, 0))
        self.width += diff

    leftMargin = property(_get_leftMargin, _set_leftMargin)

    def _get_rightMargin(self):
        bounds = self.bounds
        if bounds is None:
            return None
        xMin, yMin, xMax, yMax = bounds
        return self.width - xMax

    def _set_rightMargin(self, value):
        if value is None:
            return
        bounds = self.bounds
        if bounds is None:
            return
        xMin, yMin, xMax, yMax = bounds
        self.width = xMax + value

    rightMargin = property(_get_rightMargin, _set_rightMargin)

    def move(self, (moveX, moveY)):
        oldBounds = self._bounds
        for i in range(len(self.components)):
            glyphName, (xx, xy, yx, yy, x, y) = self.components[i]
            self.components[i] = glyphName, (xx, xy, yx, yy, x+moveX, y+moveY)
        if oldBounds:
            xMin, yMin, xMax, yMax = oldBounds
            xMin += moveX
            yMin += moveY
            xMax += moveX
            yMax += moveY
            self._bounds = (xMin, yMin, xMax, yMax)

    def draw(self, pen):
        for glyphName, transformation in self.components:
            pen.addComponent(glyphName, transformation)

    def drawPoints(self, pen):
        self.draw(pen)


class MathPoint(tuple):

    """
    A math object for calculation with tuples.
    """

    def __new__(cls, point, allowTupleMathOnly=False):
        return super(MathPoint, cls).__new__(cls, point)

    def __init__(self, point, allowTupleMathOnly=False):
        self.allowTupleMathOnly = allowTupleMathOnly

    def _operation(self, other, operation):
        x, y = self
        ox = oy = 0
        if isinstance(other, tuple):
            ox, oy = other
        elif not self.allowTupleMathOnly:
            ox = oy = other
        if ox != 0:
            x = operation(x, ox)
        if oy != 0:
            y = operation(y, oy)
        return self.__class__((x, y), self.allowTupleMathOnly)

    def __add__(self, other):
        return self._operation(other, operator.add)

    def __iadd__(self, other):
        return self._operation(other, operator.iadd)

    def __sub__(self, other):
        return self._operation(other, operator.sub)

    def __isub__(self, other):
        return self._operation(other, operator.isub)

    def __mul__(self, other):
        return self._operation(other, operator.mul)

    def __div__(self, other):
        return self._operation(other, operator.div)

    def __truediv__(self, other):
        return self._operation(other, operator.truediv)


def _parsePosition(name, position, angle, fixedPosition, glyph, font, direction, isBase, prefix, top, bottom, left, right, width, height):
    # glyph anchor + prefix
    found = _findAnchor(glyph, "%s%s" % (prefix, name))
    if found is not None:
        return found, angle, fixedPosition

    # glyph anchor
    found = _findAnchor(glyph, name)
    if found is not None:
        return found, angle, fixedPosition

    # glyph guide + prefix
    found = _findGuide(glyph, "%s%s" % (prefix, name))
    if found is not None:
        position, angle = found
        return position, angle, fixedPosition

    # glyph guide
    found = _findGuide(glyph, name)
    if found is not None:
        position, angle = found
        return position, angle, fixedPosition

    # font guide
    found = _findGuide(font, name)
    if found is not None:
        if isBase:
            if direction == "x":
                name = "center"
            elif direction == "y":
                name = "top"
        else:
            position, angle = found
            return position, angle, fixedPosition

    # glyph metrics
    if direction == "x" and name in legalGlyphMetricHorizontalPositions:
        if name == "origin":
            position = (0, 0)
        elif name == "width":
            position = (glyph.width, 0)
        fixedPosition = True
        return position, angle, fixedPosition

    if direction == "y" and name in legalGlyphMetricVerticalPositions:
        if name == "origin":
            position = (0, 0)
        elif name == "height":
            position = (0, getattr(glyph, "height", height))
        fixedPosition = True
        return position, angle, fixedPosition

    # font metrics
    if name in legalFontInfoAttributes:
        found = _findFontInfoValue(font, name)
        if found is not None:
            _, value = found
            position = (0, value-bottom)

            # if isBase:
            #     position = _diffPoint(found, (0, top))
            # else:
            #     position = _diffPoint(found, (0, bottom))
            fixedPosition = True
            return position, angle, fixedPosition

    # calculate
    centerValue = .5
    if name.endswith("%"):
        try:
            centerValue = float(name[:-1]) * 0.01
            name = "center"
        except:
            pass

    if name in legalCalculatablePositions:
        if name == "center":
            if isBase:
                position = (left + width * centerValue, bottom + height * centerValue)
            else:
                position = (left + width * centerValue + width - width * centerValue * 2,
                            bottom + height * centerValue + height - height * centerValue * 2)

        elif name in legalBoundsPositions:

            if direction == "y" and name == "top":
                if isBase:
                    position = (0, top)
                else:
                    position = (0, bottom)
            if direction == "y" and name == "innerTop":
                position = (0, top)
            elif direction == "y" and name == "bottom":
                if isBase:
                    position = (0, bottom)
                else:
                    position = (0, top)
            elif direction == "y" and name == "innerBottom":
                position = (0, bottom)
            elif direction == "x" and name == "left":
                if isBase:
                    position = (left, 0)
                else:
                    position = (right, 0)
            elif direction == "x" and name == "innerLeft":
                position = (left, 0)
            elif direction == "x" and name == "right":
                if isBase:
                    position = (right, 0)
                else:
                    position = (left, 0)
            elif direction == "x" and name == "innerRight":
                position = (right, 0)
    return position, angle, fixedPosition


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

    names = simpleVariableRe.findall(positionName)
    percentage = percentageRe.findall(positionName)
    nameSpace = dict()

    # try to convert to float
    if not names and not percentage:
        # resolve simple math operations
        try:
            exec("positionName=%s" % positionName)
        except:
            pass
    try:
        value = float(positionName)
        if direction == "x":
            position = (value-left, 0)
        elif direction == "y":
            position = (0, value-bottom)
        fixedPosition = True
        return position, angle, fixedPosition
    except:
        pass

    data = dict(
            glyph=glyph,
            font=font,
            direction=direction,
            isBase=isBase,
            prefix=prefix,
            top=top,
            bottom=bottom,
            left=left,
            right=right,
            width=width,
            height=height
        )

    for name in names + percentage:
        position, angle, fixedPosition = _parsePosition(name, position, angle, fixedPosition, **data)
        nameSpace[name] = MathPoint(position, not isBase and not fixedPosition)

    try:
        exec("position=%s" % positionName, nameSpace)
    except ZeroDivisionError:
        raise GlyphBuilderError("ZeroDivisionError: integer division or modulo by zero in '%s'" % positionName)
    except SyntaxError:
        if not percentage:
            raise GlyphBuilderError("SyntaxError: invalid syntax in '%s'" % positionName)
    except:
        raise GlyphBuilderError("Something went wrong in '%s'" % positionName)
    position = nameSpace.get("position", position)
    return position, angle, fixedPosition


def _findAnchor(glyph, name):
    anchors = glyph.anchors
    for anchor in anchors:
        if anchor.name == name:
            return (anchor.x, anchor.y)
    return None


def _findGuide(glyph, name):
    if hasattr(glyph, "guides"):
        guides = glyph.guides
        for guide in guides:
            if guide.name == name:
                return (guide.x, guide.y), guide.angle
    return None


def _findFontInfoValue(font, name):
    value = getattr(font.info, name)
    if value is None:
        value = 0
    return (0, value)


def parsePositions(baseGlyph, markGlyph, font, markTransformMap, advanceWidth, advanceHeight):
    xx, xy, yx, yy, x, y = 1, 0, 0, 1, advanceWidth, advanceHeight

    baseGlyphX = baseGlyphY = baseGlyph
    markFixedX = markFixedY = False

    flipX = flipY = False

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
                raise GlyphBuilderError("mark positions should have 6 or 2 options")
        else:
            positionX = positionY = position

        if positionBaseSplit in positionX:
            baseGlyphX, positionX = positionX.split(positionBaseSplit)

        if positionBaseSplit in positionY:
            baseGlyphY, positionY = positionY.split(positionBaseSplit)

        if flipMarkGlyphSplit in positionX:
            flipX = True
            positionX = positionX.replace(flipMarkGlyphSplit, "")

        if flipMarkGlyphSplit in positionY:
            flipY = True
            positionY = positionY.replace(flipMarkGlyphSplit, "")

        if positionX and positionY:
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

    if flipX:
        bounds = font[markGlyph].bounds
        if bounds:
            minx, miny, maxx, maxy = bounds
            bt = Transform(*transformMatrix)
            minx, miny = bt.transformPoint((minx, miny))
            maxx, maxy = bt.transformPoint((maxx, maxy))
            t = Transform()
            t = t.translate(0, miny)
            t = t.scale(1, -1)
            t = t.translate(0, -maxy)
            t = t.transform(bt)
            transformMatrix = t[:]

    if flipY:
        bounds = font[markGlyph].bounds
        if bounds:
            minx, miny, maxx, maxy = bounds
            bt = Transform(*transformMatrix)
            minx, miny = bt.transformPoint((minx, miny))
            maxx, maxy = bt.transformPoint((maxx, maxy))
            t = Transform()
            t = t.translate(minx, 0)
            t = t.scale(-1, 1)
            t = t.translate(-maxx, 0)
            t = t.transform(bt)
            transformMatrix = t[:]
    return markGlyph, transformMatrix


def _parseGlyphMetric(construction, font, attr):
    value = None
    construction = reEscapeMathOperations(construction)
    if metricsSuffixSplit in construction:
        construction, value = construction.split(metricsSuffixSplit)
        try:
            value = float(value)
        except:
            if value in font:
                value = getattr(font[value], attr)
            else:
                lastIndex = 0
                newText = "value="
                for i in glyphNameRe.finditer(value):
                    newText += value[lastIndex:i.start()]
                    glyphName = i.group()
                    if glyphName in font:
                        newText += "%s" % getattr(font[glyphName], attr)
                    lastIndex = i.end()
                newText += value[lastIndex:]
                try:
                    exec(newText)
                except:
                    value = None
    return value, construction


def parseWidth(construction, font):
    return _parseGlyphMetric(construction, font, "width")


def parseLeftMargin(construction, font):
    return _parseGlyphMetric(construction, font, "leftMargin")


def parseRightMargin(construction, font):
    return _parseGlyphMetric("%s%s" % (metricsSuffixSplit, construction), font, "rightMargin")


def parseUnicode(construction, font=None):
    """
    Parse unicode from construction.
    unicode splitter: |

    >>> parseUnicode("agrave = a + grave | 00E0")
    (224, 'agrave = a + grave ')
    """
    unicode = None
    if unicodeSplit in construction:
        construction, unicode = construction.split(unicodeSplit)
        try:
            unicode = int(unicode, 16)
        except:
            unicode = None
    return unicode, construction


def parseMark(construction, font=None):
    """
    Parse mark from construction.
    mark splitter: !

    >>> parseMark("agrave = a + grave ! 1, 0, 0, 1")
    ((1.0, 0.0, 0.0, 1.0), 'agrave = a + grave ')
    """
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
        "unicode": parseUnicode,
        "mark": parseMark,
        "width": parseWidth,
        "leftMargin": parseLeftMargin,
        "rightMargin": parseRightMargin
    }


def parseGlyphattributes(construction, font):
    """
    Parse glyph attributes from constructtion.
    width splitter: ^ (could be a tuple referring to leftMargin and rightMargin)
    mark splitter:  !
    unicode splitter: |

    >>> font = testDummyFont()
    >>> parseGlyphattributes("name | 0000 ! 1, 0, 0, 1 ^ 100", font)
    ({'width': 100.0, 'unicode': 0, 'mark': (1.0, 0.0, 0.0, 1.0)}, 'name ')

    >>> parseGlyphattributes("name ! 1, 0, 0, 1 ^ 100 | 0000", font)
    ({'width': 100.0, 'unicode': 0, 'mark': (1.0, 0.0, 0.0, 1.0)}, 'name ')

    >>> parseGlyphattributes("name ^ 100 | 0000 ! 1, 0, 0, 1", font)
    ({'width': 100.0, 'unicode': 0, 'mark': (1.0, 0.0, 0.0, 1.0)}, 'name ')

    >>> parseGlyphattributes("name ^ 100 | 0000", font)
    ({'width': 100.0, 'unicode': 0}, 'name ')

    >>> parseGlyphattributes("name ^ 100", font)
    ({'width': 100.0}, 'name ')

    >>> parseGlyphattributes("name | 0000", font)
    ({'unicode': 0}, 'name ')

    >>> parseGlyphattributes("name ^ 100", font)
    ({'width': 100.0}, 'name ')

    >>> parseGlyphattributes("name ^ 10, 20", font)
    ({'leftMargin': 10.0, 'rightMargin': 20.0}, 'name ')
    """
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
    if "width" in attrs:
        if positionXYSplit in attrs["width"]:
            margins = attrs["width"].split(positionXYSplit)
            if len(margins) == 2:
                attrs["leftMargin"], attrs["rightMargin"] = margins
                del attrs["width"]
    for attr, value in attrs.items():
        func = glyphAttrFuncMap[attr]
        value, _ = func(value, font)
        values[attr] = value
    return values, newConstruction


def parseNote(construction):
    """
    Parse note from construction.
    note splitter: #
        * and must be the last part of the construction

    >>> parseNote("agrave = a + grave # this is a note")
    ('this is a note', 'agrave = a + grave ')
    """
    note = ""
    if glyphCommentSuffixSplit in construction:
        construction, note = construction.split(glyphCommentSuffixSplit)
        # remove trailing spaces
        note = note.strip()
    return note, construction


def parseGlyphName(construction):
    """
    Parse glyph name from construction.
    glyph name splitter: =

    >>> parseGlyphName("agrave = a + grave")
    ('agrave', ' a + grave')
    """
    glyphName, construction = construction.split(glyphNameSplit)
    glyphName = glyphName.strip()
    return glyphName, construction


escapeMathOperatorMap = {
        "+": "<<add>>",
        "-": "<<sub>>"
    }

escapeMathOperatorMapReversed = {value: key for key, value in escapeMathOperatorMap.items()}


def forceEscapingMathOperations(data):
    """
    force escape math to restore it lateron,
    as some operators are used inside a glyph construction,
    especially the + and - .

    >>> forceEscapingMathOperations("`10 + 5`")
    '10 <<add>> 5'
    >>> forceEscapingMathOperations("`10 - 5`")
    '10 <<sub>> 5'
    """
    result = ""
    index = 0
    for found in explicitMathRe.finditer(data):
        result += data[index:found.start()]
        seq = found.group("explicitMath")
        for find, replace in escapeMathOperatorMap.items():
            seq = seq.replace(find, replace)
        result += seq
        index = found.end()
    result += data[index:]
    return result


def reEscapeMathOperations(data):
    """
    Re escape math back to readable and executable math.

    >>> reEscapeMathOperations("10 <<add>> 5")
    '10 + 5'
    >>> reEscapeMathOperations("10 <<sub>> 5")
    '10 - 5'
    """
    for find, replace in escapeMathOperatorMapReversed.items():
        data = data.replace(find, replace)
    return data


def removeSpacesAndTabs(data):
    """
    Remove all tabs and spaces.

    >>> removeSpacesAndTabs("a Sting With Spaces")
    'aStingWithSpaces'
    >>> removeSpacesAndTabs("a\tSting\tWith\tTabs")
    'aStingWithTabs'
    """
    return data.replace(" ", "").replace("\t", "")


def GlyphConstructionBuilder(construction, font):
    # create a construction glyph
    destination = ConstructionGlyph(font)
    # test if the input is a proper string
    try:
        construction = str(construction)
    except:
        return destination
    # parse the note
    destination.note, construction = parseNote(construction)
    # check if there is a = sing
    if glyphNameSplit not in construction:
        return destination
    # remove all spaces and tabs
    construction = removeSpacesAndTabs(construction)
    # escape math formulas inside a ` `
    construction = forceEscapingMathOperations(construction)
    # extract the name
    destination.name, construction = parseGlyphName(construction)
    # extract glyph attributes
    glyphAttributes, construction = parseGlyphattributes(construction, font)
    # split into base glyphs, ligatures
    baseGlyphs = construction.split(baseGlyphSplit)

    advanceWidth = 0
    # start
    for baseGlyph in baseGlyphs:
        # split into mark glyphs
        markGlyphs = baseGlyph.split(markGlyphSplit)
        baseGlyph = None
        baseMarkGlyph = None
        baseTransformMatrix = [1, 0, 0, 1, 0, 0]
        markTransformMap = {}

        advanceHeight = 0

        for markGlyph in markGlyphs:
            markGlyph = reEscapeMathOperations(markGlyph)
            component, transformMatrix = parsePositions(baseMarkGlyph, markGlyph, font, markTransformMap, advanceWidth, advanceHeight)
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


def ParseVariables(txt):
    """
    Parse all variables from all constructions and remove them.

    >>> txt = unichr(10).join([
    ...    "$name = test",
    ...    "$positionX = center",
    ...    "$positionY = 100",
    ...    "aacute = a + acute@positionX, positionY"
    ...    ])
    >>> txt, variables = ParseVariables(txt)
    >>> variables
    {u'positionX': u'center', u'positionY': u'100', u'name': u'test'}
    >>> txt.replace(unichr(10), "")
    u'aacute = a + acute@positionX, positionY'
    """
    variables = {}
    for i in varialbesRE.finditer(txt):
        name = i.group("name")
        value = i.group("value")
        variables[name] = value
        txt = txt.replace(i.group(), "")
    return txt, variables


def ParseGlyphConstructionListFromString(source, font=None):
    """
    Parse glyph constructions from a big text, could be a file path, file object or a string.
    Optionally a font can be provided to check and ignore existing glyph names.

    This returns a list of optimized glyph constructions.

    # Basic parsing with comment
    >>> txt = unichr(10).join([
    ...    "agrave = a + grave",
    ...    "# a comment",
    ...    "aacute = a + acute"
    ...    ])
    >>> ParseGlyphConstructionListFromString(txt)
    [u'agrave = a + grave', u'aacute = a + acute']

    # Basic parsing with variable
    >>> txt = unichr(10).join([
    ...    "$name = grave",
    ...    "agrave = a + {name}",
    ...    "# a comment",
    ...    "aacute = a + acute"
    ...    ])
    >>> ParseGlyphConstructionListFromString(txt)
    [u'agrave = a + grave', u'aacute = a + acute']

    # Parsing with ignore glyph existing glyph names without a font
    >>> font = testDummyFont()

    >>> txt = unichr(10).join([
    ...    "$name = grave",
    ...    "?agrave = a + {name}",
    ...    "# a comment",
    ...    "aacute = a + acute"
    ...    ])
    >>> ParseGlyphConstructionListFromString(txt)
    [u'agrave = a + grave', u'aacute = a + acute']

    # Parsing with ignore glyph existing glyph names
    >>> txt = unichr(10).join([
    ...    "$name = grave",
    ...    # the next line will be ignored",
    ...    "?agrave = a + {name}",
    ...    "# a comment",
    ...    "aacute = a + acute"
    ...    ])
    >>> ParseGlyphConstructionListFromString(txt, font)
    [u'aacute = a + acute']
    """
    txt = None
    if isinstance(source, (str, unicode)):
        if os.path.exists(source):
            f = open(source)
            txt = f.read()
            f.close()
        else:
            txt = source
    elif hasattr(source, "read"):
        txt = source.read()
    else:
        raise GlyphBuilderError("Unreadable source: '%s'" % source)

    # parse all variable out of the text
    txt, variables = ParseVariables(txt)
    try:
        # try to format the text with all the variables
        txt = txt.format(**variables)
    except KeyError, err:
        raise GlyphBuilderError("Variable %s is missing" % err)
    # split all the lines, one line -> one construction
    lines = []
    for line in txt.split("\n"):
        # strip it
        line = line.strip()
        # do nothing if it is a comment
        if line:
            if line[0] == glyphCommentSuffixSplit:
                continue
            elif line[0] == glyphCheckIfExists:
                if font:
                    glyphName, _ = parseGlyphName(line[1:])
                    if glyphName in font:
                        continue
                line = line[1:]
        # do nothing with empty lines when there is no line added
        if not line and not lines:
            continue
        lines.append(line)
    # remove trailing empty lines
    while lines and not lines[-1]:
        lines.pop()
    return lines


# -----
# Tests
# -----

def testDummyGlyph(glyph, i):
    add = 20 * i
    pen = glyph.getPen()
    pen.moveTo((100, 100))
    pen.lineTo((200+add, 100+add))
    pen.lineTo((200+add, 200+add))
    pen.closePath()


def testDummyFont():
    from defcon import Font
    font = Font()
    for i, glyphName in enumerate(("a", "grave", "f", "i", "agrave")):
        font.newGlyph(glyphName)
        testDummyGlyph(font[glyphName], i)
        font[glyphName].width = 60 + 10*i
    return font


def testDigestGlyph(glyph):
    from robofab.pens.digestPen import DigestPointPen
    pen = DigestPointPen()
    glyph.draw(pen)
    return (
            glyph.name,
            glyph.width,
            glyph.unicode,
            glyph.mark,
            glyph.note,
            pen.getDigest()
        )


def testGlyphConstructionBuilder_GlyphAttributes():
    """
    >>> font = testDummyFont()

    >>> result = GlyphConstructionBuilder("agrave = a + grave", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 0, 0))))

    # unicode

    >>> result = GlyphConstructionBuilder("agrave = a + grave | 00E0", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, 224, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 0, 0))))

    # mark

    >>> result = GlyphConstructionBuilder("agrave = a + grave ! 1, 0, 0, 1", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, (1.0, 0.0, 0.0, 1.0), '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 0, 0))))

    # note

    >>> result = GlyphConstructionBuilder("agrave = a + grave # this is a note", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, None, 'this is a note', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 0, 0))))

    # width

    >>> result = GlyphConstructionBuilder("agrave = a + grave ^ 300", font)
    >>> testDigestGlyph(result)
    ('agrave', 300.0, None, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 0, 0))))

    # left and right margin

    >>> result = GlyphConstructionBuilder("agrave = a + grave ^ 300, 200", font)
    >>> testDigestGlyph(result)
    ('agrave', 620.0, None, None, '', (('a', (1, 0, 0, 1, 200, 0)), ('grave', (1, 0, 0, 1, 200, 0))))

    # all glyph attributes

    >>> result = GlyphConstructionBuilder("agrave = a + grave ^ 300, 200 ! 1, 0, 0, 1 | 00E0 # this is a note ", font)
    >>> testDigestGlyph(result)
    ('agrave', 620.0, 224, (1.0, 0.0, 0.0, 1.0), 'this is a note', (('a', (1, 0, 0, 1, 200, 0)), ('grave', (1, 0, 0, 1, 200, 0))))

    # all glyph attributes, different order

    >>> result = GlyphConstructionBuilder("agrave = a + grave | 00E0 ! 1, 0, 0, 1 ^ 300, 200 # this is a note ", font)
    >>> testDigestGlyph(result)
    ('agrave', 620.0, 224, (1.0, 0.0, 0.0, 1.0), 'this is a note', (('a', (1, 0, 0, 1, 200, 0)), ('grave', (1, 0, 0, 1, 200, 0))))
    """


def testGlyphConstructionBuilder_Marks():
    """
    >>> font = testDummyFont()

    >>> result = GlyphConstructionBuilder("agrave = a + grave", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 0, 0))))

    Multiple marks, same width, like staked accents

    >>> result = GlyphConstructionBuilder("agrave = a + grave + anotherGlyph", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 0, 0)), ('anotherGlyph', (1, 0, 0, 1, 0, 0))))

    Multiple marks, adjust width, like ligatures

    >>> result = GlyphConstructionBuilder("f_f_i = f & f & i", font)
    >>> testDigestGlyph(result)
    ('f_f_i', 250, None, None, '', (('f', (1, 0, 0, 1, 0, 0)), ('f', (1, 0, 0, 1, 80, 0)), ('i', (1, 0, 0, 1, 160, 0))))
    """


def testGlyphConstructionBuilder_Positioning():
    """
    >>> font = testDummyFont()

    # set mark at 0, 0

    >>> result = GlyphConstructionBuilder("agrave = a + grave @ 0, 0", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, -100, -100))))

    # postion mark at center, top

    >>> result = GlyphConstructionBuilder("agrave = a + grave @ center, top", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, -10, 100))))

    # postion mark at center of 'i', top

    >>> result = GlyphConstructionBuilder("agrave = a + grave @i: center, top", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 20, 100))))

    # postion mark at center of 'i', top of 'i'

    >>> result = GlyphConstructionBuilder("agrave = a + grave @i: center, i: top", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 20, 160))))

    # postion mark at 100%

    >>> result = GlyphConstructionBuilder("agrave = a + grave @100%", font)
    >>> testDigestGlyph(result)
    ('agrave', 60, None, None, '', (('a', (1, 0, 0, 1, 0, 0)), ('grave', (1, 0, 0, 1, 100, 100))))
    """


if __name__ == "__main__":
    import doctest
    doctest.testmod()
