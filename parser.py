# grammar rule --> method (creating/ returning objects!)

from ast_nodes import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos    = 0

    def current(self):
        return self.tokens[self.pos]

    def peek(self):
        """Look at current token type."""
        return self.current().type

    def consume(self, expected_type):
        """Consume a token of the expected type, or raise an error."""
        tok = self.current()
        if tok.type != expected_type:
            raise SyntaxError(
                f'Line {tok.line}: expected {expected_type}, got {tok.type} ({tok.value!r})'
            )
        self.pos += 1
        return tok

    def match(self, *types):
        """Return True if current token matches any of the given types."""
        return self.peek() in types

    # grammar rules

    def parse_program(self):
        node = self.parse_world_block()
        self.consume('EOF')
        return node

    def parse_world_block(self):
        self.consume('WORLD')
        name = self.consume('IDENT').value
        self.consume('COLON')
        body = self.parse_world_body()
        self.consume('END')
        return WorldNode(name, body)

    def parse_world_body(self):
        body = []
        while not self.match('END', 'EOF'):
            if self.match('FLAG'):
                body.append(self.parse_flag_decl())
            elif self.match('PLAYER'):
                body.append(self.parse_player_block())
            elif self.match('ITEM'):
                body.append(self.parse_item_block())
            elif self.match('ROOM'):
                body.append(self.parse_room_block())
            elif self.match('PUZZLE'):
                body.append(self.parse_puzzle_block())
            elif self.match('NPC'):
                body.append(self.parse_npc_block())
            else:
                tok = self.current()
                raise SyntaxError(f'Line {tok.line}: unexpected token {tok.type} ({tok.value!r}) in world body')
        return body

    def parse_flag_decl(self):
        self.consume('FLAG')
        name = self.consume('IDENT').value
        self.consume('EQUALS')
        value = self.parse_bool_literal()
        return FlagNode(name, value)

    def parse_bool_literal(self):
        if self.match('TRUE'):
            self.consume('TRUE')
            return True
        elif self.match('FALSE'):
            self.consume('FALSE')
            return False
        else:
            tok = self.current()
            raise SyntaxError(f'Line {tok.line}: expected true or false, got {tok.value!r}')

    def parse_player_block(self):
        self.consume('PLAYER')
        self.consume('COLON')
        inventory = []
        while self.match('INV'):
            self.consume('INV')
            item_name = self.consume('IDENT').value
            inventory.append(InvNode(item_name))
        self.consume('END')
        return PlayerNode(inventory)

    def parse_item_block(self):
        self.consume('ITEM')
        name = self.consume('IDENT').value
        self.consume('COLON')
        actions = []
        while not self.match('END', 'EOF'):
            if self.match('EXAMINE'):
                actions.append(self.parse_examine_action())
            elif self.match('USE'):
                actions.append(self.parse_use_action())
            else:
                tok = self.current()
                raise SyntaxError(f'Line {tok.line}: unexpected token {tok.type} in item block')
        self.consume('END')
        return ItemNode(name, actions)

    def parse_examine_action(self):
        self.consume('EXAMINE')
        self.consume('COLON')
        text = self.consume('STRING').value
        return ExamineAction(text)

    def parse_use_action(self):
        self.consume('USE')
        self.consume('COLON')
        stmts = self.parse_statements()
        self.consume('END')
        return UseAction(stmts)

    def parse_room_block(self):
        self.consume('ROOM')
        name = self.consume('IDENT').value
        self.consume('COLON')
        body = []
        while not self.match('END', 'EOF'):
            if self.match('ITEM'):
                body.append(self.parse_item_ref())
            elif self.match('GO'):
                body.append(self.parse_exit_stmt())
            elif self.match('ON'):
                body.append(self.parse_on_enter_block())
            else:
                tok = self.current()
                raise SyntaxError(f'Line {tok.line}: unexpected token {tok.type} in room body')
        self.consume('END')
        return RoomNode(name, body)

    def parse_item_ref(self):
        self.consume('ITEM')
        name = self.consume('IDENT').value
        return ItemRef(name)

    def parse_exit_stmt(self):
        self.consume('GO')
        if not self.match('NORTH', 'SOUTH', 'EAST', 'WEST'):
            tok = self.current()
            raise SyntaxError(
                f'Line {tok.line}: expected direction (north/south/east/west), got {tok.type}'
            )
        direction = self.consume(self.peek()).value
        self.consume('ARROW')
        target = self.consume('IDENT').value
        condition = None
        if self.match('REQUIRES'):
            self.consume('REQUIRES')
            condition = self.parse_condition()
        return ExitNode(direction, target, condition)

    def parse_on_enter_block(self):
        self.consume('ON')
        self.consume('ENTER')
        self.consume('COLON')
        stmts = self.parse_statements()
        self.consume('END')
        return OnEnterBlock(stmts)

    def parse_puzzle_block(self):
        self.consume('PUZZLE')
        self.consume('GATE')
        self.consume('COLON')
        self.consume('REQUIRES')
        condition = self.parse_condition()
        self.consume('UNLOCK')
        unlock_flag = self.consume('IDENT').value
        self.consume('END')
        return PuzzleNode(condition, unlock_flag)

    def parse_npc_block(self):
        self.consume('NPC')
        name = self.consume('IDENT').value
        self.consume('COLON')
        dialogues = []
        while not self.match('END', 'EOF'):
            if self.match('TALK'):
                dialogues.append(self.parse_dialogue_block())
            else:
                tok = self.current()
                raise SyntaxError(f'Line {tok.line}: unexpected token {tok.type} in npc block')
        self.consume('END')
        return NPCNode(name, dialogues)

    def parse_dialogue_block(self):
        self.consume('TALK')
        self.consume('COLON')
        branches = []
        while not self.match('END', 'EOF'):
            branches.append(self.parse_dialogue_branch())
        self.consume('END')
        return DialogueNode(branches)

    def parse_dialogue_branch(self):
        if self.match('IF'):
            self.consume('IF')
            condition = self.parse_condition()
            if_statements = self.parse_statements()
            else_statements = []
            if self.match('ELSE'):
                self.consume('ELSE')
                else_statements = self.parse_statements()
            self.consume('END')
            return DialogueBranch(condition, if_statements, else_statements)

        statements = self.parse_statements()
        if not statements:
            tok = self.current()
            raise SyntaxError(f'Line {tok.line}: expected statement or if-branch in talk block')
        return DialogueBranch(None, statements, [])

    def parse_condition(self):
        if self.match('FLAG'):
            self.consume('FLAG')
            name = self.consume('IDENT').value
            return ConditionFlag(name)
        elif self.match('INV'):
            self.consume('INV')
            self.consume('HAS')
            name = self.consume('IDENT').value
            return ConditionInv(name)
        else:
            tok = self.current()
            raise SyntaxError(f'Line {tok.line}: expected condition (flag/inv), got {tok.type}')

    def parse_statements(self):
        stmts = []
        while self.match('SAY', 'WIN', 'LOSE'):
            if self.match('SAY'):
                self.consume('SAY')
                text = self.consume('STRING').value
                stmts.append(SayStmt(text))
            elif self.match('WIN'):
                self.consume('WIN')
                text = self.consume('STRING').value
                stmts.append(WinStmt(text))
            elif self.match('LOSE'):
                self.consume('LOSE')
                text = self.consume('STRING').value
                stmts.append(LoseStmt(text))
        return stmts

