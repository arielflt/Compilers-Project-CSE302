# --------------------------------------------------------------------
import contextlib as cl
import typing as tp

from .bxerrors import Reporter
from .bxast    import *
from .bxscope  import Scope

# ====================================================================
SigType    = tuple[tuple[BasicBXType], Opt[BasicBXType]]
ProcSigMap = dict[str, SigType]

# --------------------------------------------------------------------
class PreTyper:
    def __init__(self, reporter : Reporter):
        self.reporter = reporter

    def pretype(self, prgm : Program) -> tuple[Scope, ProcSigMap]:
        scope = Scope()
        procs = dict()

        for topdecl in prgm:
            match topdecl:
                case ProcDecl(name, arguments, rettype, body):
                    if name.value in procs:
                        self.reporter(
                            f'duplicated procedure name: {name.value}',
                            position = name.position
                        )
                        continue

                    procs[name.value] = (
                        tuple(x[1] for x in arguments),
                        BasicBXType.VOID if rettype is None else rettype
                    )

                case GlobVarDecl(name, init, type_):
                    if name.value in scope:
                        self.reporter(
                            f'duplicated global variable name: {name.value}',
                            position = name.position
                        )
                        continue

                    scope.push(name.value, type_)

                case _:
                    assert(False)

        if 'main' not in procs:
            self.reporter('this program is missing a main subroutine')
        elif procs['main'] != ((), BasicBXType.VOID):
            self.reporter(
                '"main" should not take any argument and should not return any value'
            )

        return scope, procs

