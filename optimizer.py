"""

==================================
  (งツ)ว PicoScrypt TAC Optimizer
==================================

implements [[[ 3 optimization passes ]]] over the TAC instruction list
produced by codegen.TACGenerator:

  pass 1 — constant folding
      evaluates flag/inv conditions whose values are known at compile time.
      - statically-known conditions  -->  replaced with CONST assignment
      - conditional jump  -->  rewritten to an unconditional goto (always-true) 
      OR dropped (always-false).

  pass 2 — dead code elimination (region-aware)
      - intra-region unreachable code: instructions after an
        unconditional HALT or goto, before the next top-level label,
        are removed
      - dead temp assignments: temps assigned but never read anywhere
        in the entire instruction list are removed

  pass 3 — peephole optimization
      - goto L immediately followed by label L  -->  drop the goto
      - consecutive identical PRINT instructions  -->  keep only first
      - labels never targeted by any jump  -->  drop

usage
-------
    from optimizer import TACOptimizer
    opt = TACOptimizer(flag_values, player_inventory)
    optimized = opt.optimize(raw_instructions)
    opt.dump_comparison(raw_instructions, optimized)
"""

from __future__ import annotations
import re
from typing import Optional


# tiny IR (immediate representation) helpers for pattern matching over TAC instructions

# a "top-level label" is one that opens an independent TAC region
# we will recognise them by the naming conventions codegen uses
_TOP_LEVEL_PREFIXES = ("ROOM_", "PUZZLE_")

def _is_label(instr: str) -> bool:
    return bool(re.match(r'^\s*[A-Z][A-Z0-9_]*\s*:\s*$', instr))
 
def _label_name(instr: str) -> str:
    return instr.strip().rstrip(":").strip()
 
def _is_top_level_label(instr: str) -> bool:
    if not _is_label(instr):
        return False
    name = _label_name(instr)
    return any(name.startswith(p) for p in _TOP_LEVEL_PREFIXES)

def _is_unconditional_goto(instr: str) -> bool:
    # fix: strip inline annotation comments before matching so that
    # "goto LABEL  // folded: ..." is still recognised as an unconditional goto
    code = instr.split("//")[0].strip()
    return bool(re.match(r'^goto\s+\S+$', code))

def _is_halt(instr: str) -> bool:
    return instr.strip() == "HALT"
 
def _is_cond_goto(instr: str) -> Optional[tuple[str, str]]:
    m = re.match(r'^\s*if\s+(\w+)\s+goto\s+(\S+)\s*$', instr)
    return (m.group(1), m.group(2)) if m else None
 
def _is_inv_has(instr: str) -> Optional[tuple[str, str]]:
    m = re.match(r'^\s*(\w+)\s*=\s*inv_has\((\w+)\)\s*$', instr)
    return (m.group(1), m.group(2)) if m else None
 
def _is_flag_read(instr: str) -> Optional[tuple[str, str]]:
    m = re.match(r'^\s*(\w+)\s*=\s*flag\((\w+)\)\s*$', instr)
    return (m.group(1), m.group(2)) if m else None
 
def _is_const_assign(instr: str) -> Optional[tuple[str, bool]]:
    m = re.match(r'^\s*(\w+)\s*=\s*(true|false)\s*', instr)
    if m:
        return m.group(1), m.group(2) == "true"
    return None

def _goto_target(instr: str) -> str:
    # fix: strip inline annotation comment first so "goto L  // folded: ..." -> "L"
    code = instr.split("//")[0]
    m = re.search(r'goto\s+(\S+)', code)
    if m is None:
        raise ValueError(f"_goto_target called on non-goto instruction: {instr!r}")
    return m.group(1).strip()
 
def _is_print(instr: str) -> bool:
    return bool(re.match(r'^\s*PRINT\s+', instr))
 
def _is_comment(instr: str) -> bool:
    return instr.strip().startswith("//")
 
def _all_goto_targets(instrs: list[str]) -> set[str]:
    targets: set[str] = set()
    for instr in instrs:
        if _is_comment(instr):
            continue
        if "goto " in instr:
            m = re.search(r'goto\s+(\S+)', instr)
            if m:
                targets.add(m.group(1).strip())
    return targets

# actual optimizer implementation