# custom pretty printer :D
def print_ast(node, indent=0):
    pad = "  " * indent
    name = type(node).__name__

    if isinstance(node, WorldNode):
        print(f"{pad}WorldNode({node.name!r})")
        for child in node.body:
            print_ast(child, indent + 1)

    elif isinstance(node, FlagNode):
        print(f"{pad}FlagNode({node.name!r} = {node.value})")

    elif isinstance(node, PlayerNode):
        print(f"{pad}PlayerNode")
        for child in node.inventory:
            print_ast(child, indent + 1)

    elif isinstance(node, InvNode):
        print(f"{pad}InvNode({node.item_name!r})")

    elif isinstance(node, ItemNode):
        print(f"{pad}ItemNode({node.name!r})")
        for action in node.actions:
            print_ast(action, indent + 1)

    elif isinstance(node, ExamineAction):
        print(f"{pad}ExamineAction({node.text!r})")

    elif isinstance(node, UseAction):
        print(f"{pad}UseAction")
        for stmt in node.statements:
            print_ast(stmt, indent + 1)

    elif isinstance(node, RoomNode):
        print(f"{pad}RoomNode({node.name!r})")
        for child in node.body:
            print_ast(child, indent + 1)

    elif isinstance(node, ItemRef):
        print(f"{pad}ItemRef({node.item_name!r})")

    elif isinstance(node, ExitNode):
        print(f"{pad}ExitNode({node.direction} -> {node.target!r})")
        if node.condition:
            print_ast(node.condition, indent + 1)

    elif isinstance(node, OnEnterBlock):
        print(f"{pad}OnEnterBlock")
        for stmt in node.statements:
            print_ast(stmt, indent + 1)

    elif isinstance(node, PuzzleNode):
        print(f"{pad}PuzzleNode(unlock={node.unlock_flag!r})")
        print_ast(node.condition, indent + 1)

    elif isinstance(node, NPCNode):
        print(f"{pad}NPCNode({node.name!r})")
        for dialogue in node.dialogues:
            print_ast(dialogue, indent + 1)

    elif isinstance(node, DialogueNode):
        print(f"{pad}DialogueNode")
        for branch in node.branches:
            print_ast(branch, indent + 1)

    elif isinstance(node, DialogueBranch):
        if node.condition is None:
            print(f"{pad}DialogueBranch(default)")
        else:
            print(f"{pad}DialogueBranch(if)")
            print_ast(node.condition, indent + 1)
        if node.if_statements:
            print(f"{pad}  then:")
            for stmt in node.if_statements:
                print_ast(stmt, indent + 2)
        if node.else_statements:
            print(f"{pad}  else:")
            for stmt in node.else_statements:
                print_ast(stmt, indent + 2)

    elif isinstance(node, ConditionFlag):
        print(f"{pad}ConditionFlag({node.flag_name!r})")

    elif isinstance(node, ConditionInv):
        print(f"{pad}ConditionInv(has {node.item_name!r})")

    elif isinstance(node, SayStmt):
        print(f"{pad}SayStmt({node.text!r})")

    elif isinstance(node, WinStmt):
        print(f"{pad}WinStmt({node.text!r})")

    elif isinstance(node, LoseStmt):
        print(f"{pad}LoseStmt({node.text!r})")

    else:
        print(f"{pad}{name}(?)")


# test!
if __name__ == '__main__':
    from lexer import tokenize

    source = open('examples/crypt.pico').read()
    tokens = tokenize(source)
    parser = Parser(tokens)
    ast    = parser.parse_program()
    print_ast(ast)