# --------------------------------------------------------------------
class TypeChecker:
    B : BasicBXType = BasicBXType.BOOL
    I : BasicBXType = BasicBXType.INT

    SIGS = {
        'opposite'                 : ([I   ], I),
        'bitwise-negation'         : ([B   ], B),
        'boolean-not'              : ([B   ], B),
        'addition'                 : ([I, I], I),
        'subtraction'              : ([I, I], I),
        'multiplication'           : ([I, I], I),
        'division'                 : ([I, I], I),
        'modulus'                  : ([I, I], I),
        'logical-right-shift'      : ([I, I], I),
        'logical-left-shift'       : ([I, I], I),
        'bitwise-and'              : ([I, I], I),
        'bitwise-or'               : ([I, I], I),
        'bitwise-xor'              : ([I, I], I),
        'boolean-and'              : ([B, B], B),
        'boolean-or'               : ([B, B], B),
        'cmp-equal'                : ([I, I], B),
        'cmp-not-equal'            : ([I, I], B),
        'cmp-lower-than'           : ([I, I], B),
        'cmp-lower-or-equal-than'  : ([I, I], B),
        'cmp-greater-than'         : ([I, I], B),
        'cmp-greater-or-equal-than': ([I, I], B),
    }

    def __init__(self, scope : Scope, procs : ProcSigMap, reporter : Reporter):
        self.scope    = scope
        self.procs    = procs
        self.loops    = 0
        self.proc     = None
        self.reporter = reporter

    def report(self, msg: str, position: Opt[Range] = None):
        self.reporter(msg, position = position)

    @cl.contextmanager
    def in_loop(self):
        self.loops += 1
        try:
            yield self
        finally:
            self.loops -= 1

    @cl.contextmanager
    def in_proc(self, proc: ProcDecl):
        assert(self.proc is None)

        self.proc = proc
        self.scope.open()
        try:
            yield self
        finally:
            self.proc = None
            self.scope.close()

    def check_local_free(self, name : Name):
        if self.scope.islocal(name.value):
            self.report(f'duplicated variable declaration for {name.value}')
            return False
        return True

    def check_local_bound(self, name : Name):
        if name.value not in self.scope:
            self.report(
                f'missing variable declaration for {name.value}',
                position = name.position,
            )
            return None
        return self.scope[name.value]

    def check_integer_constant_range(self, value : int):
        if value not in range(-(1 << 63), 1 << 63):
            self.report(f'integer literal out of range: {value}')
            return False
        return True

    def for_expression(self, expr : Expression, etype : tp.Optional[Type] = None):
        type_ = None

        match expr:
            case VarExpression(name):
                if self.check_local_bound(name):
                    type_ = self.scope[name.value]

            case BoolExpression(_):
                type_ = BasicBXType.BOOL

            case IntExpression(value):
                self.check_integer_constant_range(value)
                type_ = BasicBXType.INT

            case OpAppExpression(opname, arguments):
                opsig = self.SIGS[opname]
                for atype, argument in zip(opsig[0], arguments):
                    self.for_expression(argument, etype = atype)
                type_ = opsig[1]

            case CallExpression(name, arguments):
                atypes, retty = [], None

                if name.value not in self.procs:
                    self.report(
                        f'unknown procedure: {name.value}',
                        position = name.position,
                    )
                else:
                    atypes, retty = self.procs[name.value]

                    if len(atypes) != len(arguments):
                        self.report(
                            f'invalid number of arguments: expected {len(atypes)}, got {len(arguments)}',
                            position = expr.position,
                        )

                for i, a in enumerate(arguments):
                    self.for_expression(a, atypes[i] if i in range(len(atypes)) else None)

                type_ = retty

            case PrintExpression(e):
                self.for_expression(e);

                if e.type_ is not None:
                    if e.type_ not in (BasicBXType.INT, BasicBXType.BOOL):
                        self.report(
                            f'can only print integers and booleans, not {e.type_}',
                            position = e.position,
                        )

                type_ = BasicBXType.VOID

            case AllocExpression(element_type, size_expr):
                self.for_expression(size_expr, etype=Type.INT)
                type_ = Type.POINTER_INT if element_type == Type.INT else Type.POINTER_BOOL

            case DereferenceExpression(pointer_expr):
                self.for_expression(pointer_expr)
                if pointer_expr.type_ not in [Type.POINTER_INT, Type.POINTER_BOOL]:
                    self.report("Dereference of non-pointer type", position=pointer_expr.position)
                else:
                    type_ = Type.INT if pointer_expr.type_ == Type.POINTER_INT else Type.BOOL

                    
            case IndexExpression(array_expr, index_expr):
                self.for_expression(array_expr)
                self.for_expression(index_expr, etype=Type.INT)
                if array_expr.type_ not in [Type.POINTER_INT, Type.POINTER_BOOL, Type.ARRAY_INT, Type.ARRAY_BOOL]:
                    self.report("Indexing on non-array and non-pointer type", position=array_expr.position)
                else:
                    # The type is int or bool based on the array/pointer type
                    type_ = Type.INT if array_expr.type_ in [Type.POINTER_INT, Type.ARRAY_INT] else Type.BOOL

            case _:
                print(expr)
                assert(False)

        if type_ is not None:
            if etype is not None:
                if type_ != etype:
                    self.report(
                        f'invalid type: get {type_}, expected {etype}',
                        position = expr.position,
                    )

        expr.type_ = type_

    def for_statement(self, stmt : Statement):
        match stmt:
            case VarDeclStatement(name, init, type_):
                if self.check_local_free(name):
                    self.scope.push(name.value, type_)
                self.for_expression(init, etype = type_)

            case AssignStatement(lhs, rhs):
                lhstype = self.check_local_bound(lhs)
                self.for_expression(rhs, etype = lhstype)

            case ExprStatement(expression):
                self.for_expression(expression)

            case BlockStatement(block):
                self.for_block(block)

            case IfStatement(condition, iftrue, iffalse):
                self.for_expression(condition, etype = BasicBXType.BOOL)
                self.for_statement(iftrue)
                if iffalse is not None:
                    self.for_statement(iffalse)

            case WhileStatement(condition, body):
                self.for_expression(condition, etype = BasicBXType.BOOL)
                with self.in_loop():
                    self.for_statement(body)

            case BreakStatement() | ContinueStatement():
                if self.loops == 0:
                    self.report(
                        'break/continue statement outside of a loop',
                        position = stmt.position,
                    )

            case PrintStatement(init):
                self.for_expression(init, etype = BasicBXType.INT)

            case ReturnStatement(e):
                if e is None:
                    if self.proc.rettype is not None:
                        self.report(
                            'value-less return statement in a function',
                            position = stmt.position,
                        )
                    self.for_expression(e, etype = self.proc.retty)
                else:
                    if self.proc.rettype is None:
                        self.report(
                            'return statement in a subroutine',
                            position = stmt.position,
                        )

            case _:
                print(stmt)
                assert(False)

    def for_block(self, block : Block):
        with self.scope.in_subscope():
            for stmt in block:
                self.for_statement(stmt)

    def for_topdecl(self, decl : TopDecl):
        match decl:
            case ProcDecl(name, arguments, retty, body):
                with self.in_proc(decl):
                    for vname, vtype_ in arguments:
                        if self.check_local_free(vname):
                            self.scope.push(vname.value, vtype_)
                    self.for_statement(body)

                    if retty is not None:
                        if not self.has_return(body):
                            self.report(
                                'this function is missing a return statement',
                                position = decl.position,
                            )

            case GlobVarDecl(name, init, type_):
                self.for_expression(init, etype = type_)

                if not self.check_constant(init):
                    self.report(
                        'this expression is not a literal',
                        position = init.position,
                    )

    def for_program(self, prgm : Program):
        for decl in prgm:
            self.for_topdecl(decl)

    def check_constant(self, expr: Expression):
        match expr:
            case IntExpression(_):
                return True

            case _:
                return False

    def has_return(self, stmt: Statement):
        match stmt:
            case ReturnStatement(_):
                return True

            case IfStatement(_, iftrue, iffalse):
                return \
                    self.has_return(iftrue) and \
                    self.has_return(iffalse)

            case BlockStatement(block):
                return any(self.has_return(b) for b in block)

            case _:
                return False

    def check(self, prgm : Program):
        self.for_program(prgm)

# --------------------------------------------------------------------
def check(prgm : Program, reporter : Reporter):
    with reporter.checkpoint() as checkpoint:
        scope, procs = PreTyper(reporter).pretype(prgm)
        TypeChecker(scope, procs, reporter).check(prgm)
        return bool(checkpoint)
