"""

==================================
  (งツ)ว PicoScrypt TAC Optimizer
==================================

implements [[[ 3 optimization passes ]]] over the TAC instruction list
produced by codegen.TACGenerator:

  pass 1 — constant folding
      evaluates flag/inv conditions whose values are known at compile
      time (from flag declarations and player inventory).

      statically true/false conditions --> replaced with a CONST assignment,
      conditional jump --> rewritten to an unconditional GOTO 
        OR: dropped when the branch is never taken!!

  pass 2 — dead code elimination
      after constant folding, some branches may become unreachable.
      
      any instruction that [follows] an unconditional HALT or GOTO, and
      that is [not a jump target], is removed!
      ++ removes instructions that assign to temp vars that are never 
      read afterwards.

  pass 3 — peephole optimization
      local pattern matching over a [[[sliding window]]]:
        • GOTO L immediately followed by label L  -->  [drop] the goto
        • PRINT msg; HALT; PRINT msg  -->  [collapse] duplicate PRINT+HALT
        • consecutive identical PRINT instructions  -->  [keep] only one
        • label L that is never jumped to  -->  [drop] the label

usage
-------

    from optimizer import TACOptimizer
    opt = TACOptimizer(flag_values, player_inventory)
    optimized = opt.optimize(raw_instructions)
    opt.dump_comparison(raw_instructions, optimized)

flag_values      : dict[str, bool]      from SemanticAnalyzer symbol table
player_inventory : set[str]             items the player starts with

"""

from __future__ import annotations
import re
from typing import Optional


# tiny IR (immediate representation) helpers for pattern matching over TAC instructions

def _is_label(instr: str) -> bool:
    return instr.endswith(":")

def _label_name(instr: str) -> str:
    """'FOO:' -> 'FOO'"""
    return instr.rstrip(":")

def _is_unconditional_goto(instr: str) -> bool:
    return re.match(r'^goto\s+\S+$', instr.strip()) is not None

def _is_halt(instr: str) -> bool:
    return instr.strip() == "HALT"

def _is_cond_goto(instr: str) -> Optional[tuple[str, str]]:
    """Returns (temp, label) if instr is 'if <temp> goto <label>', else None."""
    m = re.match(r'^if\s+(\w+)\s+goto\s+(\S+)$', instr.strip())
    return (m.group(1), m.group(2)) if m else None

def _is_inv_has(instr: str) -> Optional[tuple[str, str]]:
    """'t1 = inv_has(key)' -> ('t1', 'key')"""
    m = re.match(r'^(\w+)\s*=\s*inv_has\((\w+)\)$', instr.strip())
    return (m.group(1), m.group(2)) if m else None

def _is_flag_read(instr: str) -> Optional[tuple[str, str]]:
    """'t2 = flag(door_open)' -> ('t2', 'door_open')"""
    m = re.match(r'^(\w+)\s*=\s*flag\((\w+)\)$', instr.strip())
    return (m.group(1), m.group(2)) if m else None

def _is_const_assign(instr: str) -> Optional[tuple[str, bool]]:
    """'t1 = true' / 'tN = false' -> (temp, bool)"""
    m = re.match(r'^(\w+)\s*=\s*(true|false)$', instr.strip())
    if m:
        return m.group(1), m.group(2) == "true"
    return None

def _goto_target(instr: str) -> str:
    """'goto FOO' -> 'FOO'"""
    return instr.strip().split()[-1]

def _is_print(instr: str) -> bool:
    return instr.strip().startswith("PRINT ")


# actual optimizer implementation

