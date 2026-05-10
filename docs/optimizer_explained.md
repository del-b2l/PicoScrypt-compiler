### for crypt.pico

| Instr | What happened | Why it's correct |
| ----- | ------------- | ---------------- |
| 000 ROOM_CHAMBER_ENTER: | dead label | nothing ever `goto`s it |
| 003 ROOM_CHAMBER_END: | dead label | nothing ever `goto`s it |
| 004 t1 = true | kept (needed) | t1 is read by instr 005 |
| 005 goto PUZZLE_DOOR_OPEN_UNLOCK_1 | kept | unconditional jump, correctly folded from `if t1` |
| 006 goto PUZZLE_DOOR_OPEN_END_1 | unreachable | falls after an unconditional goto, before the next top-level label |
| 009 PUZZLE_DOOR_OPEN_END_1: | dead label | only instr 006 jumped to it, and 006 was eliminated |

> Pass 1 folds the branch, which makes 006 unreachable (Pass 2), which makes PUZZLE_DOOR_OPEN_END_1: a dead label (Pass 3). The optimizer is done and correct.