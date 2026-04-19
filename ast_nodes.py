class WorldNode:
    def __init__(self, name, body):
        self.name = name    # string
        self.body = body    # list of nodes

    def __repr__(self):
        return f'WorldNode({self.name!r}, {self.body})'

class FlagNode:
    def __init__(self, name, value):
        self.name  = name   # string
        self.value = value  # True or False

    def __repr__(self):
        return f'FlagNode({self.name!r}, {self.value})'

class PlayerNode:
    def __init__(self, inventory):
        self.inventory = inventory  # list of InvNode

    def __repr__(self):
        return f'PlayerNode({self.inventory})'

class InvNode:
    def __init__(self, item_name):
        self.item_name = item_name

    def __repr__(self):
        return f'InvNode({self.item_name!r})'

class ItemNode:
    def __init__(self, name, actions):
        self.name    = name     # string
        self.actions = actions  # list of ExamineAction / UseAction

    def __repr__(self):
        return f'ItemNode({self.name!r}, {self.actions})'

class ExamineAction:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return f'ExamineAction({self.text!r})'

class UseAction:
    def __init__(self, statements):
        self.statements = statements    # list of statements

    def __repr__(self):
        return f'UseAction({self.statements})'

class RoomNode:
    def __init__(self, name, body):
        self.name = name    # string
        self.body = body    # list of ItemRef / ExitNode / OnEnterBlock

    def __repr__(self):
        return f'RoomNode({self.name!r}, {self.body})'

class ItemRef:
    def __init__(self, item_name):
        self.item_name = item_name

    def __repr__(self):
        return f'ItemRef({self.item_name!r})'

class ExitNode:
    def __init__(self, direction, target, condition=None):
        self.direction = direction  # 'north' / 'south' etc.
        self.target    = target     # room name string
        self.condition = condition  # ConditionNode or None

    def __repr__(self):
        return f'ExitNode({self.direction} -> {self.target!r}, requires={self.condition})'

class OnEnterBlock:
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f'OnEnterBlock({self.statements})'

class PuzzleNode:
    def __init__(self, condition, unlock_flag):
        self.condition   = condition    # ConditionNode
        self.unlock_flag = unlock_flag  # string

    def __repr__(self):
        return f'PuzzleNode(requires={self.condition}, unlock={self.unlock_flag!r})'

class ConditionFlag:
    def __init__(self, flag_name):
        self.flag_name = flag_name

    def __repr__(self):
        return f'ConditionFlag({self.flag_name!r})'

class ConditionInv:
    def __init__(self, item_name):
        self.item_name = item_name

    def __repr__(self):
        return f'ConditionInv(has {self.item_name!r})'

class SayStmt:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return f'SayStmt({self.text!r})'

class WinStmt:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return f'WinStmt({self.text!r})'

class LoseStmt:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return f'LoseStmt({self.text!r})'