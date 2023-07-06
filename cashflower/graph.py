import ast
import inspect

from queue import Queue

from .error import CashflowModelError
from .utils import get_object_by_name


def get_calc_direction(variables):
    """Set calculation direction to irrelevant/forward/backward"""
    # For non-cycle => single variable, for cycle => variables from the cycle
    variable_names = [variable.name for variable in variables]

    visitor = CalcDirectionVisitor(variable_names)
    for variable in variables:
        node = ast.parse(inspect.getsource(variable.func))
        visitor.visit(node)
        variable.calc_direction = visitor.calc_direction

    return None


def get_calls(variable, variables):
    """List variables called by the given variable"""
    variable_names = [variable.name for variable in variables]
    call_visitor = CallVisitor(variable_names)
    node = ast.parse(inspect.getsource(variable.func))
    # print("\n", ast.dump(node, indent=2))
    call_visitor.visit(node)
    call_names = call_visitor.calls
    calls = [get_object_by_name(variables, call_name) for call_name in call_names if call_name != variable.name]
    return calls


def get_predecessors(node, DG):
    """Get predecessors and their predecessors and their..."""
    queue = Queue()
    visited = []

    queue.put(node)
    visited.append(node)

    while not queue.empty():
        node = queue.get()
        for child in DG.predecessors(node):
            if child not in visited:
                queue.put(child)
                visited.append(child)

    return visited


def raise_error_if_incorrect_argument(node):
    if len(node.args) != 1:
        msg = f"Model variable must have one argument. Please review the call of '{node.func.id}'."
        raise CashflowModelError(msg)

    # Model variable can only call t, t+/-x, and x
    arg = node.args[0]
    msg = f"\nPlease review '{node.func.id}'. The argument of a model variable can be only:\n" \
          f"- t,\n" \
          f"- t plus/minus integer (e.g. t+1 or t-12),\n" \
          f"- an integer (e.g. 0 or 12)."

    # The model variable calls a variable
    if isinstance(arg, ast.Name):
        if not arg.id == "t":
            raise CashflowModelError(msg)

    # The model variable calls a constant
    if isinstance(arg, ast.Constant):
        if not isinstance(arg.value, int):
            raise CashflowModelError(msg)

    # The model variable calls an operation
    if isinstance(arg, ast.BinOp):
        check1 = isinstance(arg.left, ast.Name) and arg.left.id == "t"
        check2 = isinstance(arg.op, ast.Add) or isinstance(arg.op, ast.Sub)
        check3 = isinstance(arg.right, ast.Constant) and isinstance(arg.right.value, int)
        if not (check1 and check2 and check3):
            raise CashflowModelError(msg)

    # The model variable calls something else
    if not (isinstance(arg, ast.Name) or isinstance(arg, ast.Constant) or isinstance(arg, ast.BinOp)):
        raise CashflowModelError(msg)


class CallVisitor(ast.NodeVisitor):
    def __init__(self, variable_names):
        self.variable_names = variable_names
        self.calls = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.variable_names:
                raise_error_if_incorrect_argument(node)
                self.calls.append(node.func.id)


class CalcDirectionVisitor(ast.NodeVisitor):
    def __init__(self, variable_names):
        self.variable_names = variable_names
        self.calc_direction = "irrelevant"

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.variable_names:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp):
                    # Does it call t+... or t-...?
                    check1 = isinstance(arg.left, ast.Name) and arg.left.id == "t"
                    check2 = isinstance(arg.op, ast.Add)
                    check3 = isinstance(arg.op, ast.Sub)

                    if check1 and check2:
                        self.calc_direction = "backward"

                    if check1 and check3:
                        self.calc_direction = "forward"
        return None