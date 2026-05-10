"""

============================
PicoScrypt frontend
                   ᥥ ᥥ 
                 ( ･ ༝ ･) 🥕
============================

usage
-----
  python3 main.py <source.pico>                   # run the game
  python3 main.py <source.pico> --tokens          # print token stream
  python3 main.py <source.pico> --ast             # print AST
  python3 main.py <source.pico> --symbols         # print symbol table
  python3 main.py <source.pico> --tac             # print raw TAC
  python3 main.py <source.pico> --optimize        # print optimization report
  python3 main.py <source.pico> --debug           # all of the above, then run

* [NOTE]: flags can be combined, e.g.  --ast --symbols  or  --tokens --tac

"""

import argparse

from lexer import tokenize
from parser import Parser, print_ast
from semantic import SemanticAnalyzer, SemanticError
from codegen import TACGenerator
from optimizer import TACOptimizer
from interpreter import GameRuntime
from ast_nodes import FlagNode, PlayerNode


def build_pipeline(source_text: str):
    """
        run lexer → parser → semantic → codegen → optimizer
        returns: (tokens, ast, tac_gen, optimizer, raw_instructions, optimized_instructions)
    """
    tokens = tokenize(source_text)
    ast = Parser(tokens).parse_program()
    semantic = SemanticAnalyzer()
    semantic.analyze(ast)

    tac_gen = TACGenerator()
    raw_instructions = tac_gen.generate(ast)

    flag_values: dict = {}
    player_inv: set = set()
    for node in ast.body:
        if isinstance(node, FlagNode):
            flag_values[node.name] = node.value
        elif isinstance(node, PlayerNode):
            for inv in node.inventory:
                player_inv.add(inv.item_name)

    opt = TACOptimizer(flag_values, player_inv)
    optimized = opt.optimize(raw_instructions)

    # storing clean (no annotation comments) optimized TAC on the generator
    tac_gen.instructions = [l for l in optimized if not l.strip().startswith("//")]

    return tokens, ast, semantic, tac_gen, opt, raw_instructions, optimized


# required arg: source file
# optional flags: --tokens, --ast, --symbols, --tac, --optimize, --debug

def main():
    cli = argparse.ArgumentParser(
        description="PicoScrypt compiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    cli.add_argument("source_file", help="Path to .pico source file")
    cli.add_argument("--tokens",   action="store_true", help="Print token stream")
    cli.add_argument("--ast",      action="store_true", help="Print AST")
    cli.add_argument("--symbols",  action="store_true", help="Print symbol table")
    cli.add_argument("--tac",      action="store_true", help="Print raw TAC (before optimization)")
    cli.add_argument("--optimize", action="store_true", help="Print optimization report")
    cli.add_argument("--debug",    action="store_true",
                     help="Print everything (tokens + AST + symbols + TAC + optimization report), then run the game")
    args = cli.parse_args()

    with open(args.source_file, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tokens, ast, semantic, tac_gen, opt, raw, optimized = build_pipeline(source)
    except SemanticError as err:
        print("Semantic analysis failed:")
        print(err)
        raise SystemExit(1)

    show_all = args.debug

    if show_all or args.tokens:
        print("TOKENS\n")
        for tok in tokens:
            print(tok)
        print()

    if show_all or args.ast:
        print("AST\n")
        print_ast(ast)
        print()

    if show_all or args.symbols:
        semantic.dump_symbol_table()
        print()

    if show_all or args.tac:
        print("RAW TAC\n")
        for idx, instr in enumerate(raw):
            print(f"{idx:03}: {instr}")
        print()

    if show_all or args.optimize:
        opt.dump_comparison(raw, optimized)

    # run the game (unless we were only asked for analysis output)
    analysis_only = any([args.tokens, args.ast, args.symbols, args.tac, args.optimize])
    if show_all or not analysis_only:
        runtime = GameRuntime(ast)
        runtime.run()


if __name__ == "__main__":
    main()