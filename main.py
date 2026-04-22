# run "python3 main.py examples/crypt.pico --debug" in terminal

import argparse

from lexer import tokenize
from parser import Parser, print_ast


def run_parser(source_text: str, debug: bool = False):
    tokens = tokenize(source_text)
    parser = Parser(tokens)
    ast = parser.parse_program()

    if debug:
        print("=== TOKENS ===")
        for tok in tokens:
            print(tok)
        print("\n=== AST ===")
        print_ast(ast)

    return ast


def main():
    cli = argparse.ArgumentParser(description="PicoScrypt compiler frontend")
    cli.add_argument("source_file", help="Path to .pico source file")
    cli.add_argument("--debug", action="store_true", help="Print token stream and AST")
    args = cli.parse_args()

    with open(args.source_file, "r", encoding="utf-8") as f:
        source = f.read()

    run_parser(source, debug=args.debug)


if __name__ == "__main__":
    main()
