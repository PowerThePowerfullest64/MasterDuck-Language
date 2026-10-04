import re
from dataclasses import dataclass

TOKEN_RE = re.compile(r'''
    (?P<STRING>"(?:\\.|[^"\\])*")
  | (?P<NUMBER>\d+(?:\.\d+)?)
  | (?P<NAME>[A-Za-z_]\w*)
  | (?P<ARROW>->)
  | (?P<OP>==|!=|<=|>=|[+\-*/%<>=])
  | (?P<PUNCT>[(){}\[\],:.])
  | (?P<SKIP>[ ]+)
''', re.VERBOSE)

CONTROL_KEYS = {"if", "while"}

WORD_MAP = {
    "and": "&&",
    "or": "||",
    "not": "!",
    "True": "true",
    "False": "false"
}

@dataclass
class Token:
    kind: str
    value: str
    line: int

@dataclass
class Line:
    indent: int
    tokens: list[Token]

def tokenize_line(text: str, line_no: int) -> list[Token]:
    tokens, pos = [], 0
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m:
            raise SyntaxError(f"line {line_no}: unexpected {text[pos]!r}")
        if m.lastgroup != "SKIP":
            tokens.append(Token(m.lastgroup, m.group(), line_no))
        pos = m.end()
    return tokens

def tokenize_lines(lines: list[list[Token]]) -> list[Line]:
    res = []

    for i, text in enumerate(lines):
        if not text.strip(): continue # skip blank lines

        spaces = len(text) - len(text.lstrip(" "))
        res.append(Line(spaces // 4, tokenize_line(text, i+1)))

    return res
    
def is_type(value: str) -> bool:
    if value == "int":
        return True
    if value == "str":
        return True
    if value == "char":
        return True
    if value == "list":
        return True
    if value == "array":
        return True
    if value == "bool":
        return True
    return False

def is_declaration(tokens: list[Token]) -> bool:
    return (
        len(tokens) >= 3
        and tokens[0].kind == "NAME"
        and tokens[1].value == ":"
        and tokens[2].kind == "NAME"
        and is_type(tokens[2].value)
    )

def translate_token(token: Token) -> str:
    if token.kind == "NAME":
        return WORD_MAP.get(token.value, token.value)
    return token.value

def type_translate(name: str):
    if name == "str":
        return "std::string"

    return name

def func_translate(tokens: list[Token]) -> str:
    arrow = next((k for k, t in enumerate(tokens) if t.kind == "ARROW"), None)
    if arrow is None or arrow + 1 >= len(tokens) or not is_type(tokens[arrow + 1].value):
        raise TypeError(f"[line {tokens[0].line}] Function '{tokens[1].value}' could not find return type.")

    return_type = type_translate(tokens[arrow + 1].value)
    signature = "".join(t.value for t in tokens[1:arrow])
    return f"{return_type} {signature}"

OPENERS = {"(", "[", "{"}
CLOSERS = {")", "]", "}"}

def print_translate(tokens: list[Token]) -> str:
    inner = tokens[2:-1] # remove print and opening and closing parenthesis
    args, current, depth = [], [], 0
    for t in inner:
        if t.kind == "PUNCT" and t.value in OPENERS:
            depth += 1
        elif t.kind == "PUNCT" and t.value in CLOSERS:
            depth -= 1
        if t.kind == "PUNCT" and t.value == "," and depth == 0:
            args.append(current)
            current = []
        else:
            current.append(t)
    if current:
        args.append(current)

    parts = [" ".join(translate_token(t) for t in arg) for arg in args]
    body = ' << " " << '.join(parts)
    return f'std::cout << {body} << "\\n"' if parts else 'std::cout << "\\n"'

def parse_tokens(token_lines: list[Line]) -> str:
    output = ""
    level = 0
    for i, line in enumerate(token_lines):
        # dendent to right level
        while (level > line.indent):
            level -= 1
            output += "\t" * level + "}\n"

        tokens = line.tokens

        if len(tokens) == 1 and tokens[0].value == "pass":
            output += "\t" * line.indent + "// pass\n"
            continue

        opens_block = tokens[-1].value == ":"
        if opens_block:
            tokens = tokens[:-1] # remove colon

        if is_declaration(tokens):
            text = f"{type_translate(tokens[2].value)} {tokens[0].value}"
            text += "".join(f" {t.value}" for t in tokens[3:])
        elif tokens[0].value == "func":
            text = func_translate(tokens)
        elif tokens[0].value in CONTROL_KEYS:
            condition = " ".join(translate_token(t) for t in tokens[1:])
            text = f"{tokens[0].value} ({condition})"
        elif tokens[0].value == "print":
            text = print_translate(tokens)
        else:
            text = " ".join(t.value for t in tokens)

        if opens_block:
            text += "{"
            level += 1
        else:
            text += ";"

        # indent visually and add text!
        output += "\t" * line.indent + text + "\n"

    # close whatever indent is still open
    output += "}\n" * level
    
    return output

def add_includes(output: str):
    includes = []
    if "std::cout" in output:
        includes.append("#include <iostream>")
    if "std::vector" in output:
        includes.append("#include <vector>")
    if "std::array" in output:
        includes.append("#include <array>")

    if includes:
        return "\n".join(includes) + "\n\n" + output
    return output

with open("input.madc", 'r') as file:
    contents = file.read()
    lines = contents.splitlines()
    token_lines = tokenize_lines(lines)

output = parse_tokens(token_lines)
output = add_includes(output)

with open("output.cpp", 'w') as file:
    file.flush()
    file.write(output)

