from typing import Optional

file_in = "input.madc"
file_out = "output.cpp"

with open(file_in, "r", encoding="utf-8") as file:
    contents = file.read()
del file


def look_ahead(conts: Optional[str]) -> tuple[str, int]:
    if conts is None or conts == "":
        return "", 0

    if conts.startswith("    "):
        return "\t", 3

    if conts[0] in " \n\t":
        return "", 0

    if conts[0] == ':':
        return ":", 0
    if conts[0] == '"':
        return '"', 0

    current_word = ""
    for i, char in enumerate(conts):
        if char == "\n":
            if current_word:
                return current_word, i - 1
            return "", 0
        if char == " ":
            if current_word:
                return current_word, i - 1
            return "", 0
        if char == ":":
            if current_word:
                return current_word, i - 1
            return ":", 0
        if char == '"':
            if current_word:
                return current_word, i - 1
            return '"', 0
        current_word += char

    return current_word, len(conts) - 1


def get_lines(conts: str):
    lines = []
    while conts:
        if "\n" in conts:
            line_text, conts = conts.split("\n", 1)
        else:
            line_text, conts = conts, ""

        line = []
        temp = line_text
        while temp:
            res = look_ahead(temp)
            if res[0] == "":
                temp = temp[1:]
                continue
            temp = temp[res[1] + 1:]
            line.append(res[0])

        if line:
            lines.append(line)

    return lines


lines = get_lines(contents)
print(f"Input is...\n{lines}")

current_indent = 0


def count_tabs(line) -> int:
    return sum(1 for word in line if word == "\t")


def type_translate(word: str) -> str:
    values = {
        "int": "int",
        "float": "float",
        "str": "std::string",
        "bool": "bool",
        "list": "std::vector",
        "dict": "std::unordered_map",
        "array": "std::array",
    }
    return values.get(word, word)


def is_type(word: str) -> bool:
    return word in ["int", "float", "str", "bool", "list", "dict", "array"]


def translate(word: str) -> str:
    if is_type(word):
        return type_translate(word)
    if word == "if":
        return "if("
    if word == "for":
        return "for("
    if word == "and":
        return "&&"
    if word == "or":
        return "||"
    if word == "not":
        return "!"
    if word == '"':
        return '"'
    if word == "print(":
        return "std::print("
    if word == "->":
        return ""
    if word == ":":
        return ""
    return word


output = []
current_indent = 0

for line in lines:
    indent = count_tabs(line)
    if current_indent > indent:
        output.append("}\n" * (current_indent - indent))
    current_indent = indent

    tokens = [token for token in line if token != "\t"]
    if not tokens:
        continue

    if tokens[0] == "#include":
        output.append("#include <print>\n")
        continue

    if tokens[0] == "func":
        func_name = tokens[1]
        return_type = ""
        for token in tokens[2:]:
            if token == "->":
                continue
            if token == ":":
                break
            if is_type(token):
                return_type = type_translate(token)
        output.append(f"{return_type} {func_name} {{\n")
        continue

    if tokens[0] == "if":
        expr_tokens = []
        for token in tokens[1:]:
            if token == ":":
                break
            expr_tokens.append(translate(token))
        output.append(f"if({''.join(expr_tokens)}) {{\n")
        continue

    if tokens[0] == "return":
        expr_tokens = []
        for token in tokens[1:]:
            if token == ":":
                break
            expr_tokens.append(translate(token))
        output.append(f"return {''.join(expr_tokens)};\n")
        continue

    if tokens[0] == "print(":
        expr_tokens = []
        for token in tokens[1:]:
            if token == ")":
                break
            expr_tokens.append(translate(token))
        output.append(f"std::print({''.join(expr_tokens)});\n")
        continue

    output.append("".join(translate(token) for token in tokens) + ";\n")

output.append("}\n" * current_indent)

print(f"Output is...\n{output}")

with open(file_out, 'w', encoding="utf-8") as file:
    file.write("".join(output))
