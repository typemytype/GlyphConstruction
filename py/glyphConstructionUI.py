from AppKit import *
import weakref
from vanilla import *
from vanilla.dialogs import getFile
from defconAppKit.windows.baseWindow import BaseWindowController

from mojo.roboFont import version as RoboFontVersion
from mojo.events import addObserver, removeObserver
from mojo.drawingTools import *
from mojo.UI import MultiLineView
from mojo.glyphPreview import GlyphPreview

from mojo.extensions import getExtensionDefault, setExtensionDefault, getExtensionDefaultColor, setExtensionDefaultColor

from lib.UI.splitter import Splitter
from lib.UI.enterTextEditor import EnterTextEditor
from lib.tools.misc import NSColorToRgba
from lib.UI.statusBar import StatusBar

from glyphConstructionBuilder import GlyphConstructionBuilder, ParseGlyphConstructionListFromString, GlyphBuilderError
from glyphConstructionLexer import GlyphConstructionLexer

from lib.scripting.codeEditor import CodeEditor
import os

defaultKey = "com.typemytype.glyphBuilder"

constructions = """# capitals

Agrave = A + grave.cap@center,top
Aacute = A + acute.cap@center,top
Acircumflex = A + circumflex.cap@center,top
Atilde = A + tilde.cap@center,top
Adieresis = A + dieresis.cap@center,top
Aring = A + ring.cap@center,top

Ccedilla = C + cedilla.cap@center, bottom

Egrave = E + grave.cap@center, top
Eacute = E + acute.cap@center, top
Ecircumflex = E + circumflex.cap@center, top
Edieresis = E + dieresis.cap@center, top

Igrave = I + grave.cap@center, top
Iacute = I + acute.cap@center, top
Icircumflex = I + circumflex.cap@center, top
Idieresis = I + dieresis.cap@center, top

Ntilde = N + tilde@center,top

Ograve = O + grave.cap@center, top
Oacute = O + acute.cap@center, top
Ocircumflex = O + circumflex.cap@center, top
Otilde = O + tilde.cap@center, top
Odieresis = O + dieresis.cap@center, top
Oslash = O + slash@center,center

Scaron = S + caron.cap@center, top

Ugrave = U + grave.cap@center, top
Uacute = U + acute.cap@center, top
Ucircumflex = U + circumflex.cap@center, top
Udieresis = U + dieresis.cap@center, top

Zcaron = Z + caron.cap@center, top

# capitals ligatures

F_L = F & L
F_I = F & I

AE = A & E@75%,origin
OE = O & E@75%,origin

# lowercase

agrave = a + grave@center,top
aacute = a + acute@center,top
acircumflex = a + circumflex@center,top
atilde = a + tilde@center,top
adieresis = a + dieresis@center,top
aring = a + ring@center,top
amacron = a + macron@center,top
abreve = a + breve@center,top
aogonek = a + ogonek@innerRight,bottom
aringacute = a + ring@center,top + acute@center,110%

ccedilla =c + cedilla@center,bottom

egrave = e + grave@center,top
eacute = e + acute@center,top
ecircumflex = e + circumflex@center,top
edieresis = e + dieresis@center,top
emacron = e + macron@center,top
ebreve = e + breve@center,top
edotaccent = e + dotaccent@center,top
eogonek = e + ogonek@center,bottom
ecaron = e + caron@center,top

igrave = dotlessi + grave@center,top
iacute = dotlessi + acute@center,top
icircumflex = dotlessi + circumflex@center,top
idieresis = dotlessi + dieresis@center,top

ograve = o + grave@center,top
oacute = o + acute@center,top
otilde = o + tilde@center,top
odieresis = o + dieresis@center,top
ohungarumlaut = o + hungarumlaut@center,top
oslash = o + slash@center,center

scaron = s + caron@center,top

yacute = y + acute@center,top
ydieresis = y + dieresis@center,top

zcaron = z + caron@center,top

# lowercase ligatures

fi = f & i
fl = f & l
f_f_i = f & f & i
f_f_l = f & f & l

ae = a & e@80%,orgin
oe = o & e@80%,orgin

# fractions

onequarter = fraction@110%,origin + one.superior@innerLeft,innerTop + four.inferior@ fraction:innerRight,fraction:innerBottom
onehalf = fraction@110%,origin + one.superior@innerLeft,innerTop + two.inferior@ fraction:innerRight,fraction:innerBottom
threequarters = fraction@110%,origin + three.superior@innerLeft,innerTop + four.inferior@ fraction:innerRight,fraction:innerBottom
percent = fraction@110%,origin + zero.superior@innerLeft,innerTop + zero.inferior@ fraction:innerRight,fraction:innerBottom
perthousand = fraction@110%,origin + zero.superior@innerLeft,innerTop + zero.inferior@ fraction:innerRight,fraction:innerBottom & zero.inferior@fraction:right,fraction:innerBottom

## some test cases

L_aringacute=L & a+ring@center,top+acute@center,top
"""