class TACOptimizer:
    """
        params
        ----------
        flag_values : dict[str, bool]
            compile-time flag declarations, e.g. {'door_open': False}.
        player_inventory : set[str]
            items the player starts with, e.g. {'key'}.
    """

    def __init__(self, flag_values: dict, player_inventory: set):
        self.flag_values = {k: bool(v) for k, v in flag_values.items()}
        self.player_inv  = set(player_inventory)
        self._stats: dict[str, int] = {}

    # the public API 

    def optimize(self, instructions: list[str]) -> list[str]:
        """Run all three passes and return the optimized instruction list."""
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
        """Pretty-print a before/after report."""
        SEP = "─" * 60
        print(f"\n{'═'*60}")
        print("  OPTIMIZATION REPORT  —  PicoScrypt TAC Optimizer")
        print(f"{'═'*60}\n")

        print("BEFORE OPTIMIZATION")
        print(SEP)
        for i, line in enumerate(before):
            print(f"  {i:03}: {line}")

        print(f"\nAFTER OPTIMIZATION  (annotations show what was removed)")
        print(SEP)
        for i, line in enumerate(after):
            print(f"  {i:03}: {line}")

        real_after = [l for l in after if not _is_comment(l)]
        removed = len(before) - len(real_after)
        print(f"\nSUMMARY")
        print(SEP)
        print(f"  Instructions before : {len(before)}")
        print(f"  Instructions after  : {len(real_after)}"
              f"  (+ {len(after) - len(real_after)} annotation comments)")
        print(f"  Total removed       : {removed}"
              f"  ({removed / max(len(before), 1) * 100:.0f}% reduction)")
        print()
        print("  Pass 1 — Constant Folding")
        print(f"    Condition reads folded   : {self._stats['const_fold_replacements']}")
        print(f"    Branches eliminated      : {self._stats['const_fold_branches_eliminated']}")
        print()
        print("  Pass 2 — Dead Code Elimination  (region-aware)")
        print(f"    Unreachable instrs removed : {self._stats['dce_unreachable_removed']}")
        print(f"    Dead temp assigns removed  : {self._stats['dce_dead_assigns_removed']}")
        print()
        print("  Pass 3 — Peephole Optimization")
        print(f"    Redundant gotos removed  : {self._stats['peephole_redundant_gotos']}")
        print(f"    Dead labels removed      : {self._stats['peephole_dead_labels']}")
        print(f"    Duplicate PRINTs removed : {self._stats['peephole_duplicate_prints']}")
        print(f"{'═'*60}\n")

    # pass 1: constant folding

    def _pass1_constant_folding(self, instrs: list[str]) -> list[str]:
        """
            sub-pass A: replace inv_has / flag reads with known constants.
            sub-pass B: rewrite conditional jumps whose temp is now constant.
        """
        const_temps: dict[str, bool] = {}
        folded: list[str] = []

        for instr in instrs:
            if _is_comment(instr):
                folded.append(instr)
                continue

            inv_m  = _is_inv_has(instr)
            flag_m = _is_flag_read(instr)

            if inv_m:
                temp, item = inv_m
                val = item in self.player_inv
                const_temps[temp] = val
                folded.append(
                    f"{temp} = {'true' if val else 'false'}"
                    f"  // folded: inv_has({item}) is always {val}"
                )
                self._stats["const_fold_replacements"] += 1

            elif flag_m:
                temp, flag = flag_m
                if flag in self.flag_values:
                    val = self.flag_values[flag]
                    const_temps[temp] = val
                    folded.append(
                        f"{temp} = {'true' if val else 'false'}"
                        f"  // folded: flag({flag}) = {val}"
                    )
                    self._stats["const_fold_replacements"] += 1
                else:
                    folded.append(instr)

            else:
                c = _is_const_assign(instr)
                if c:
                    const_temps[c[0]] = c[1]
                folded.append(instr)

        # sub-pass B: rewrite / eliminate conditional jumps
        out: list[str] = []
        for instr in folded:
            if _is_comment(instr):
                out.append(instr)
                continue
            cg = _is_cond_goto(instr)
            if cg:
                temp, label = cg
                if temp in const_temps:
                    self._stats["const_fold_branches_eliminated"] += 1
                    if const_temps[temp]:
                        out.append(
                            f"goto {label}  // folded: {temp} always true"
                        )
                    else:
                        out.append(
                            f"// ELIMINATED (branch never taken): {instr}  [condition always false]"
                        )
                    continue
            out.append(instr)

        return out

    # pass 2: dead code elimination (region-aware)

    def _pass2_dead_code_elimination(self, instrs: list[str]) -> list[str]:
        """
            sub-pass A  — intra-region unreachable code
                a HALT or unconditional goto ends the current region's live code.
                instructions until the *next top-level label* (which opens a 
                brand-new independent region) are dead, UNLESS they are themselves 
                a label targeted by a jump.

            sub-pass B  — dead temporary assignments
                a temp that is assigned but never appears on any RHS is dead.
        """
        jump_targets = _all_goto_targets(instrs)

        # sub-pass A
        after_a: list[str] = []
        dead = False

        for instr in instrs:
            stripped = instr.strip()

            if _is_comment(stripped):
                after_a.append(instr)
                continue

            # a top-level label always starts a fresh live region
            if _is_top_level_label(stripped):
                dead = False
                after_a.append(instr)
                continue

            if dead:
                # inside a dead stretch - only a jump-targeted label revives it
                if _is_label(stripped):
                    lname = _label_name(stripped)
                    if lname in jump_targets:
                        dead = False
                        after_a.append(instr)
                    else:
                        after_a.append(
                            f"// ELIMINATED (unreachable label): {instr}"
                        )
                        self._stats["dce_unreachable_removed"] += 1
                else:
                    after_a.append(f"// ELIMINATED (unreachable): {instr}")
                    self._stats["dce_unreachable_removed"] += 1
            else:
                after_a.append(instr)
                if _is_halt(stripped) or _is_unconditional_goto(stripped):
                    dead = True

        # sub-pass B: dead temp assignments
        # collect every temp that appears somewhere on a RHS
        used_temps: set[str] = set()
        for instr in after_a:
            if _is_comment(instr):
                continue
            lhs_m = re.match(r'^\s*(t\d+)\s*=', instr)
            # find all tN tokens; exclude the LHS position
            for m in re.finditer(r'\b(t\d+)\b', instr):
                if lhs_m and m.group(1) == lhs_m.group(1):
                    # only skip if this match IS the lhs token
                    if m.start() == instr.index(lhs_m.group(1)):
                        continue
                used_temps.add(m.group(1))

        after_b: list[str] = []
        for instr in after_a:
            if _is_comment(instr):
                after_b.append(instr)
                continue
            lhs_m = re.match(r'^\s*(t\d+)\s*=', instr)
            if lhs_m and lhs_m.group(1) not in used_temps:
                after_b.append(f"// ELIMINATED (dead temp assign): {instr}")
                self._stats["dce_dead_assigns_removed"] += 1
            else:
                after_b.append(instr)

        return after_b

    # pass 3: peephole optimization

    def _pass3_peephole(self, instrs: list[str]) -> list[str]:
        """
            pattern-matching over a sliding window:
            - goto L; <comments>; L:  -->  drop the goto (it jumps to itself)
            - consecutive identical PRINT  -->  keep only the first
            - labels never targeted by any jump  -->  drop

            updates
            -------
              - tracks when a dead label is removed
              - keeps eliminating subsequent non-label instructions as out.append(f"// ELIMINATED (dead after removed label): {instr}")
              - stops elimination when a live label is encountered again
        """
        live_labels = _all_goto_targets(instrs)

        out: list[str] = []
        i = 0
        dead = False
        entry_label_preserved = False
        while i < len(instrs):
            instr  = instrs[i]
            stripped = instr.strip()

            if _is_comment(stripped):
                out.append(instr)
                i += 1
                continue

            if _is_label(stripped):
                lname = _label_name(stripped)

                # preserve the entry label even if it isn't targeted by a goto
                if _is_top_level_label(stripped) and not entry_label_preserved:
                    entry_label_preserved = True
                    dead = False
                    out.append(instr)
                    i += 1
                    continue

                if dead:
                    if lname in live_labels:
                        dead = False
                        out.append(instr)
                    else:
                        out.append(f"// ELIMINATED (dead label): {instr}")
                        self._stats["peephole_dead_labels"] += 1
                    i += 1
                    continue

                if lname not in live_labels:
                    out.append(f"// ELIMINATED (dead label): {instr}")
                    self._stats["peephole_dead_labels"] += 1
                    dead = True
                    i += 1
                    continue

            if dead:
                out.append(f"// ELIMINATED (dead after removed label): {instr}")
                i += 1
                continue

            # redundant goto: goto L and next real instr is label L
            # look ahead past comments for the next real instruction
            if _is_unconditional_goto(stripped) and "// folded" not in instr:
                target = _goto_target(stripped)
                j = i + 1
                while j < len(instrs) and _is_comment(instrs[j]):
                    j += 1
                if j < len(instrs):
                    nxt = instrs[j].strip()
                    if _is_label(nxt) and _label_name(nxt) == target:
                        out.append(f"// ELIMINATED (redundant goto): {instr}")
                        self._stats["peephole_redundant_gotos"] += 1
                        i += 1
                        continue

            # duplicate consecutive PRINT
            if _is_print(stripped):
                prev_real = next(
                    (x for x in reversed(out) if not _is_comment(x)), None
                )
                if prev_real is not None and prev_real.strip() == stripped:
                    out.append(f"// ELIMINATED (duplicate PRINT): {instr}")
                    self._stats["peephole_duplicate_prints"] += 1
                    i += 1
                    continue

            out.append(instr)
            i += 1

        return out