class TACOptimizer:
    """
    three-pass TAC optimizer for PicoScrypt

    params
    ----------
    flag_values : dict[str, bool]
        compile-time flag declarations, e.g. {'door_open': False}
    player_inventory : set[str]
        items the player starts with, e.g. {'key'}
    """

    def __init__(self, flag_values: dict, player_inventory: set):
        self.flag_values    = {k: bool(v) for k, v in flag_values.items()}
        self.player_inv     = set(player_inventory)
        self._stats: dict[str, int] = {}

    # the public API

    def optimize(self, instructions: list[str]) -> list[str]:
        """run all three passes and return the optimized instruction list"""
        self._stats = {
            "const_fold_replacements": 0,
            "const_fold_branches_eliminated": 0,
            "dce_unreachable_removed": 0,
            "dce_dead_assigns_removed": 0,
            "peephole_redundant_gotos": 0,
            "peephole_dead_labels": 0,
            "peephole_duplicate_prints": 0,
        }
        out = list(instructions)
        out = self._pass1_constant_folding(out)
        out = self._pass2_dead_code_elimination(out)
        out = self._pass3_peephole(out)
        return out

    def dump_comparison(self, before: list[str], after: list[str]):
        """pretty-printing a before/after side-by-side diff."""
        SEP = "─" * 60
        print(f"\n{'═'*60}")
        print("  OPTIMIZATION REPORT  —  PicoScrypt TAC Optimizer")
        print(f"{'═'*60}\n")

        print("BEFORE OPTIMIZATION")
        print(SEP)
        for i, line in enumerate(before):
            print(f"  {i:03}: {line}")

        print(f"\nAFTER OPTIMIZATION")
        print(SEP)
        for i, line in enumerate(after):
            print(f"  {i:03}: {line}")

        real_after = [l for l in after if not l.strip().startswith("//")]
        removed = len(before) - len(real_after)
        print(f"\nSUMMARY")
        print(SEP)
        print(f"  Instructions before : {len(before)}")
        print(f"  Instructions after  : {len(real_after)} (+ {len(after)-len(real_after)} annotation comments)")
        print(f"  Total removed       : {removed} "
              f"({removed/max(len(before),1)*100:.0f}% reduction)"
              )
        print()
        print("  Pass 1 — Constant Folding")
        print(f"    Condition reads folded  : {self._stats['const_fold_replacements']}")
        print(f"    Branches eliminated     : {self._stats['const_fold_branches_eliminated']}")
        print()
        print("  Pass 2 — Dead Code Elimination")
        print(f"    Unreachable instrs removed : {self._stats['dce_unreachable_removed']}")
        print(f"    Dead temp assigns removed  : {self._stats['dce_dead_assigns_removed']}")
        print()
        print("  Pass 3 — Peephole Optimization")
        print(f"    Redundant gotos removed : {self._stats['peephole_redundant_gotos']}")
        print(f"    Dead labels removed     : {self._stats['peephole_dead_labels']}")
        print(f"    Duplicate PRINTs removed: {self._stats['peephole_duplicate_prints']}")
        print(f"{'═'*60}\n")

    # pass 1: constant folding

    def _pass1_constant_folding(self, instrs: list[str]) -> list[str]:
        """
        replace inv_has / flag reads whose values are known at compile
        time with CONST assignments, then rewrite conditional jumps to
        unconditional ones (or drop the dead branch entirely).
        """
        # first sub-pass: fold condition reads into constant assignments
        # track temp --> known bool value for use in the second sub-pass
        const_temps: dict[str, bool] = {}
        folded: list[str] = []

        for instr in instrs:
            inv_m = _is_inv_has(instr)
            flag_m = _is_flag_read(instr)

            if inv_m:
                temp, item = inv_m
                if item in self.player_inv:
                    val = True
                else:
                    val = False # not in starting inv --> false
                const_temps[temp] = val
                folded.append(f"{temp} = {'true' if val else 'false'}  // folded: inv_has({item}) is always {val}")
                self._stats["const_fold_replacements"] += 1

            elif flag_m:
                temp, flag = flag_m
                if flag in self.flag_values:
                    val = self.flag_values[flag]
                    const_temps[temp] = val
                    folded.append(f"{temp} = {'true' if val else 'false'}  // folded: flag({flag}) = {val}")
                    self._stats["const_fold_replacements"] += 1
                else:
                    folded.append(instr) # unknown at compile time --> keep

            else:
                """ 
                    accumulate any other const assignments so downstream
                    conditional jumps using those temps can also be folded.
                    e.g. t1 = true; if t1 goto L  -->  if true goto L  -->  goto L
                """
                c = _is_const_assign(instr)
                if c:
                    temp, val = c
                    const_temps[temp] = val
                folded.append(instr)

        # second sub-pass: rewrite conditional jumps using known const temp vars
        out: list[str] = []
        for instr in folded:
            cg = _is_cond_goto(instr)
            if cg:
                temp, label = cg
                if temp in const_temps:
                    if const_temps[temp]:
                        # condition is always true --> unconditional jump
                        out.append(f"goto {label}  // folded: {temp} is always true")
                    else:
                        # condition is always false --> branch is never taken, drop it
                        out.append(f"// ELIMINATED: {instr}  [condition always false]")
                    self._stats["const_fold_branches_eliminated"] += 1
                else:
                    out.append(instr)
            else:
                out.append(instr)

        return out

    # pass 2: dead code elimination

    def _pass2_dead_code_elimination(self, instrs: list[str]) -> list[str]:
        """
        1. remove instructions unreachable after an unconditional HALT/goto
           (unless they are a label that is jumped to from elsewhere)
        2. remove assignments to temp vars that are never read
        """
        # collect all jump targets so we know which labels are 'live'!
        # 'live' means "jumped to from somewhere else", so we don't
        # eliminate them as unreachable even if they follow a HALT/goto.
        jump_targets: set[str] = set()
        for instr in instrs:
            if _is_unconditional_goto(instr) or "// folded:" in instr:
                if "goto " in instr:
                    jump_targets.add(_goto_target(instr.split("//")[0]))
            cg = _is_cond_goto(instr)
            if cg:
                jump_targets.add(cg[1])

        # sub-pass A: unreachable code after HALT / unconditional goto
        after_a: list[str] = []
        dead = False
        for instr in instrs:
            stripped = instr.strip()
            if stripped.startswith("//"):
                after_a.append(instr)
                continue

            if dead:
                if _is_label(stripped):
                    lname = _label_name(stripped)
                    if lname in jump_targets:
                        dead = False   # label is reachable → resume
                        after_a.append(instr)
                    else:
                        # label itself is unreachable
                        after_a.append(f"// ELIMINATED (unreachable label): {instr}")
                        self._stats["dce_unreachable_removed"] += 1
                else:
                    after_a.append(f"// ELIMINATED (unreachable): {instr}")
                    self._stats["dce_unreachable_removed"] += 1
            else:
                after_a.append(instr)
                if _is_halt(stripped) or _is_unconditional_goto(stripped):
                    dead = True

        # sub-pass B: dead temporary assignments (assigned but never read)
        # collect all temp vars that appear on the [right-hand side] of any
        # live instruction (i.e. they are 'actually used' somewhere)
        used_temps: set[str] = set()
        for instr in after_a:
            if instr.strip().startswith("//"):
                continue
            # look for temps on the RHS: "if t1 goto ..." or "= ... t1 ..."
            for m in re.finditer(r'\b(t\d+)\b', instr):
                # skip the LHS of an assignment
                lhs_m = re.match(r'^(t\d+)\s*=', instr.strip())
                if lhs_m and m.group(1) == lhs_m.group(1) and m.start() == instr.index(lhs_m.group(1)):
                    continue
                used_temps.add(m.group(1))

        after_b: list[str] = []
        for instr in after_a:
            stripped = instr.strip()
            if stripped.startswith("//"):
                after_b.append(instr)
                continue
            lhs_m = re.match(r'^(t\d+)\s*=', stripped)
            if lhs_m:
                temp = lhs_m.group(1)
                if temp not in used_temps:
                    after_b.append(f"// ELIMINATED (dead assign): {instr}")
                    self._stats["dce_dead_assigns_removed"] += 1
                    continue
            after_b.append(instr)

        return after_b

    # pass 3: peephole optimization

    def _pass3_peephole(self, instrs: list[str]) -> list[str]:
        """
            window-based local optimizations:
              - goto L followed (possibly after comments) by label L  -->  drop goto
              - consecutive identical PRINT instructions  -->  keep first
              - PRINT+HALT followed by another PRINT+HALT block  -->  keep first
              - labels that no jump instruction targets  -->  drop
        """
        # collect live labels again (after pass 2: DCE, may have removed some gotos)
        live_labels: set[str] = set()
        for instr in instrs:
            if instr.strip().startswith("//"):
                continue
            if "goto " in instr:
                m = re.search(r'goto\s+(\S+)', instr)
                if m:
                    live_labels.add(m.group(1).rstrip(";"))

        out: list[str] = []
        i = 0
        while i < len(instrs):
            instr = instrs[i]
            stripped = instr.strip()

            # skip comment lines
            if stripped.startswith("//"):
                out.append(instr)
                i += 1
                continue

            # dead label removal
            if _is_label(stripped):
                lname = _label_name(stripped)
                if lname not in live_labels:
                    out.append(f"// ELIMINATED (dead label): {instr}")
                    self._stats["peephole_dead_labels"] += 1
                    i += 1
                    continue

            # redundant goto: goto L and next real instr is label L
            if _is_unconditional_goto(stripped) and "// folded" not in instr:
                target = _goto_target(stripped)
                # look ahead past comments for the next real instruction
                j = i + 1
                while j < len(instrs) and instrs[j].strip().startswith("//"):
                    j += 1
                if j < len(instrs):
                    next_real = instrs[j].strip()
                    if _is_label(next_real) and _label_name(next_real) == target:
                        out.append(f"// ELIMINATED (redundant goto): {instr}")
                        self._stats["peephole_redundant_gotos"] += 1
                        i += 1
                        continue

            # duplicate consecutive PRINT
            if _is_print(stripped) and out:
                # find the last non-comment instruction we emitted
                prev = next((x for x in reversed(out) if not x.strip().startswith("//")), None)
                if prev is not None and prev.strip() == stripped:
                    out.append(f"// ELIMINATED (duplicate PRINT): {instr}")
                    self._stats["peephole_duplicate_prints"] += 1
                    i += 1
                    continue

            out.append(instr)
            i += 1

        return out