constructions = ""

class GlyphConstructorFont(object):

    def __init__(self, font):
        self.font = font
        self.glyphsDone = {}

    def __getattr__(self, attr):
        return getattr(self.font, attr)

    def __getitem__(self, glyphName):
        if glyphName in self.glyphsDone:
            return self.glyphsDone[glyphName]
        return self.font[glyphName]

    def __contains__(self, glyphName):
        if glyphName in self.glyphsDone:
            return True
        return glyphName in self.font

    def __len__(self):
        return len(self.keys())

    def keys(self):
        return set(list(self.font.keys()) + list(self.glyphsDone.keys()))

    def __iter__(self):
        names = self.keys()
        while names:
            name = names[0]
            yield self[name]
            names = names[1:]

class AnalyserTextEditor(EnterTextEditor):

    def __init__(self, *args, **kwargs):
        super(AnalyserTextEditor, self).__init__(*args, **kwargs)
        self.getNSScrollView().setBorderType_(NSNoBorder)

        try:
            self.getNSTextView().setUsesFindBar_(True)
        except:
            self.getNSTextView().setUsesFindPanel_(True)

        #basicAttrs = getBasicTextAttributes()
        font = NSFont.fontWithName_size_("Menlo", 10)

        #self.getNSTextView().setTypingAttributes_(basicAttrs)
        self.getNSTextView().setFont_(font)

def _stringDict(d, verb):
    out = []
    for key in sorted(d.keys()):
        value = d[key]
        out.append("\tGlyph %s %s %s" %(key, verb, ", ".join(value)))
    return "\n".join(out)

def analyseConstructions(font, constructionGlyphs):
    missingGlyphs = []
    notMissingGlyphs = []
    missingComponents = {}
    unusedComponents = {}
    doubleEntries = []

    done = []

    for construction in constructionGlyphs:
        if construction.name is None:
            continue
        if construction.name not in font:
            missingGlyphs.append(construction.name)
            continue

        notMissingGlyphs.append(construction.name)

        if construction.name in done:
            doubleEntries.append(construction.name)

        done.append(construction.name)

        glyph = font[construction.name]

        glyphComponentNames = [component.baseGlyph for component in glyph.components]
        constructionComponentNames = [component.baseGlyph for component in construction.components]

        if glyphComponentNames == constructionComponentNames:
            # same values in the same order
            continue

        other = list(constructionComponentNames)
        for name in glyphComponentNames:
            if name in other:
                other.remove(name)
            else:
                if name not in unusedComponents:
                    unusedComponents[glyph.name] = []
                unusedComponents[glyph.name].append(name)

        other = list(glyphComponentNames)
        for name in constructionComponentNames:
            if name in other:
                other.remove(name)
            else:
                if name not in unusedComponents:
                    missingComponents[glyph.name] = []
                missingComponents[glyph.name].append(name)

    text = []

    if doubleEntries:
        text += [
                 "Double entries:",
                 "---------------",
                 "\t" + "\n\t".join(doubleEntries),
                 "\n"
                ]

    if missingGlyphs:
        text += [
                 "Missing Glyphs:",
                 "---------------",
                 "\t" + "\n\t".join(missingGlyphs),
                 "\n"
                ]
    if notMissingGlyphs:
        text += [
                 "Existing Glyphs:",
                 "---------------",
                 "\t" + "\n\t".join(notMissingGlyphs),
                 "\n"
                ]
    if missingComponents:
        text += [
                 "Existing Glyphs with Missing Components:",
                 "----------------------------------------",
                 _stringDict(missingComponents, "is missing"),
                 "\n"
                ]
    if unusedComponents:
        text += [
                 "Existing Glyphs with different components:",
                 "------------------------------------------",
                 _stringDict(unusedComponents, "has no"),
                 "\n"
                ]

    return "\n".join(text)


