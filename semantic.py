from ast_nodes import (
    ConditionFlag,
    ConditionInv,
    DialogueBranch,
    DialogueNode,
    ExitNode,
    FlagNode,
    ItemNode,
    ItemRef,
    NPCNode,
    PlayerNode,
    PuzzleNode,
    RoomNode,
    WorldNode,
)


class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    def __init__(self):
        self.symbols = {
            "world": {
                "flags": {},                # flag_name -> "bool"
                "items": set(),        # globally declared item names
                "rooms": set(),        # declared room names
                "player_inv": set(),   # items listed in player block
            },
            "rooms": {},              # room_name -> {"items": set()}
            "locals": {               # local condition usage by construct
                "puzzles": [],
                "npcs": {},
            },
        }
        self.errors = []

    def analyze(self, ast: WorldNode):
        if not isinstance(ast, WorldNode):
            raise SemanticError("Semantic analysis expects a WorldNode as the AST root.")

        self._first_pass(ast)
        self._second_pass(ast)

        if self.errors:
            raise SemanticError("\n".join(self.errors))
        return self.symbols

    # debug printer
    def dump_symbol_table(self):
        world = self.symbols["world"]
        print("SYMBOL TABLE")
        print("world.flags:")
        for flag_name in sorted(world["flags"]):
            print(f"  - {flag_name}: bool")

        print("world.items:")
        for item_name in sorted(world["items"]):
            print(f"  - {item_name}")

        print("world.rooms:")
        for room_name in sorted(world["rooms"]):
            print(f"  - {room_name}")

        print("world.player_inv:")
        for item_name in sorted(world["player_inv"]):
            print(f"  - {item_name}")

        print("room scopes:")
        for room_name in sorted(self.symbols["rooms"]):
            room_scope = self.symbols["rooms"][room_name]
            items = sorted(room_scope["items"])
            print(f"  - {room_name}: items={items}")

        print("local condition scopes:")
        print("  puzzles:")
        for idx, cond in enumerate(self.symbols["locals"]["puzzles"], start=1):
            print(f"    {idx}. {cond}")
        print("  npcs:")
        for npc_name in sorted(self.symbols["locals"]["npcs"]):
            conds = self.symbols["locals"]["npcs"][npc_name]
            print(f"    - {npc_name}: {conds}")

    # collect world symbols (flags, items, rooms, player inventory)
    def _first_pass(self, ast: WorldNode):
        for node in ast.body:
            if isinstance(node, FlagNode):
                self._declare_flag(node.name)
            elif isinstance(node, ItemNode):
                self._declare_item(node.name)
            elif isinstance(node, RoomNode):
                self._declare_room(node.name)
            elif isinstance(node, PlayerNode):
                self._declare_player_inventory(node)

    # resolve / check references (exists, requires, puzzle unlock, room item refs, NPC dialogue conditions)
    def _second_pass(self, ast: WorldNode):
        for node in ast.body:
            if isinstance(node, RoomNode):
                self._check_room(node)
            elif isinstance(node, PuzzleNode):
                self._check_puzzle(node)
            elif isinstance(node, NPCNode):
                self._check_npc(node)
            elif isinstance(node, PlayerNode):
                self._check_player_inventory(node)

    def _declare_flag(self, flag_name: str):
        flags = self.symbols["world"]["flags"]
        if flag_name in flags:
            self.errors.append(f"Duplicate flag declaration: '{flag_name}'.")
            return
        flags[flag_name] = "bool"

    def _declare_item(self, item_name: str):
        items = self.symbols["world"]["items"]
        if item_name in items:
            self.errors.append(f"Duplicate item declaration: '{item_name}'.")
            return
        items.add(item_name)

    def _declare_room(self, room_name: str):
        rooms = self.symbols["world"]["rooms"]
        if room_name in rooms:
            self.errors.append(f"Duplicate room declaration: '{room_name}'.")
            return
        rooms.add(room_name)
        self.symbols["rooms"][room_name] = {"items": set()}

    def _declare_player_inventory(self, player_node: PlayerNode):
        inv_set = self.symbols["world"]["player_inv"]
        for inv_decl in player_node.inventory:
            inv_set.add(inv_decl.item_name)

    def _check_player_inventory(self, player_node: PlayerNode):
        declared_items = self.symbols["world"]["items"]
        for inv_decl in player_node.inventory:
            if inv_decl.item_name not in declared_items:
                self.errors.append(
                    f"Player inventory references undeclared item '{inv_decl.item_name}'."
                )

    def _check_room(self, room_node: RoomNode):
        room_scope = self.symbols["rooms"][room_node.name]
        for child in room_node.body:
            if isinstance(child, ItemRef):
                room_scope["items"].add(child.item_name)
                if child.item_name not in self.symbols["world"]["items"]:
                    self.errors.append(
                        f"Room '{room_node.name}' references undeclared item '{child.item_name}'."
                    )
            elif isinstance(child, ExitNode):
                self._check_exit(room_node.name, child)

    def _check_exit(self, source_room: str, exit_node: ExitNode):
        if exit_node.target not in self.symbols["world"]["rooms"]:
            self.errors.append(
                f"Room '{source_room}' has exit to undeclared room '{exit_node.target}'."
            )
        if exit_node.condition is not None:
            self._check_condition(exit_node.condition, f"room '{source_room}' exit")

    def _check_puzzle(self, puzzle_node: PuzzleNode):
        self._check_condition(puzzle_node.condition, "puzzle gate")
        self.symbols["locals"]["puzzles"].append(self._condition_to_string(puzzle_node.condition))

        if puzzle_node.unlock_flag not in self.symbols["world"]["flags"]:
            self.errors.append(
                f"Puzzle unlock references undeclared flag '{puzzle_node.unlock_flag}'."
            )
        else:
            # Flag declarations are boolean-only in this language phase.
            if self.symbols["world"]["flags"][puzzle_node.unlock_flag] != "bool":
                self.errors.append(
                    f"Flag '{puzzle_node.unlock_flag}' has invalid type; expected bool."
                )

    def _check_npc(self, npc_node: NPCNode):
        npc_conds = []
        for dialogue in npc_node.dialogues:
            if isinstance(dialogue, DialogueNode):
                for branch in dialogue.branches:
                    if isinstance(branch, DialogueBranch) and branch.condition is not None:
                        self._check_condition(branch.condition, f"npc '{npc_node.name}' dialogue")
                        npc_conds.append(self._condition_to_string(branch.condition))
        self.symbols["locals"]["npcs"][npc_node.name] = npc_conds

    def _check_condition(self, condition_node, context: str):
        if isinstance(condition_node, ConditionFlag):
            if condition_node.flag_name not in self.symbols["world"]["flags"]:
                self.errors.append(
                    f"Condition in {context} references undeclared flag '{condition_node.flag_name}'."
                )
        elif isinstance(condition_node, ConditionInv):
            item_name = condition_node.item_name
            if item_name not in self.symbols["world"]["items"]:
                self.errors.append(
                    f"Condition in {context} references undeclared inventory item '{item_name}'."
                )
        else:
            self.errors.append(f"Unknown condition node type in {context}: {type(condition_node).__name__}.")

    def _condition_to_string(self, condition_node):
        if isinstance(condition_node, ConditionFlag):
            return f"flag {condition_node.flag_name}"
        if isinstance(condition_node, ConditionInv):
            return f"inv has {condition_node.item_name}"
        return "<unknown condition>"