# demo

if __name__ == "__main__":
    """
        runs optimizer on a hand-crafted TAC sequence 
        representative of what codegen.py produces for example.pico
          ++ prints a before/after report
    """

    # simulated flag declarations and player inventory (from crypt.pico)
    flags = {"door_open": False}
    inventory = {"key"}

    # raw TAC as codegen.py would produce for crypt.pico
    raw = [
        "ROOM_ENTRANCE_ENTER:",
        'PRINT "You are in the entrance."',
        "goto ROOM_ENTRANCE_END",
        "ROOM_ENTRANCE_END:",
        "t1 = inv_has(key)",
        "if t1 goto PUZZLE_DOOR_OPEN_UNLOCK_1",
        "goto PUZZLE_DOOR_OPEN_END_1",
        "PUZZLE_DOOR_OPEN_UNLOCK_1:",
        "door_open = true",
        "PUZZLE_DOOR_OPEN_END_1:",
        "t2 = flag(door_open)",
        "if t2 goto PUZZLE_DOOR_OPEN_UNLOCK_2",
        "goto PUZZLE_DOOR_OPEN_END_2",
        "PUZZLE_DOOR_OPEN_UNLOCK_2:",
        "door_open = true",
        "PUZZLE_DOOR_OPEN_END_2:",
        "ROOM_CHAMBER_ENTER:",
        'PRINT "You escaped!"',
        "HALT",
        'PRINT "You escaped!"',     # [NOTE]: duplicate --> peephole removes
        "HALT",
        "ROOM_CHAMBER_END:",
    ]

    opt = TACOptimizer(flags, inventory)
    optimized = opt.optimize(raw)
    opt.dump_comparison(raw, optimized)