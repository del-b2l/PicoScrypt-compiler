import re

# token def
KEYWORDS = {
    'world', 'room', 'item', 'flag', 'player', 'inv',
    'go', 'say', 'win', 'lose', 'requires', 'has',
    'unlock', 'puzzle', 'gate', 'on', 'enter',
    'examine', 'use', 'talk', 'give', 'take', 'drop',
    'if', 'else', 'end', 'npc',
    'north', 'south', 'east', 'west',
    'true', 'false'
}

# tuple format: (token_type, regex_pattern)
# order dependent -> first match wins!
TOKEN_PATTERNS = [
    ('COMMENT',  r'//[^\n]*'),                  # // comments - skipped
    ('STRING',   r'"[^"]*"'),                   # "any text"
    ('ARROW',    r'->'),                        # ->
    ('COLON',    r':'),                         # :
    ('EQUALS',   r'='),                         # =
    ('NEWLINE',  r'\n'),                        # these will be skipped too
    ('SKIP',     r'[ \t]+'),                    # spaces and tabs - skipped
    ('WORD',     r'[a-zA-Z_][a-zA-Z0-9_]*'),    # keywords and IDENTs
]

# combining all patterns into one big regex
MASTER_RE = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_PATTERNS)
)

class Token:
    def __init__(self, type_, value, line):
        self.type  = type_
        self.value = value
        self.line  = line # for error messages later

    def __repr__(self):
        return f'Token({self.type}, {self.value!r}, line = {self.line})'

# lexer func
def tokenize(source: str) -> list[Token]:
    tokens = []
    line_num = 1

    for match in MASTER_RE.finditer(source):
        kind  = match.lastgroup
        value = match.group()

        # tracking line numbers
        if kind == 'NEWLINE':
            line_num += 1
            continue # no token emission

        # skipping comments, spaces, tabs
        if kind in ('COMMENT', 'SKIP'):
            continue

        # distinguishing keywords from identifiers
        if kind == 'WORD':
            if value in KEYWORDS:
                kind = value.upper() # e.g. 'world' -> 'WORLD'
            else:
                kind = 'IDENT'

        # stripping quotes from strings for literals
        if kind == 'STRING':
            value = value[1:-1] # "hello" -> hello

        tokens.append(Token(kind, value, line_num))

    tokens.append(Token('EOF', None, line_num)) # always ending with EOF
    return tokens

# test!
if __name__ == '__main__':
    source = open('examples/crypt.pico').read()
    for tok in tokenize(source):
        print(tok)