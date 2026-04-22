from ast_nodes import (
    ConditionFlag,
    ConditionInv,
    DialogueNode,
    ExitNode,
    ItemNode,
    ItemRef,
    LoseStmt,
    NPCNode,
    OnEnterBlock,
    PuzzleNode,
    RoomNode,
    SayStmt,
    WinStmt,
    WorldNode,
)


class GameRuntime:
    def __init__(self, ast: WorldNode):
        self.ast = ast
        self.rooms = {}
        self.items = {}
        self.npcs = {}
        self.puzzles = []
        self.flags = {}
        self.inventory = set()
        self.room_items = {}
        self.current_room = None
        self.game_over = False
        self._triggered_puzzles = set()
        self._build_state()

    def _build_state(self):
        room_order = []
        for node in self.ast.body:
            if node.__class__.__name__ == "FlagNode":
                self.flags[node.name] = bool(node.value)
            elif node.__class__.__name__ == "PlayerNode":
                for inv in node.inventory:
                    self.inventory.add(inv.item_name)
            elif isinstance(node, ItemNode):
                self.items[node.name] = node
            elif isinstance(node, RoomNode):
                self.rooms[node.name] = node
                room_order.append(node.name)
            elif isinstance(node, NPCNode):
                self.npcs[node.name] = node
            elif isinstance(node, PuzzleNode):
                self.puzzles.append(node)

        for room_name, room in self.rooms.items():
            placed = set()
            for part in room.body:
                if isinstance(part, ItemRef):
                    placed.add(part.item_name)
            self.room_items[room_name] = placed

        if not room_order:
            raise RuntimeError("No rooms declared.")
        self.current_room = room_order[0]

    def run(self):
        self._enter_room(self.current_room, initial=True)
        while not self.game_over:
            raw = input("\n> ").strip()
            if not raw:
                continue
            if raw.lower() in {"quit", "exit"}:
                print("Goodbye.")
                break
            self._handle_command(raw)

    def _handle_command(self, raw: str):
        parts = raw.split()
        verb = parts[0].lower()
        args = [p.lower() for p in parts[1:]]

        if verb == "help":
            print("Commands: go <dir>, take <item>, drop <item>, use <item>, examine <item>, talk <npc>, give, inv, look, quit")
        elif verb == "look":
            self._describe_room()
        elif verb == "inv":
            print("Inventory:", ", ".join(sorted(self.inventory)) if self.inventory else "(empty)")
        elif verb == "go" and len(args) == 1:
            self._go(args[0])
        elif verb == "take" and len(args) == 1:
            self._take(args[0])
        elif verb == "drop" and len(args) == 1:
            self._drop(args[0])
        elif verb == "use" and len(args) == 1:
            self._use(args[0])
        elif verb == "examine" and len(args) == 1:
            self._examine(args[0])
        elif verb == "talk" and len(args) == 1:
            self._talk(args[0])
        elif verb == "give":
            print("Give command is recognized but not yet modeled in this phase.")
        else:
            print("Unknown command. Type 'help' for available commands.")

    def _current_room_node(self):
        return self.rooms[self.current_room]

    def _room_exits(self, room_node):
        return [part for part in room_node.body if isinstance(part, ExitNode)]

    def _describe_room(self):
        room = self._current_room_node()
        exits = [e.direction for e in self._room_exits(room)]
        print(f"You are in {self.current_room}.")
        if self.room_items[self.current_room]:
            print("\nYou see:", ", ".join(sorted(self.room_items[self.current_room])))
        else:
            print("You see: nothing useful.")
        if exits:
            print("Exits:", ", ".join(sorted(exits)))

    def _go(self, direction: str):
        room = self._current_room_node()
        for ex in self._room_exits(room):
            if ex.direction == direction:
                if ex.condition and not self._eval_condition(ex.condition):
                    print("You can't go that way yet.")
                    return
                self.current_room = ex.target
                self._enter_room(self.current_room)
                return
        print("No exit in that direction.")

    def _take(self, item: str):
        if item not in self.room_items[self.current_room]:
            print("That item is not here.")
            return
        self.room_items[self.current_room].remove(item)
        self.inventory.add(item)
        print(f"You take {item}.")

    def _drop(self, item: str):
        if item not in self.inventory:
            print("You don't have that item.")
            return
        self.inventory.remove(item)
        self.room_items[self.current_room].add(item)
        print(f"You drop {item}.")

    def _use(self, item: str):
        if item not in self.inventory:
            print("You need to carry that item first.")
            return
        node = self.items.get(item)
        if not node:
            print("Nothing happens.")
            unlocked = self._apply_puzzles()
            for flag_name in unlocked:
                print(f"You hear a mechanism unlock ({flag_name}).")
            return
        executed_use_action = False
        for action in node.actions:
            if action.__class__.__name__ == "UseAction":
                self._exec_statements(action.statements)
                executed_use_action = True
        if not executed_use_action:
            print("Nothing happens.")
        unlocked = self._apply_puzzles()
        for flag_name in unlocked:
            print(f"You hear a mechanism unlock ({flag_name}).")

    def _examine(self, item: str):
        if item not in self.inventory and item not in self.room_items[self.current_room]:
            print("You don't see that here.")
            return
        node = self.items.get(item)
        if not node:
            print("Nothing special.")
            return
        for action in node.actions:
            if action.__class__.__name__ == "ExamineAction":
                print(action.text)
                return
        print("Nothing special.")

    def _talk(self, npc_name: str):
        npc = self.npcs.get(npc_name)
        if not npc:
            print("No such NPC.")
            return
        for dialogue in npc.dialogues:
            if isinstance(dialogue, DialogueNode):
                for branch in dialogue.branches:
                    if branch.condition is None:
                        self._exec_statements(branch.if_statements)
                    elif self._eval_condition(branch.condition):
                        self._exec_statements(branch.if_statements)
                    else:
                        self._exec_statements(branch.else_statements)

    def _enter_room(self, room_name: str, initial: bool = False):
        if not initial:
            print(f"You enter {room_name}.")
        self._describe_room()
        room = self._current_room_node()
        for part in room.body:
            if isinstance(part, OnEnterBlock):
                self._exec_statements(part.statements)

    def _eval_condition(self, condition):
        if isinstance(condition, ConditionFlag):
            return bool(self.flags.get(condition.flag_name, False))
        if isinstance(condition, ConditionInv):
            return condition.item_name in self.inventory
        return False

    def _apply_puzzles(self):
        unlocked_flags = []
        for idx, puzzle in enumerate(self.puzzles):
            if idx in self._triggered_puzzles:
                continue
            if self._eval_condition(puzzle.condition):
                self.flags[puzzle.unlock_flag] = True
                self._triggered_puzzles.add(idx)
                unlocked_flags.append(puzzle.unlock_flag)
        return unlocked_flags

    def _exec_statements(self, statements):
        for stmt in statements:
            if isinstance(stmt, SayStmt):
                print(stmt.text)
            elif isinstance(stmt, WinStmt):
                print(stmt.text)
                self.game_over = True
                return
            elif isinstance(stmt, LoseStmt):
                print(stmt.text)
                self.game_over = True
                return
