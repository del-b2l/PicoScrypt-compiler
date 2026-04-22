from ast_nodes import (
    ConditionFlag,
    ConditionInv,
    LoseStmt,
    OnEnterBlock,
    PuzzleNode,
    RoomNode,
    SayStmt,
    WinStmt,
    WorldNode,
)

""" 
    
required constructs:
    - puzzle gate condition -> conditional jumps
    - inv has key -> temp comparison (t1 = inv_has(key))
    - on enter block -> room_<name>_enter: label
    - win/lose -> PRINT + HALT

"""

class TACGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0

    def generate(self, ast: WorldNode):
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0

        # lower global control-flow blocks (room enter hooks + puzzles) into TAC
        for node in ast.body:
            if isinstance(node, RoomNode):
                self._emit_room_on_enter(node)
            elif isinstance(node, PuzzleNode):
                self._emit_puzzle(node)

        return self.instructions

    def dump_tac(self):
        print("TAC\n")
        for idx, instr in enumerate(self.instructions):
            print(f"{idx:03}: {instr}")

    def _new_temp(self):
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def _new_label(self, prefix: str):
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def _emit(self, text: str):
        self.instructions.append(text)

    def _emit_label(self, label: str):
        self._emit(f"{label}:")

    def _emit_condition_eval(self, condition):
        if isinstance(condition, ConditionInv):
            tmp = self._new_temp()
            self._emit(f"{tmp} = inv_has({condition.item_name})")
            return tmp
        if isinstance(condition, ConditionFlag):
            tmp = self._new_temp()
            self._emit(f"{tmp} = flag({condition.flag_name})")
            return tmp
        raise ValueError(f"Unsupported condition node: {type(condition).__name__}")

    def _emit_statements(self, statements):
        for stmt in statements:
            if isinstance(stmt, SayStmt):
                self._emit(f'PRINT "{stmt.text}"')
            elif isinstance(stmt, WinStmt):
                self._emit(f'PRINT "{stmt.text}"')
                self._emit("HALT")
            elif isinstance(stmt, LoseStmt):
                self._emit(f'PRINT "{stmt.text}"')
                self._emit("HALT")

    def _emit_room_on_enter(self, room_node: RoomNode):
        for part in room_node.body:
            if isinstance(part, OnEnterBlock):
                enter_label = f"room_{room_node.name}_enter"
                self._emit_label(enter_label)
                self._emit_statements(part.statements)
                self._emit(f"goto END_{enter_label}")
                self._emit_label(f"END_{enter_label}")

    def _emit_puzzle(self, puzzle_node: PuzzleNode):
        unlock_label = f"UNLOCK_{puzzle_node.unlock_flag}"
        end_label = self._new_label("END_puzzle")

        cond_temp = self._emit_condition_eval(puzzle_node.condition)
        self._emit(f"if {cond_temp} goto {unlock_label}")
        self._emit(f"goto {end_label}")
        self._emit_label(unlock_label)
        self._emit(f"{puzzle_node.unlock_flag} = true")
        self._emit_label(end_label)
