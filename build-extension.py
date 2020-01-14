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
readmePath = os.path.join(basePath, 'README.md')
extensionPath = os.path.join(basePath, 'GlyphConstruction.roboFontExt')
modulePath = os.path.join(basePath, "Lib", "glyphConstruction.py")

# ----------------
# create extension
# ----------------

B = ExtensionBundle()
B.name = "Glyph Construction"
B.developer = 'Frederk Berlaen'
B.developerURL = 'http://typemytype.com/'
B.version = '0.6'
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

with open(licensePath, mode="r", encoding="utf-8") as f:
    B.license = f.read()
B.repositoryURL = 'http://github.com/typemytype/GlyphConstruction/'
B.summary = 'A simple, human-readable, powerful language for describing how shapes are constructed.'

# ---------------
# build extension
# ---------------

# copy README file into 'html' folder as 'index.md'
shutil.copyfile(readmePath, os.path.join(htmlPath, 'index.md'))

print('building extension...')
B.save(extensionPath, libPath=libPath, htmlPath=htmlPath)

print('copying module...')
destModulePath = os.path.join(B.libPath(), "glyphConstruction.py")
if os.path.exists(destModulePath):
    os.path.remove(destModulePath)
shutil.copy(modulePath, destModulePath)

print('...done!')
print()
print(B.validationErrors())
