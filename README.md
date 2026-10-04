# MasterDuck-Language

A programming language that works as a mix between Python and C++.

## Running the prototype

Run `python lexer.py` from any directory. The script reads `input.madc` and
writes `output.cpp` beside `lexer.py`.

The current translator supports top-level `#include` directives, typed
`func` declarations, `if` blocks, `return`, `print(...)`, and indentation with
four spaces per level. `print(...)` is emitted as `std:cout`.

This is still a small language prototype, not a complete parser. Unsupported
syntax such as classes, and imports should not be expected to translate
correctly yet.