class BuildGlyphsSheet(BaseWindowController):

    overWriteKey = "%s.overWrite" % defaultKey
    useMarkColorKey = "%s.useMarkColor" % defaultKey
    markColorKey = "%s.markColor" % defaultKey

    def __init__(self, constructions, font, parentWindow):

        self.font = font
        self.constructions = constructions

        self.w = Sheet((300, 120), parentWindow=parentWindow)

        getExtensionDefault, setExtensionDefault, getExtensionDefaultColor, setExtensionDefaultColor
        y = 15
        self.w.overWrite = CheckBox((15, y, 200, 22), "Overwrite Existing Glyphs", value=getExtensionDefault(self.overWriteKey, True))

        y += 35
        self.w.markGlyphs = CheckBox((15, y, 200, 22), "Mark Glyphs", value=getExtensionDefault(self.overWriteKey, True), callback=self.markGlyphsCallback)
        self.w.markGlyphColor = ColorWell((130, y-5, 50, 30), color=getExtensionDefaultColor(self.markColorKey, NSColor.redColor()))

        self.w.markGlyphColor.enable(getExtensionDefault(self.overWriteKey, True))

        self.w.okButton = Button((-70, -30, -15, 20), "Build", callback=self.buildCallback, sizeStyle="small")
        self.w.setDefaultButton(self.w.okButton)

        self.w.closeButton = Button((-140, -30, -80, 20), "Cancel", callback=self.closeCallback, sizeStyle="small")
        self.w.closeButton.bind(".", ["command"])
        self.w.closeButton.bind(unichr(27), [])

        self.w.open()

    def markGlyphsCallback(self, sender):
        self.w.markGlyphColor.enable(sender.get())

    def buildCallback(self, sender):

        overWrite = self.w.overWrite.get()
        markColor = None
        if self.w.markGlyphs.get():
            markColor = NSColorToRgba(self.w.markGlyphColor.get())

        progress = self.startProgress("Building Glyphs...", len(self.constructions))

        font = self.font
        font.naked().holdNotifications()

        for construction in self.constructions:
            progress.update()

            if construction.name is None:
                continue

            if construction.name in font and not overWrite:
                continue

            glyph = self.font.newGlyph(construction.name)
            glyph.clear()

            glyph.width = construction.width
            glyph.unicode = construction.unicode
            glyph.note = construction.note

            construction.draw(glyph.getPen())

            if construction.mark:
                glyph.mark = construction.mark
            elif markColor:
                glyph.mark = markColor

        font.naked().releaseHeldNotifications()

        progress.close()

        self.closeCallback(sender)

    def closeCallback(self, sender):
        overWrite = self.w.overWrite.get()
        markColor = None
        if self.w.markGlyphs.get():
            markColor = self.w.markGlyphColor.get()

        setExtensionDefault(self.overWriteKey, overWrite)
        setExtensionDefault(self.useMarkColorKey, bool(markColor))
        if markColor is not None:
            setExtensionDefaultColor(self.markColorKey, markColor)

        self.w.close()

