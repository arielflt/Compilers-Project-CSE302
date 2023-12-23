# --------------------------------------------------------------------
import dataclasses as dc
import enum
from typing import Optional as Opt, List, Tuple

# ====================================================================
# Parse tree / Abstract Syntax Tree

# --------------------------------------------------------------------
@dc.dataclass
class Range:
    start: tuple[int, int]
    end: tuple[int, int]

    @staticmethod
    def of_position(line: int, column: int):
        return Range((line, column), (line, column+1))

# --------------------------------------------------------------------
@dc.dataclass
class AST:
    position: Opt[Range] = dc.field(kw_only=True, default=None)

# --------------------------------------------------------------------
@dc.dataclass
class Name(AST):
    value: str

# --------------------------------------------------------------------
class Type():
    pass

class BasicBXType(Type, enum.Enum):
    VOID = 0
    BOOL = 1
    INT = 2
    NULL = 3
    POINTER_INT = 4
    POINTER_BOOL = 5
    ARRAY_INT = 6
    ARRAY_BOOL = 7

    def __str__(self):
        match self:
            case self.VOID:
                return 'void'
            case self.INT:
                return 'int'
            case self.BOOL:
                return 'bool'
            case self.NULL:
                return 'null_ptr'
            case self.POINTER_INT:
                return 'pointer_int'
            case self.POINTER_BOOL:
                return 'pointer_bool'
            case self.ARRAY_INT:
                return 'array_int'
            case self.ARRAY_BOOL:
                return 'array_bool'

@dc.dataclass
class PointerType(Type):
    target: Type
    
    def __str__(self):
        return f"{self.target}*"

@dc.dataclass
class ArrayType(Type):
    target: Type
    size: int
    
    def __str__(self):
        return f"{self.target}[{self.size}]"

@dc.dataclass
class StructType(Type):
    attributes: list[Tuple[Name, Type]]
    attr_lookup: Opt[dict[str, Tuple[int, Type]]] = dc.field(kw_only=True, default=None)

    def __str__(self):
        return f"struct"

@dc.dataclass
class StandinType(Type):
    type_name: Name

# --------------------------------------------------------------------
@dc.dataclass
class Expression(AST):
    type_: Opt[Type] = dc.field(kw_only=True, default=None)

# --------------------------------------------------------------------
@dc.dataclass
class VarExpression(Expression):
    name: Name

# --------------------------------------------------------------------
@dc.dataclass
class BoolExpression(Expression):
    value: bool

# --------------------------------------------------------------------
@dc.dataclass
class IntExpression(Expression):
    value: int

@dc.dataclass
class AllocExpression(Expression):
    element_type: Type
    size_expr: Expression

@dc.dataclass
class DereferenceExpression(Expression):
    pointer_expr: Expression

@dc.dataclass
class IndexExpression(Expression):
    array_expr: Expression
    index_expr: Expression


# --------------------------------------------------------------------
@dc.dataclass
class NullExpression(Expression):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class OpAppExpression(Expression):
    operator: str
    arguments: list[Expression]

# --------------------------------------------------------------------
@dc.dataclass
class AllocExpression(Expression):
    alloctype: Type
    size: Expression

# --------------------------------------------------------------------
@dc.dataclass
class CallExpression(Expression):
    proc: Name
    arguments: list[Expression]

# --------------------------------------------------------------------
@dc.dataclass
class PrintExpression(Expression):
    argument: Expression

# --------------------------------------------------------------------
class Assignable(Expression):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class VarAssignable(Assignable):
    name: Name

# --------------------------------------------------------------------
@dc.dataclass
class DerefAssignable(Assignable):
    argument: Assignable

# --------------------------------------------------------------------
@dc.dataclass
class ArrayAssignable(Assignable):
    argument: Assignable
    index: Expression

# --------------------------------------------------------------------
@dc.dataclass
class AttributeAssignable(Assignable):
    argument: Assignable
    attribute: str

# --------------------------------------------------------------------
@dc.dataclass
class AttrPointerAssignable(Assignable):
    argument: Assignable
    attribute: str

# --------------------------------------------------------------------
@dc.dataclass
class RefExpression(Expression):
    argument: Assignable

# --------------------------------------------------------------------
class Statement(AST):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class VarDeclStatement(Statement):
    name: Name
    init: Expression
    type_: Type

# --------------------------------------------------------------------
@dc.dataclass
class AssignStatement(Statement):
    lhs: Assignable
    rhs: Expression

# --------------------------------------------------------------------
@dc.dataclass
class ExprStatement(Statement):
    expression: Expression

# --------------------------------------------------------------------
@dc.dataclass
class PrintStatement(Statement):
    value: Expression

# --------------------------------------------------------------------
@dc.dataclass
class BlockStatement(Statement):
    body: list[Statement]

# --------------------------------------------------------------------
@dc.dataclass
class IfStatement(Statement):
    condition: Expression
    then: Statement
    else_: Opt[Statement] = None

# --------------------------------------------------------------------
@dc.dataclass
class WhileStatement(Statement):
    condition: Expression
    body: Statement

# --------------------------------------------------------------------
@dc.dataclass
class BreakStatement(Statement):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class ContinueStatement(Statement):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class ReturnStatement(Statement):
    expr: Opt[Expression]

# --------------------------------------------------------------------
class TopDecl(AST):
    pass

# --------------------------------------------------------------------
@dc.dataclass
class GlobVarDecl(TopDecl):
    name: Name
    init: Expression
    type_: Type

# --------------------------------------------------------------------
@dc.dataclass
class ProcDecl(TopDecl):
    name: Name
    arguments: list[Tuple[Name, Type]]
    rettype: Opt[Type]
    body: Statement

# --------------------------------------------------------------------
@dc.dataclass
class TypedefDecl(TopDecl):
    alias: Name
    original_type: Type

# --------------------------------------------------------------------
Block = list[Statement]
Program = list[TopDecl]
