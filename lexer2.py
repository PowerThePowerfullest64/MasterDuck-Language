import re
from dataclasses import dataclass

TOKEN_RE = re.compile(r'''
    (?P<STRING>"(?:\\.|[^"\\])*")
  | (?P<COMMENT>//.*)
  | (?P<NUMBER>\d+(?:\.\d+)?)
  | (?P<NAME>[A-Za-z_]\w*)
  | (?P<ARROW>->)
  | (?P<OP>==|!=|<=|>=|>>|<<|[+\-*/%<>=])
  | (?P<PUNCT>[(){}\[\],:.])
  | (?P<SKIP>[ ]+)
''', re.VERBOSE)

CONTROL_KEYS = {"if", "while"}
KEYWORDS = {"return", "in", "and", "or", "not", "if", "while"}

WORD_MAP = {
    "and": "&&",
    "or": "||",
    "not": "!",
    "True": "true",
    "False": "false"
}

TYPE_MAP = {
    "int": "int",
    "float": "float",
    "bool": "bool",
    "char": "char",
    "str": "std::string",
    "list": "std::vector",
    "array": "std::array",
    "dict": "std::unordered_map",
}
GENERIC = {"list", "array", "dict"}

METHOD_MAP = {
    "push": "push_back",
    "append": "push_back",
    "push_back": "push_back",

    "length": "size",
    "size": "size"
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

def matching_paren(tokens: list[Token], open_idx: int) -> int:
    depth = 0
    for k in range(open_idx, len(tokens)):
        if tokens[k].value == "(":
            depth += 1
        elif tokens[k].value == ")":
            depth -= 1
            if depth == 0:
                return k
    raise SyntaxError(f"[line {tokens[open_idx].line}] Unclosed '('.")

def tokenize_line(text: str, line_no: int) -> list[Token]:
    tokens, pos = [], 0
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m:
            raise SyntaxError(f"line {line_no}: unexpected {text[pos]!r}")
        if m.lastgroup not in ("SKIP", "COMMENT"):
            tokens.append(Token(m.lastgroup, m.group(), line_no))
        pos = m.end()
    return tokens

def tokenize_lines(lines: list[str]) -> list[Line]:
    res = []

    for i, text in enumerate(lines):
        if not text.strip(): continue # skip blank lines

        tokens = tokenize_line(text, i+1)
        if not tokens: continue # blank line or comment-only line

        spaces = len(text) - len(text.lstrip(" "))
        res.append(Line(spaces // 4, tokens))

    return res

def split_args(tokens: list[Token]) -> list[list[Token]]:
    args, current, depth = [], [], 0
    for t in tokens:
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
    return args
    
def parse_type(tokens: list[Token], start: int, line_no: int) -> tuple[str, int]:
    if start >= len(tokens) or not is_type(tokens[start].value):
        raise SyntaxError(f"[Line {line_no}] Expected a type.")

    name = tokens[start].value
    base = type_translate(name)
    nxt = start + 1

    if nxt < len(tokens) and tokens[nxt].value == "[":
        depth = 0
        for end in range(nxt, len(tokens)):
            if tokens[end].value == "[":
                depth += 1
            elif tokens[end].value == "]":
                depth -= 1
                if depth == 0:
                    break
        else:
            raise SyntaxError(f"[Line {line_no}] Unclosed '[' in type.")

        parts = []
        for arg in split_args(tokens[nxt + 1:end]):
            if len(arg) == 1 and arg[0].kind == "NUMBER":
                parts.append(arg[0].value)
            else:
                inner, used = parse_type(arg, 0, line_no)
                if used != len(arg):
                    raise SyntaxError(f"[Line {line_no}] Bad type argument.")
                parts.append(inner)
        return f"{base}<{', '.join(parts)}>", end + 1

    if name in GENERIC:
        raise SyntaxError(f"[Line {line_no}] '{name}' needs type arguments such as {name}[int]")
    return base, nxt

def is_type(value: str) -> bool:
    return value in TYPE_MAP

def is_declaration(tokens: list[Token]) -> bool:
    return (
        len(tokens) >= 3
        and tokens[0].kind == "NAME"
        and tokens[1].value == ":"
        and is_type(tokens[2].value)
    )

def translate_token(token: Token) -> str:
    if token.kind == "NAME":
        return WORD_MAP.get(token.value, token.value)
    return token.value

def type_translate(name: str):
    return TYPE_MAP.get(name, name)

def param_translate(tokens: list[Token], line_no: int) -> str:
    if len(tokens) < 3 or tokens[1].value != ":":
        raise SyntaxError(f"[line {line_no}] Parameters must be 'name: type' fr.")
    type_text, end = parse_type(tokens, 2, line_no)
    text = f"{type_text} {tokens[0].value}"
    if end < len(tokens):
        text += " " + expr(tokens[end:])
    return text

def func_translate(tokens: list[Token]) -> str:
    line_no = tokens[0].line
    arrow = next((k for k, t in enumerate(tokens) if t.kind == "ARROW"), None)

    if arrow is None or arrow + 1 >= len(tokens):
        raise TypeError(f"[line {tokens[0].line}] Function '{tokens[1].value}' could not find return type.")
    if tokens[2].value != "(" or tokens[arrow - 1].value != ")":
        raise SyntaxError(f"[line {line_no}] Expected parameters in parentheses.")

    name = tokens[1].value
    params = ", ".join(
        param_translate(p, line_no) for p in split_args(tokens[3:arrow - 1])
    )
    return_type, end = parse_type(tokens, arrow + 1, line_no)
    if end != len(tokens):
        raise SyntaxError(f"[Line {line_no}] Unexpected tokens after return type bruhhh.")
    return f"{return_type} {name}({params})"

OPENERS = {"(", "[", "{"}
CLOSERS = {")", "]", "}"}

def print_translate(tokens: list[Token]) -> str:
    args = split_args(tokens[2:-1]) # drop print and ()

    parts = [expr(arg) for arg in args]
    body = ' << " " << '.join(parts)
    return f'std::cout << {body} << "\\n"' if parts else 'std::cout << "\\n"'

def expr(tokens: list[Token]) -> str:
    out, stack, prev = [], [], None
    k = 0
    while k < len(tokens):
        t = tokens[k]
        nxt = tokens[k + 1] if k + 1 < len(tokens) else None

        # len(x) -> static_cast<int>((x).size())
        if t.kind == "NAME" and t.value == "len" and nxt and nxt.value == "(":
            end = matching_paren(tokens, k + 1)
            inner = expr(tokens[k + 2:end])
            out.append(f"static_cast<int>(({inner}).size())")
            prev = tokens[end]
            k = end + 1
            continue

        if t.kind == "PUNCT" and t.value == "[":
            is_index = prev is not None and (
                (prev.kind in ("NAME", "STRING") and prev.value not in KEYWORDS)
                or prev.value in (")", "]")
            )
            stack.append(is_index)
            out.append("[" if is_index else "{")
        elif t.kind == "PUNCT" and t.value == "]":
            out.append("]" if (stack.pop() if stack else True) else "}")
        elif t.kind == "NAME" and prev is not None and prev.value == "." and nxt and nxt.value == "(":
            out.append(METHOD_MAP.get(t.value, t.value))
        else:
            out.append(translate_token(t))

        prev = t
        k += 1
    return " ".join(out)

def for_translate(tokens: list[Token]) -> str:
    var = tokens[1].value
    iterable = tokens[3:]

    is_range = (
        len(iterable) >= 3
        and iterable[0].value == "range"
        and iterable[1].value == "("
        and iterable[-1].value == ")"
    )
    if is_range:
        args = [expr(a) for a in split_args(iterable[2:-1])]
        if len(args) == 1:
            start, stop, step = "0", args[0], "1"
        elif len(args) == 2:
            start, stop, step = args[0], args[1], "1"
        elif len(args) == 3:
            start, stop, step = args
        else:
            raise SyntaxError(f"[Line {tokens[0].line}] range() takes 1 to 3 arguments.")

        compare = ">" if step.startswith("-") else "<"
        iteration = f"{var} += {step}"
        clean = step.replace(" ", "")
        if step == '1':
            iteration = f"{var}++"
        elif step == '-1':
            iteration = f"{var}--"

        return f"for (int {var} = {start}; {var} {compare} {stop}; {iteration})"

    return f"for (auto {var} : {expr(iterable)})"

def parse_tokens(token_lines: list[Line]) -> str:
    output = ""
    level = 0
    for line in token_lines:
        # dedent to the right level
        while level > line.indent:
            level -= 1
            output += "\t" * level + "}\n"

        tokens = line.tokens

        if len(tokens) == 1 and tokens[0].value == "pass":
            output += "\t" * line.indent + "// pass\n"
            continue

        opens_block = tokens[-1].value == ":"
        if opens_block:
            tokens = tokens[:-1]  # remove colon

        if is_declaration(tokens):
            type_text, end = parse_type(tokens, 2, tokens[0].line)
            text = f"{type_text} {tokens[0].value}"
            if end < len(tokens):
                text += " " + expr(tokens[end:])
        elif tokens[0].value == "func":
            text = func_translate(tokens)
        elif tokens[0].value in CONTROL_KEYS:
            text = f"{tokens[0].value} ({expr(tokens[1:])})"
        elif tokens[0].value == "elif":
            text = f"else if ({expr(tokens[1:])})"
        elif tokens[0].value == "print":
            text = print_translate(tokens)
        elif tokens[0].value == "for":
            text = for_translate(tokens)
        else:
            text = expr(tokens)

        if opens_block:
            text += " {"
            level += 1
        else:
            text += ";"

        output += "\t" * line.indent + text + "\n"

    # close whatever is still open
    while level > 0:
        level -= 1
        output += "\t" * level + "}\n"

    return output

def add_includes(output: str):
    includes = []
    if "std::cout" in output:
        includes.append("#include <iostream>")
    if "std::vector" in output:
        includes.append("#include <vector>")
    if "std::array" in output:
        includes.append("#include <array>")
    if "std::string" in output:
        includes.append("#include <string>")
    if "std::unordered_map" in output:
        includes.append("#include <unordered_map>")

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
    file.write(output)