if __name__ == "__main__":
    """
    run the optimizer on two hand-crafted TAC sequences:

      test A — crypt.pico output
          reproduces exactly what codegen.py emits for crypt.pico.
          key facts: player has 'key' in inventory; door_open starts False.

          expected:
            - inv_has(key) --> true  (constant folded, branch always taken)
            - flag(door_open) --> false (constant folded, branch eliminated)
            - intra-region dead code after HALT removed
            - redundant goto + dead labels cleaned

      test B — duplicate PRINT peephole
          2 identical consecutive PRINT instructions; the second must
          be removed by Pass 3.

      test C — dead label body elimination
            a conditional jump whose condition is always false, so the target
            label is never jumped to. the label and all instructions after it
            until the next top-level label should be removed as dead code by Pass 3!
    """

    print("=" * 60)
    print("TEST A  —  crypt.pico representative TAC")
    print("=" * 60)

    flags_a = {"door_open": False}
    inv_a   = {"key"}

    # faithful reproduction of codegen output for crypt.pico
    raw_a = [
        "ROOM_CHAMBER_ENTER:",
        'PRINT "You escaped!"',
        "HALT",
        "ROOM_CHAMBER_END:", # intra-region dead (after HALT, before next top-level)
        "t1 = inv_has(key)",
        "if t1 goto PUZZLE_DOOR_OPEN_UNLOCK_1",
        "goto PUZZLE_DOOR_OPEN_END_1",
        "PUZZLE_DOOR_OPEN_UNLOCK_1:",
        "door_open = true",
        "PUZZLE_DOOR_OPEN_END_1:",
    ]

    opt_a = TACOptimizer(flags_a, inv_a)
    out_a = opt_a.optimize(raw_a)
    opt_a.dump_comparison(raw_a, out_a)

    print()
    print("=" * 60)
    print("TEST B  —  duplicate PRINT peephole")
    print("=" * 60)

    raw_b = [
        "ROOM_HALL_ENTER:",
        'PRINT "You are in the hall."',
        'PRINT "You are in the hall."', # duplicate --> peephole removes
        "goto ROOM_HALL_END",
        "ROOM_HALL_END:",
        "t1 = inv_has(torch)",
        "if t1 goto PUZZLE_LIGHT_UNLOCK_1",
        "goto PUZZLE_LIGHT_END_1",
        "PUZZLE_LIGHT_UNLOCK_1:",
        "light_on = true",
        "PUZZLE_LIGHT_END_1:",
    ]

    opt_b = TACOptimizer({"light_on": False}, set()) # player has no items
    out_b = opt_b.optimize(raw_b)
    opt_b.dump_comparison(raw_b, out_b)

    print()
    print("=" * 60)
    print("TEST C  —  dead label body elimination")
    print("=" * 60)

    raw_c = [
        "ROOM_SHIP_ENTER:",
        "t1 = false",
        "if t1 goto PUZZLE_HULL_PATCHED_UNLOCK_1",
        "goto PUZZLE_HULL_PATCHED_END_1",
        "PUZZLE_HULL_PATCHED_UNLOCK_1:",
        "hull_patched = true",
        "PUZZLE_HULL_PATCHED_END_1:",
    ]

    opt_c = TACOptimizer({}, set())
    out_c = opt_c.optimize(raw_c)
    opt_c.dump_comparison(raw_c, out_c)