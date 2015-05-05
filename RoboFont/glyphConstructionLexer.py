from pygments.lexer import RegexLexer, include, bygroups
from pygments import token

from lib.scripting.codeEditor import CodeEditor, languagesIDEBehavior

glyphConstructionAlignmentWords = ["top", "bottom", "center", "left", "right", "innerRight", "innerLeft", "innerTop", "innerBottom", "origin", "descender",  "xHeight", "capHeight", "ascender"]
glyphConstructionOperations = [
    "=", "+", "|", "@", ":", ",", "&", "!", "^", "`",
    "-", "+", "/", "*" # math stuff"
    ]

languagesIDEBehavior["GlyphConstruction"] = {
            "openToCloseMap" : {},
            "indentWithEndOfLine" : [],
            "comment" : "#",
            "keywords" : glyphConstructionAlignmentWords + glyphConstructionOperations,
            #"dropPathFormatting" : None
        }
        
class GlyphConstructionLexer(RegexLexer):
    
    name = "GlyphConstruction"
    aliases = ['GlyphConstruction', 'gc']
    filenames = ['*.glyphConstruction', "*.gc"]
    
    tokens = {
            'root' : [
                    (r'\n', token.Text),
                    (r'#.*$', token.Comment),
                    (r'(\|)[\s|\\\s]*([a-fA-F0-9]{4,})', bygroups(token.Operator, token.Number.Hex)),
                    (r'%s' % ("\\"+"|\\".join(glyphConstructionOperations)), token.Operator),
                    (r'([a-zA-Z_\{][a-zA-Z0-9_.\{\}]*)((\s|\\\s)*=)',  bygroups(token.Keyword, token.Operator)),
                    (r'(%s)' % ("|".join(glyphConstructionAlignmentWords)), token.Name.Tag),
                    (r'\.([a-zA-Z_][a-zA-Z0-9_]*)?', token.String.Other),
                    (r'(\$\s*[a-zA-Z_][a-zA-Z0-9_]*)\s*\=\s*(.*)', bygroups(token.Name.Function, token.String)),
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
#r"\%(?P<name>[a-zA-Z_][a-zA-Z0-9]*)\s+\=\s+(?P<value>.*)")

if __name__ == "__main__":
    
    from vanilla import Window
    
    t = """Aacute = A + acute.cap@center,top|00C1
Abreve = A + breve.cap@center,top|0102"""
    
    class Test:
        
        def __init__(self):
            self.w = Window((400, 400))
            self.w.e = CodeEditor((0, 0, -0, -0), t, lexer=GlyphConstructionLexer())
            self.w.open()
        
    Test()