class GlyphBuilderController(BaseWindowController):

    fileNameKey = "%s.lastSavedFileName" % defaultKey

    def __init__(self, font):
        self.font = None
        self._glyphs = []

        statusBarHeight = 20

        self.w = Window((900, 700), "Glyph Builder", minSize=(400, 400))
        self.w.getNSWindow().setCollectionBehavior_(128) #NSWindowCollectionBehaviorFullScreenPrimary

        toolbarItems = [
                        dict(itemIdentifier="save",
                            label="Save",
                            imageNamed="toolbarScriptSave",
                            callback=self.saveFile,
                            ),
                        dict(itemIdentifier="open",
                            label="Open",
                            imageNamed="toolbarScriptOpen",
                            callback=self.openFile,
                            ),
                        dict(itemIdentifier=NSToolbarSpaceItemIdentifier),
                        dict(itemIdentifier="reload",
                            label="Update",
                            imageNamed="toolbarScriptReload",
                            callback=self.reload,
                            ),
                        dict(itemIdentifier=NSToolbarSpaceItemIdentifier),
                        dict(itemIdentifier="analyse",
                            label="Analyse",
                            imageNamed="prefToolbarSort",
                            callback=self.analyse,
                            ),
                        dict(itemIdentifier=NSToolbarFlexibleSpaceItemIdentifier),
                        dict(itemIdentifier="buildGlyphs",
                             label="Build Glyphs",
                             imageNamed="toolbarRun",
                             callback=self.generateGlyphs
                             ),
                        ]
        toolbar = self.w.addToolbar(toolbarIdentifier="GlyphBuilderControllerToolbar", toolbarItems=toolbarItems, addStandardItems=False)

        self.constructions = CodeEditor((0, 0, -0, -0),constructions, lexer=GlyphConstructionLexer())
        #self.constructions.wrapWord(False) # in only availbel in the RoboFont 1.7 beta

        self.constructions.getNSScrollView().setBorderType_(NSNoBorder)
        self.preview = MultiLineView((0, 0, -0, -0),
                                     pointSize=50,
                                     lineHeight=500,
                                     applyKerning=False,
                                     displayOptions={"Beam" : False,
                                                     "displayMode" : "Multi Line"},
                                     selectionCallback=self.previewSelectionCallback)


        self.analyser = AnalyserTextEditor((0, 0, -0, -0), readOnly=True)
        self.analyserPreview = Group((0, 0, -0, -0))


        self.analyserPreview.construction = GlyphPreview((0, 0, -0, -0), contourColor=NSColor.redColor(), componentColor=NSColor.redColor())
        self.analyserPreview.construction.getNSView()._buffer = 100
        self.analyserPreview.origin = GlyphPreview((0, 0, -0, -0),contourColor=NSColor.blackColor(), componentColor=NSColor.blackColor())
        self.analyserPreview.origin.getNSView()._buffer = 100

        self.analyserPreview.build = Button((10, -25, -10, 19), "Build", sizeStyle="small", callback=self.buildSingleGlyph)
        self.analyserPreview.build.enable(False)

        paneDescriptions = [
                    dict(view=self.analyser, identifier="analyserText", canCollapse=False, minSize=100),
                    dict(view=self.analyserPreview, identifier="analyserPreview", canCollapse=False, minSize=100),
                    ]

        self.analyserSplit = Splitter((0, 0, -0, -statusBarHeight), paneDescriptions=paneDescriptions, drawBorderLine=False, isVertical=False, dividerThickness=1)


        paneDescriptions = [
                    dict(view=self.constructions, identifier="constructions", canCollapse=False, minSize=200, maxSize=600, liveResizeable=False),
                    dict(view=self.preview, identifier="preview", canCollapse=False, minSize=300, liveResizeable=True),
                    dict(view=self.analyserSplit, identifier="analyser", canCollapse=True, minSize=100, maxSize=300, liveResizeable=False)
                    ]

        self.w.split = Splitter((0, 0, -0, -statusBarHeight), paneDescriptions=paneDescriptions, drawBorderLine=False, dividerThickness=1)
        #self.w.split.showPane("analyser", True)

        self.w.statusBar = StatusBar((0, -statusBarHeight, -0, statusBarHeight))
        self.w.statusBar.hiddenReload = Button((0, 0, -0, -0), "Reload", self.reload)
        button = self.w.statusBar.hiddenReload.getNSButton()
        button.setBezelStyle_(NSRoundRectBezelStyle)
        button.setAlphaValue_(0)
        self.w.statusBar.hiddenReload.bind("\r", ["command"])

        self.w.statusBar.hiddenSave = Button((0, 0, -0, -0), "Reload", self.saveFile)
        button = self.w.statusBar.hiddenSave.getNSButton()
        button.setBezelStyle_(NSRoundRectBezelStyle)
        button.setAlphaValue_(0)
        self.w.statusBar.hiddenSave.bind("s", ["command"])

        self.subscribeFont(font)
        self.setUpBaseWindowBehavior()

        addObserver(self, "fontBecameCurrent", "fontBecameCurrent")
        addObserver(self, "fontResignCurrent", "fontResignCurrent")
        self.w.open()

    def subscribeFont(self, font):
        self.unsubscribeFont()
        self.font = font
        if font is not None:
            self.preview.setFont(font)
            self.font.naked().addObserver(self, "fontChanged", "Font.Changed")
        self.constructionsCallback(self.constructions)

    def unsubscribeFont(self):
        if self.font is not None:
            self.preview.setFont(None)
            self.preview.set([])
            self.font.removeObserver(self, notification="Font.Changed")
            self.font = None

    def constructionsCallback(self, sender, update=True):
        if self.font is None:
            return

        font = self.font.naked()

        self.glyphConstructorFont = GlyphConstructorFont(font)

        self._glyphs = []
        errors = []

        try:
            constructions = ParseGlyphConstructionListFromString(sender.get(), font)
        except GlyphBuilderError, err:
            constructions = []
            errors.append(str(err))

        for construction in constructions:
            if not construction:
                glyph = self.preview.createNewLineGlyph()
            elif construction in self.glyphConstructorFont.glyphsDone:
                glyph = self.glyphConstructorFont.glyphsDone[construction]
            else:
                try:
                    constructionGlyph = GlyphConstructionBuilder(construction, self.glyphConstructorFont)
                except GlyphBuilderError, err:
                    errors.append(str(err))
                    continue

                if constructionGlyph.name is None:
                    errors.append(construction)
                    continue
                
                if RoboFontVersion < 2:
                    glyph = font._instantiateGlyphObject()
                else:
                    glyph = font.layers.defaultLayer.instantiateGlyphObject()
                glyph.name = constructionGlyph.name
                glyph.unicode = constructionGlyph.unicode
                glyph.note = constructionGlyph.note
                glyph.mark = constructionGlyph.mark
                if RoboFontVersion < 2:
                    glyph.setParent(self.glyphConstructorFont)
                    glyph.dispatcher = font.dispatcher
                else:
                    glyph._font = weakref.ref(self.glyphConstructorFont)
                    # glyph._dispatcher = font._dispatcher

                glyph.width = constructionGlyph.width
                constructionGlyph.draw(glyph.getPen())

                self.glyphConstructorFont.glyphsDone[glyph.name] = glyph

            self._glyphs.append(glyph)

        if errors:
            print "Errors:"
            print "\n".join(errors)

        if update:
            self.preview.set(self._glyphs)

        self.analyser.set(analyseConstructions(font, self._glyphs))

    ## preview

    def previewSelectionCallback(self, sender):

        def _niceNumber(value):
            i = int(value)
            if i == value:
                return "%i" % value
            else:
                return "%.2f" % value

        glyph = sender.getSelectedGlyph()

        if glyph is not None and glyph.name is None:
            glyph = None

        status = []


        if glyph is not None:
            width = _niceNumber(glyph.width)
            leftMargin = _niceNumber(glyph.leftMargin)
            rightMargin = _niceNumber(glyph.rightMargin)

            status = [
                 glyph.name,
                 "width: %s left: %s right: %s" % (width, leftMargin, rightMargin),
                 "components: %s" % (", ".join([component.baseGlyph for component in glyph.components]))
                 ]
            if glyph.unicode:
                status.append("unicode: %04X" % glyph.unicode)
            if glyph.note:
                status.append("note: %s" % (glyph.note[:30] + (glyph.note[30:] and unichr(0x2026))))
            if glyph.mark:
                status.append("mark: %s" % ", ".join([str(c) for c in glyph.mark]))

        self.w.statusBar.set(status)

        self.analyserPreview.construction.setGlyph(glyph)

        self.analyserPreview.build.enable(glyph is not None)

        if glyph is not None:
            self.analyserPreview.build.setTitle("Build %s" % glyph.name)
        else:
            self.analyserPreview.build.setTitle("Build")

        if glyph is not None and glyph.name in self.font:
            self.analyserPreview.origin.setGlyph(self.font[glyph.name])
        else:
            self.analyserPreview.origin.setGlyph(None)


    def buildSingleGlyph(self, sender):
        glyph = self.preview.getSelectedGlyph()
        if glyph is None:
            return
        if self.font is None:
            return

        dest = self.font.newGlyph(glyph.name)
        dest.clear()

        glyph.draw(dest.getPen())

        dest.unicode = glyph.unicode
        dest.note = glyph.note
        if glyph.mark:
            dest.mark = glyph.mark
        dest.width = glyph.width

    ## toolbar

    def generateGlyphs(self, sender):
        self.reload(update=False)

        if not self._glyphs:
            return

        if self.font is None:
            return

        BuildGlyphsSheet(self._glyphs, self.font, self.w)


    def reload(self, sender=None, update=True):
        self.constructionsCallback(self.constructions, update)

    def _saveFile(self, path):
        if self.font is not None:
            self.font.lib[self.fileNameKey] = os.path.splitext(os.path.basename(path))[0]
        txt = self.constructions.get()
        f = open(path, "w")
        f.write(txt)
        f.close()

    def saveFile(self, sender=None):
        preferredName = None
        if self.font is not None and self.font.path is not None:
            preferredName = os.path.splitext(os.path.basename(self.font.path))[0]
            if self.fileNameKey in self.font.lib.keys():
                # see if we have saved this file before and use that as first choice
                preferredName = self.font.lib.get(self.fileNameKey)
        self.showPutFile(["glyphConstruction"], fileName=preferredName, callback=self._saveFile)

    def _openFile(self, paths):
        if paths:
            path = paths[0]
            f = open(path, "r")
            txt = f.read()
            f.close()

            self.constructions.set(txt)

    def openFile(self, sender=None):
        directory = fileName = None
        if self.font is not None and self.font.path is not None:
            if self.fileNameKey in self.font.lib.keys():
                fileName = self.font.lib.get(self.fileNameKey, "")
                fileName += ".glyphConstruction"
                directory = os.path.dirname(self.font.path)
                fileName = os.path.join(directory, fileName)
                directory=None
        getFile(fileTypes=["glyphConstruction"], parentWindow=self.w.getNSWindow(), directory=directory, fileName=fileName, resultCallback=self._openFile)
        # self.showGetFile(["glyphConstruction"], callback=self._openFile)

    def analyse(self, sender=None):
        self.w.split.togglePane("analyser", False)
        self.reload()

    ## notifications

    def fontChanged(self, notification):
        self.reload()

    def fontBecameCurrent(self, notification):
        font = notification["font"]
        self.subscribeFont(font)

    def fontResignCurrent(self, notification):
        font = notification["font"]
        self.unsubscribeFont()

    def windowCloseCallback(self, sender):
        self.unsubscribeFont()
        removeObserver(self, "fontBecameCurrent")
        removeObserver(self, "fontResignCurrent")
        super(GlyphBuilderController, self).windowCloseCallback(sender)

GlyphBuilderController(CurrentFont())
