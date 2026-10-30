"""Executed inside the judge container, never on the API host for student input."""
import ast
import builtins
import json
import sys

CASES = (0, 1, 2, 8, 20)
SAFE_BUILTINS = {name: getattr(builtins, name) for name in (
    'range', 'len', 'list', 'tuple', 'enumerate', 'zip', 'min', 'max', 'abs', 'sum', 'reversed',
)}


def failure(message):
    return {'score': 0, 'passed': False, 'feedback': message,
            'breakdown': {'correctness': 0, 'implementation': 0}, 'tests': []}


def expected(n):
    values = []
    a, b = 0, 1
    for _ in range(n):
        values.append(a)
        a, b = b, a + b
    return values


def validate(tree):
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(tree.body) != 1 or len(functions) != 1 or functions[0].name != 'fibonacci':
        raise ValueError('Submit just one function: def fibonacci(n). No imports or top-level statements.')
    function = functions[0]
    args = function.args
    if (len(args.args) != 1 or args.args[0].arg != 'n' or args.posonlyargs or
            args.kwonlyargs or args.vararg or args.kwarg or args.defaults or
            function.decorator_list or function.returns or args.args[0].annotation):
        raise ValueError('Use the exact signature def fibonacci(n): without annotations or decorators.')
    forbidden = (ast.Import, ast.ImportFrom, ast.ClassDef, ast.AsyncFunctionDef,
                 ast.Lambda, ast.Global, ast.Nonlocal, ast.With, ast.AsyncWith,
                 ast.Try, ast.Raise, ast.Delete, ast.Yield, ast.YieldFrom, ast.Await)
    for node in ast.walk(function):
        if isinstance(node, forbidden) or (isinstance(node, ast.FunctionDef) and node is not function):
            raise ValueError('Use a simple iterative function without imports, nested functions or exception handling.')
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id in SAFE_BUILTINS:
            raise ValueError('Do not reassign built-in function names such as list or range.')
        if isinstance(node, ast.Name) and node.id.startswith('_') and node.id != '_':
            raise ValueError('Private and special names are not available in this exercise.')
        if isinstance(node, ast.Attribute) and node.attr not in ('append', 'extend'):
            raise ValueError('Only list append() and extend() methods are available in this exercise.')
        if isinstance(node, ast.Call):
            allowed = ((isinstance(node.func, ast.Name) and node.func.id in SAFE_BUILTINS) or
                       (isinstance(node.func, ast.Attribute) and node.func.attr in ('append', 'extend')))
            if not allowed:
                raise ValueError('Use loops and list operations; recursion and other function calls are not allowed.')
    return any(isinstance(node, (ast.For, ast.While, ast.ListComp)) for node in ast.walk(function))


def grade(code):
    try:
        tree = ast.parse(code)
        has_loop = validate(tree)
        scope = {'__builtins__': SAFE_BUILTINS.copy()}
        exec(compile(tree, '<submission>', 'exec'), scope)
    except SyntaxError as error:
        return failure(f'SyntaxError on line {error.lineno}: {error.msg}')
    except Exception as error:
        return failure(str(error))
    tests = []
    for n in CASES:
        wanted = expected(n)
        row = {'input': n, 'expected': wanted, 'actual': None, 'passed': False, 'error': None}
        try:
            # Fresh globals for every case, so tests cannot share mutable state.
            scope = {'__builtins__': SAFE_BUILTINS.copy()}
            exec(compile(tree, '<submission>', 'exec'), scope)
            actual = scope['fibonacci'](n)
            valid = type(actual) is list and len(actual) <= 100 and all(type(x) is int and x.bit_length() <= 256 for x in actual)
            if valid:
                row['actual'] = actual
                row['passed'] = actual == wanted
            else:
                row['error'] = 'Return a list containing the first n integer Fibonacci terms.'
        except Exception as error:
            row['error'] = f'{type(error).__name__}: {str(error)[:200]}'
        tests.append(row)
    correctness = 8 * sum(row['passed'] for row in tests)
    implementation = 10 if has_loop else 0
    passed = correctness == 40 and has_loop
    feedback = ('All output tests passed. Explain one state update to the TA.' if passed else
                'Use a for/while loop or list comprehension.' if not has_loop else
                'Check the failed cases below, including the empty list at n=0.')
    return {'score': correctness + implementation, 'passed': passed, 'feedback': feedback,
            'breakdown': {'correctness': correctness, 'implementation': implementation}, 'tests': tests}


if __name__ == '__main__':
    try:
        payload = json.load(sys.stdin)
        print(json.dumps(grade(payload['code'])))
    except Exception:
        print(json.dumps(failure('The judge could not process this submission.')))
