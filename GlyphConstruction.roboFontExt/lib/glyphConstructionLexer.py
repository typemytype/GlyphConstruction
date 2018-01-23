from pygments.lexer import RegexLexer, include, bygroups
from pygments import token

from lib.scripting.codeEditor import CodeEditor, languagesIDEBehavior
import glyphConstruction as gc

glyphConstructionAlignmentWords = list(gc.legalFontInfoAttributes | gc.legalGlyphMetricHorizontalPositions | gc.legalGlyphMetricVerticalPositions | gc.legalBoundsPositions | gc.legalCalculatablePositions)

glyphConstructionOperations = [
    gc.glyphNameSplit,
    gc.unicodeSplit,
    gc.baseGlyphSplit,
    gc.markGlyphSplit,
    gc.positionSplit,
    gc.positionXYSplit,
    gc.positionBaseSplit,
    gc.glyphSuffixSplit,
    gc.metricsSuffixSplit,
    gc.glyphCommentSuffixSplit,
    gc.glyphMarkSuffixSplit,
    gc.flipMarkGlyphSplit,

    # gc.variableDeclarationStart,
    # gc.variableDeclarationEnd,

    gc.explicitMathStart,
    gc.explicitMathEnd,

    "-", "+", "/", "*"  # math stuff"
]

languagesIDEBehavior["GlyphConstruction"] = {
    "openToCloseMap": {},
    "indentWithEndOfLine": [],
    "comment": "#",
    "keywords": glyphConstructionAlignmentWords + glyphConstructionOperations,
    # "dropPathFormatting" : None
}


class GlyphConstructionLexer(RegexLexer):

    name = "GlyphConstruction"
    aliases = ['GlyphConstruction', 'gc']
    filenames = ['*.glyphConstruction', "*.gc"]

    tokens = {
            'root': [
                    (r'\n', token.Text),
                    (r'#.*$', token.Comment),
                    (r'\.([a-zA-Z_][a-zA-Z0-9_]*)?', token.String.Other),

                    (r'(\|)[\s|\\\s]*([a-fA-F0-9]{4,})', bygroups(token.Operator, token.Number.Hex)),
                    (r'%s' % ("\\"+"|\\".join(glyphConstructionOperations)), token.Operator),
                    (r'(\?)?([a-zA-Z_\{][a-zA-Z0-9_.\{\}]*)((\s|\\\s)*=)',  bygroups(token.Name.Builtin, token.Keyword, token.Operator)),
                    (r'(%s)' % ("|".join(glyphConstructionAlignmentWords)), token.Name.Tag),

                    (r'(\%s)(\s*[a-zA-Z_][a-zA-Z0-9_]*)\s*(\=)\s*(.*)(%s)' % (gc.variableDeclarationStart, gc.variableDeclarationEnd), bygroups(token.Name.Builtin, token.Name.Variable, token.Operator, token.String, token.Name.Builtin)),
                    (r'\{[a-zA-Z_][a-zA-Z0-9_]*\}', token.Name.Function),
                    include('numbers'),
                    include('whitespace'),
                    (r'[a-zA-Z][a-zA-Z0-9]*', token.Name),
                ],
            'numbers': [
                    (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?j?\%?', token.Number.Float),
                    (r'\d+[eE][+-]?[0-9]+j?\%?', token.Number.Float),
                    (r'\d+j?\%?', token.Number.Integer),
                ],
            'string': [
                    (r'(?s)(\\\\|\\[0-7]+|\\.|[^"\'\\])', token.String),
                    (r'"|\'', token.String, '#pop')
                ],
            'whitespace': [
                    (r'\s+', token.Text),
                ],
        }


if __name__ == "__main__":

    from vanilla import Window

    t = """
$name = test

Aacute = A + acute.cap@center,top|00C1 # {name}
?Abreve = A + breve.cap@center,top|0102

$variableName = n
Laringacute = L & a + ring@~center,~`top+10` + acute@center,top ^ 100, `l*2` | 159AFFF ! 1, 0, 0, 1 # this is an example, and this is a variable {variableName}

"""

    class Test:

        def __init__(self):
            self.w = Window((400, 400), minSize=(300, 300))
            self.w.e = CodeEditor((0, 0, -0, -0), t, lexer=GlyphConstructionLexer())
            self.w.open()

    Test()
