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

    def _clean_name(self, raw: str):
        return "".join(ch if ch.isalnum() else "_" for ch in raw).upper()

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
                return True
            elif isinstance(stmt, LoseStmt):
                self._emit(f'PRINT "{stmt.text}"')
                self._emit("HALT")
                return True
        return False

    def _emit_room_on_enter(self, room_node: RoomNode):
        for part in room_node.body:
            if isinstance(part, OnEnterBlock):
                room_name = self._clean_name(room_node.name)
                enter_label = f"ROOM_{room_name}_ENTER"
                end_label = f"ROOM_{room_name}_END"
                self._emit_label(enter_label)
                terminated = self._emit_statements(part.statements)
                if not terminated:
                    self._emit(f"goto {end_label}")
                self._emit_label(end_label)

    def _emit_puzzle(self, puzzle_node: PuzzleNode):
        flag_name = self._clean_name(puzzle_node.unlock_flag)
        suffix = self._new_label("PZ").split("_")[-1]
        unlock_label = f"PUZZLE_{flag_name}_UNLOCK_{suffix}"
        end_label = f"PUZZLE_{flag_name}_END_{suffix}"

        cond_temp = self._emit_condition_eval(puzzle_node.condition)
        self._emit(f"if {cond_temp} goto {unlock_label}")
        self._emit(f"goto {end_label}")
        self._emit_label(unlock_label)
        self._emit(f"{puzzle_node.unlock_flag} = true")
        self._emit_label(end_label)
