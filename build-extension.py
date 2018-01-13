'''build RoboFont Extension'''

import os
from mojo.extensions import ExtensionBundle

# ----------
# paths etc.
# ----------

basePath = os.path.dirname(__file__)
libPath = os.path.join(basePath, 'py')
htmlPath = os.path.join(basePath, 'html')
licensePath = os.path.join(basePath, 'LICENSE')
extensionPath = os.path.join(basePath, 'GlyphConstruction.roboFontExt')

# -------------------
# build documentation
# -------------------

import markdown
import codecs

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

md = codecs.open(mdPath, mode="r", encoding="utf-8").read()
html = htmlTemplate % markdown.markdown(md)
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
B.version = '0.1'
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
B.license = open(licensePath).read()
B.repositoryURL = 'http://github.com/typemytype/GlyphConstruction/'
B.summary = 'A simple, human-readable, powerful language for describing how shapes are constructed.'

# ---------------
# build extension
# ---------------

print 'building extension...',
B.save(extensionPath, libPath=libPath, htmlPath=htmlPath)
print 'done!'
print
print B.validationErrors()
