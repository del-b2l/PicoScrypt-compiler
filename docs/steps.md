Phase 1 — Define the Language Grammar

Deliverable: A grammar file (.g or just a .txt), making sure it's LL(1)-compatible (no left recursion).

Keywords
world, room, item, npc, flag, inv, player, puzzle, gate, go, say, win, lose, take, drop, use, examine, talk, give, requires, has, unlock, on, enter, if, else, end

Directions
north, south, east, west

Literals
"An old iron key." (strings), true / false (booleans)

Identifiers
door_open, Crypt, entrance, chamber (names you make up)

Symbols
->, :, =

Comments
// anything → ignored entirely


Phase 2 — Lexer (Tokenizer)
Build the lexer first. It reads raw .pico source text and outputs a stream of tokens.

Tokens to define:

Keywords: world, room, item, npc, flag, inv, go, take, drop, use, examine, talk, give, say, win, lose, requires, has, if, else, end, on, enter, unlock, puzzle, gate, player
Identifiers (room names, item names, NPC names)
Literals: strings ("...") and booleans (true/false)
Directions: north, south, east, west
Symbols: ->, :, =
Comments: // to end of line (skip these)

Test it: Feed in the example .pico program and verify the token stream is correct. In --debug mode, print this stream.


Phase 3 — Parser (AST Builder)

Write a recursive-descent parser (or use PLY/lark) that consumes the token stream and builds an Abstract Syntax Tree (AST).

AST node types to design:

WorldNode (holds flags, player, rooms, items, puzzles)
RoomNode (holds items, exits, on-enter blocks)
ItemNode (examine/use actions)
NPCNode (dialogue trees with if/else branches)
PuzzleNode (requires clause + unlock action)
FlagNode, InvNode
ExitNode (direction + target room + optional requires)
DialogueNode (conditional branches)

Watch out for Challenge 1: Ensure your expression grammar is non-left-recursive for LL(1) parsing. Rewrite any rules like expr → expr + term into expr → term expr'.

In --debug mode, pretty-print the parse tree.


Phase 4 — Semantic Analyser (Symbol Table)

Walk the AST and enforce meaning/correctness rules.

Build a multi-level symbol table:

World scope: flags, globally declared items
Room scope: items placed in that room
NPC/puzzle scope: local conditions

Key checks to implement:

All referenced room names (in go north -> chamber) must exist in the world
All referenced flags in requires must be declared
All referenced inventory items must be declared
Flags must keep their declared type (no type changes)
Challenge 2 — Forward References: A room exit may point to a room declared later. Handle this with a two-pass strategy or a deferred resolution list: first pass registers all names, second pass resolves references.

In --debug mode, print the symbol table snapshot.


Phase 5 — IR Generation (Three-Address Code / TAC)

Lower the AST into Three-Address Code, a flat, linear intermediate representation using labels and jumps.

Key constructs to lower:

if flag door_open goto L1; else goto L2 for puzzle gates
on enter blocks become label room_chamber_enter: followed by conditional jumps
win "..." becomes a PRINT + HALT instruction
Inventory checks (inv has key) become a comparison + conditional jump

Example TAC for the puzzle gate:
t1 = inv_has(key)
if t1 goto UNLOCK_door_open
goto END_puzzle
UNLOCK_door_open: door_open = true
END_puzzle:

Challenge 3 is doing this cleanly without hardcoding game logic into the IR generator.

In --debug mode, print the full TAC listing.


Phase 6 — Interpreter / Execution Engine

Since PicoScrypt targets direct terminal execution (not compiled machine code), you need a tree-walking interpreter or a TAC interpreter.

The interpreter must:

Maintain runtime state: current room, inventory contents, flag values
Accept player input (action verbs: go north, take gem, examine key, etc.)
Print room descriptions when entering a room
Evaluate requires clauses before allowing movement
Trigger on enter blocks on room transitions
Display NPC dialogue and branch based on flag state
Print win/lose screens on win/lose

CLI interface:

picoscrypt game.pico          # run the game
picoscrypt game.pico --debug  # print tokens, AST, symbol table, TAC, then run


Phase 7 — Testing

Write tests for each phase separately:

Lexer tests: Verify token streams for valid and invalid input
Parser tests: Check AST structure for all major constructs
Semantic tests: Confirm errors are caught (undefined room, type mismatch, etc.)
Integration tests: Run complete .pico programs and verify game output
Test the example program from your proposal end-to-end


Folder Structure

picoscrypt/
├── lexer.py
├── parser.py
├── ast_nodes.py
├── semantic.py
├── codegen.py          # TAC generation
├── interpreter.py      # Runtime / execution engine
├── main.py             # Entry point + argparse CLI
├── tests/
│   ├── test_lexer.py
│   ├── test_parser.py
│   └── test_semantic.py
└── examples/
    └── crypt.pico      # Your example program
    

> Recommended Order of Work

Grammar design + keyword list
Lexer → test with crypt.pico
Parser → build AST → verify with --debug
Symbol table + semantic analysis (handle forward refs last)
TAC generation for puzzle gates and on-enter blocks
Interpreter / runtime loop
End-to-end testing + polish CLI output


Challenges & Strategies

LL(1) grammar (no left recursion)
Rewrite rules using expr' tail patterns; use a grammar validator

Forward references in symbol table
Two-pass: collect all names first, resolve on second pass

Lowering puzzle/on-enter to TAC
Design an IR with explicit labels; treat every conditional block as a guarded jump
