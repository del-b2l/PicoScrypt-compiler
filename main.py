# run "python3 main.py examples/crypt.pico --debug" to debug

import argparse

from lexer import tokenize
from parser import Parser, print_ast
from semantic import SemanticAnalyzer, SemanticError
from codegen import TACGenerator
from optimizer import TACOptimizer
from interpreter import GameRuntime
from ast_nodes import FlagNode, PlayerNode


def run_parser(source_text: str, debug: bool = False):
    tokens = tokenize(source_text)
    parser = Parser(tokens)
    ast = parser.parse_program()
    semantic = SemanticAnalyzer()
    semantic.analyze(ast)
    tac_gen = TACGenerator()
    raw_instructions = tac_gen.generate(ast)

    # extracting compile-time flag values and inventory directly from the AST
    flag_values: dict = {}
    player_inv: set = set()
    for node in ast.body:
        if isinstance(node, FlagNode):
            flag_values[node.name] = node.value   # True / False (python bool, not random var)
        elif isinstance(node, PlayerNode):
            for inv in node.inventory:
                player_inv.add(inv.item_name)

    opt = TACOptimizer(flag_values, player_inv)
    optimized_instructions = opt.optimize(raw_instructions)

    if debug:
        print("TOKENS\n")
        for tok in tokens:
            print(tok)
        print("\n\nAST\n")
        print_ast(ast)
        print()
        print()
        semantic.dump_symbol_table()
        print()
        print()
        opt.dump_comparison(raw_instructions, optimized_instructions)

    # storing cleaned optimized TAC on the generator (strips annotation comments)
    tac_gen.instructions = [
        l for l in optimized_instructions if not l.strip().startswith("//")
    ]
    return ast


def main():
    cli = argparse.ArgumentParser(description="PicoScrypt compiler frontend")
    cli.add_argument("source_file", help="Path to .pico source file")
    cli.add_argument("--debug", action="store_true",
                     help="Print tokens, AST, symbol table, and optimization report")
    args = cli.parse_args()

    with open(args.source_file, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        ast = run_parser(source, debug=args.debug)
    except SemanticError as err:
        print("Semantic analysis failed:")
        print(err)
        raise SystemExit(1)

    runtime = GameRuntime(ast)
    runtime.run()


if __name__ == "__main__":
    main()