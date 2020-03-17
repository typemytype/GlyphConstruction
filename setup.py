import re
from setuptools import setup

_versionRE = re.compile(r'__version__\s*=\s*\"([^\"]+)\"')
# read the version number for the settings file
with open('lib/glyphConstruction.py', "r") as settings:
    code = settings.read()
    found = _versionRE.search(code)
    assert found is not None, "glyphConstruction __version__ not found"
    __version__ = found.group(1)

setup(
    name='glyphConstruction',
    version=__version__,
    author='Frederik Berlaen',
    author_email='frederik@typemytpye.com',
    url='https://github.com/typemytype/GlyphConstruction',
    license='LICENSE.txt',
    description='Letter shape description language',
    long_description='Letter shape description language',
    install_requires=[],
    py_modules=["glyphConstruction"],
    package_dir={'': 'Lib'}
)
