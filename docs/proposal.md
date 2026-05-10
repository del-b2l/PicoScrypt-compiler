**CS4031 – Compiler Construction**

**Course Project Proposal**

**Spring 2026**

| Project Title: | PicoScrypt |
| :---- | :---- |
| **Theme:** | 8-bit Adventure |

---

**Team Members:**

| Student Name | Student ID |
| :---- | :---- |
| 1\. Syeda Batool Kazmi | 23K-0672 |
| 2\. Rabia Zulfiqar | 23K-0851 |

---

**1\. Language Concept**  
PicoScrypt is a domain-specific language for authoring text-based adventure games in the spirit of classic 8-bit RPGs and the Pico-8 fantasy console aesthetic. It lets developers declare worlds, rooms, NPCs, items, puzzle gates, and player actions using a clean, readable syntax – like a programmable RPG Maker engine distilled into a language. It is perfect for hobbyist game writers, retro gaming enthusiasts and beginners alike.

**2\. Key Features**

* Feature 1: Declarative world-building.  
  Rooms, items, and NPCs) are defined in self-contained blocks forming a clear scene hierarchy.

* Feature 2: Player action verbs (e.g. go, take, drop, use, examine, talk, give).  
  They form the interaction vocabulary.

* Feature 3: Puzzle gates with “requires” conditions.  
  Exits and puzzle blocks accept a “requires” clause checked against variables to enable key-and-lock mechanics without extra syntax.

* Feature 4: Typed flag & inventory system.  
  Flags declared at world scope drive all game-state logic like inventory systems.   
  They are statically typed at declaration and cannot change type.

* Feature 5: Branching dialogue trees.  
  NPC dialogue blocks support conditional branches (if / else / end) checked against flags and inventory state.  
  Enables rich story moments and quest progression with clear and concise syntax.

**3\. Example Program**

The snippet below demonstrates a two-room mini-world with an NPC, a Pokémon-style battle encounter, an item-gated puzzle, and a win condition

// A simple program in our language

**world Crypt:**

    **flag** door\_open \= false

    **player:**

         **inv** key

    **end**

    **item key:**

        **examine:** "An old iron key."

    **end**

    **item gem:**

        **use:**

            **say** "The gem clicks into place."

        **end**

    **end**

    **room entrance:**

        **item** gem

        **go** **north** \-\> chamber requires flag door\_open

     **end**

  **room chamber:**

    **on enter:**

      **win** "You escaped\!"

    **end**

  **end**

  **puzzle gate:**

    **requires** inv has key

    **unlock** door\_open

  **end**

**end**

**4\. Target Output**

* Input files use the .pico extension and are run via:  
  picoscrypt game.pico  
  picoscrypt game.pico \--debug

* Direct execution results.

  * The compiler walks the Abstract Syntax Tree (AST) and runs the game output (room descriptions, dialogue, and win/lose screens) directly in the terminal.

  * It interprets the source similarly to how Python executes scripts.

* Invocation with \--debug:

  * The compiler prints the token stream, parse tree, symbol-table snapshot, and Three-Address Code (TAC) listing to help inspect each compiler phase.

**5\. Expected Challenges**

* Challenge 1: Left-recursive expression grammar \[ LL(1) \] to avoid infinite recursion.

* Challenge 2: Multi-level symbol table and forward references.   
  The semantic analyser must resolve forward references (e.g. a room exit pointing to a room declared later in the same world) without a two-pass architecture, requiring careful deferred resolution in the symbol table.

* Challenge 3: Lowering puzzle gates and on-enter blocks to TAC.  
  On-enter action blocks introduce implicit conditional control flow that must be linearised into labelled Three-Address Code jumps for which we need to design a clean IR without hardcoding game logic.

