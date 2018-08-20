'''
build RoboFont Extension
Run inside RoboFont
'''

import os
import shutil
from mojo.extensions import ExtensionBundle

# ----------
# paths etc.
# ----------

basePath = os.path.dirname(__file__)
libPath = os.path.join(basePath, 'LibExtension')
htmlPath = os.path.join(basePath, 'html')
licensePath = os.path.join(basePath, 'LICENSE')
extensionPath = os.path.join(basePath, 'GlyphConstruction.roboFontExt')
modulePath = os.path.join(basePath, "Lib", "glyphConstruction.py")

# -------------------
# build documentation
# -------------------

import codecs
import markdown
from markdown.extensions.toc import TocExtension
from markdown.extensions.fenced_code import FencedCodeExtension

mdPath = os.path.join(basePath, 'README.md')
htmlIndexPath = os.path.join(htmlPath, 'index.html')

htmlTemplate = '''\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Glyph Construction</title>
<link rel="stylesheet" href="GitHub-ReadMe.css">
</head>
<body>
%s
</body>
</html>
'''

with codecs.open(mdPath, mode="r", encoding="utf-8") as f:
    mdSrc = f.read()
M = markdown.Markdown(extensions=[TocExtension(permalink=True), FencedCodeExtension()])
html = htmlTemplate % M.convert(mdSrc)

htmlFile = codecs.open(htmlIndexPath, mode="w", encoding="utf-8")
htmlFile.write(html)
htmlFile.close()

# ----------------
# create extension
# ----------------

B = ExtensionBundle()
B.name = "Glyph Construction"
B.developer = 'Frederk Berlaen'
B.developerURL = 'http://typemytype.com/'
B.version = '0.2'
B.launchAtStartUp = 0
B.mainScript = ''
B.html = True
B.requiresVersionMajor = '1'
B.requiresVersionMinor = '5'
B.addToMenu = [
    {
        'path'         : 'glyphConstructionUI.py',
        'preferredName': 'Glyph Builder',
        'shortKey'     : '',
    },
]

with codecs.open(licensePath, mode="r", encoding="utf-8") as f:
    B.license = f.read()
B.repositoryURL = 'http://github.com/typemytype/GlyphConstruction/'
B.summary = 'A simple, human-readable, powerful language for describing how shapes are constructed.'

# ---------------
# build extension
# ---------------

print('building extension...', end=" ")
B.save(extensionPath, libPath=libPath, htmlPath=htmlPath)

print('copy module...', end=" ")
destModulePath = os.path.join(B.libPath(), "glyphConstruction.py")
if os.path.exists(destModulePath):
    os.path.remove(destModulePath)
shutil.copy(modulePath, destModulePath)

print('done!')
print()
print(B.validationErrors())
