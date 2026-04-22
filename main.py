# run "python3 main.py examples/crypt.pico --debug" to debug

import argparse

from lexer import tokenize
from parser import Parser, print_ast
from semantic import SemanticAnalyzer, SemanticError


def run_parser(source_text: str, debug: bool = False):
    tokens = tokenize(source_text)
    parser = Parser(tokens)
    ast = parser.parse_program()
    semantic = SemanticAnalyzer()
    semantic.analyze(ast)

    if debug:
        print("TOKENS\n")
        for tok in tokens:
            print(tok)
        print("\n\nAST\n")
        print_ast(ast)
        print()
        print()
        semantic.dump_symbol_table()
    return ast


def main():
    cli = argparse.ArgumentParser(description="PicoScrypt compiler frontend")
    cli.add_argument("source_file", help="Path to .pico source file")
    cli.add_argument("--debug", action="store_true", help="Print token stream and AST")
    args = cli.parse_args()

    with open(args.source_file, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        run_parser(source, debug=args.debug)
    except SemanticError as err:
        print("Semantic analysis failed:")
        print(err)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
