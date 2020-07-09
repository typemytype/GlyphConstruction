import vanilla
import AppKit


class GlyphConstructionNSWindow(AppKit.NSWindow):

    def setSave_saveAsCallback_(self, saveCallback, saveAsCallback):
        self.__saveDocumentCallback = saveCallback
        self.__saveAsDocumentCallback = saveAsCallback

    def saveDocument_(self, sender):
        self.__saveDocumentCallback()

    def saveDocumentAs_(self, sender):
        self.__saveAsDocumentCallback()


class GlyphConstructionWindow(vanilla.Window):

    nsWindowClass = GlyphConstructionNSWindow
