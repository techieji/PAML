from lark import Lark, Transformer, ast_utils, Tree, Token
from lark.exceptions import UnexpectedCharacters
from collections import ChainMap
from dataclasses import dataclass
from pprint import pprint
from argparse import ArgumentParser
import itertools as it, operator as op, math, json, platform, sys, functools

__version__ = '0.4.0'
n = 6

code = r"""
_seperated{elem, sep}: [ elem (sep elem)* ]
start: (extern_expr | assignment)*

extern_expr: "::" expr
?expr: literal
    | method
    | expr "(" _seperated{expr, ","} ")"                    -> func_call
    | "if" expr "then" expr "else" expr "endif"             -> if_expr
    | "switch" expr "of" case+ "end"                        -> case_expr
    | map
    | NAME                                                  -> get_var
    | "(" expr ")"
    | "fn" _seperated{NAME, ","} "->" expr "endfn"          -> make_func
    | "[" _seperated{expr, ","} "]"                         -> make_list

literal: STRING
       | NUMBER

method: expr "." NAME
      | expr "." "{" expr "}"

case: expr "->" expr ";"

assignment: NAME "=" expr
          | STRING "=" expr                                 -> py_expr_assignment
          | "<" expr ">" "=" expr                           -> expr_assignment
map: "{" start "}"

COMMENT: /#.*/
%import common.CNAME                                        -> NAME
%import common.ESCAPED_STRING                               -> STRING
%import common.SIGNED_NUMBER                                -> NUMBER
%import common.WS
%ignore WS
%ignore COMMENT
"""

parser = Lark(code, propagate_positions=True)

class AttrDict(dict):
    __init__ = lambda self, d: super().__init__({str(x): y for x, y in d.items()})
    __getattr__ = lambda self, k: self[k]

def _select_from_dict(d, keys):
    return {x: d[x] for x in keys}

NO_RESULT = object()
FILE_CONTENT = ''
PRINT_EXTERN = True
ENV = ChainMap({}, {
    'true': True,
    'false': False,
    'builtins': AttrDict({
        'trace': lambda x, y="": [print(x), y][1],
        'format': lambda s, *a: s.format(*a),
        'replace': lambda s, c, r: s.replace(c, r),
        **_select_from_dict(vars(op), 
            ['add', 'sub', 'mul', 'truediv', 'floordiv', 'getitem', 'concat', 'contains',
             'ge', 'gt', 'le', 'lt', 'eq']),
        'div': op.truediv,
        'getitem': lambda i, l: l[i],
        'zip': lambda *a: list(zip(*a)),
        'inherit': lambda a, b: AttrDict({**a, **b}),
        'get_env': lambda a: AttrDict(ENV)
    }),
    'func': AttrDict({
        'partial': functools.partial,
        # 'rotate': lambda f, n: lambda *a: # TODO: FINISH
    }),
    'platform': platform.uname(),
    'mapping': lambda l: AttrDict(dict(l)),
})

class FunctionTransformer(Transformer):
    def make_func(self, v):
        *args, tree = v
        return Tree('compiled_func', [lambda env, *a: complete_transform(tree, env.new_child(dict(zip(args, a))))])

    def if_expr(self, v):
        _cond, e1, e2 = v
        return Tree('compiled_if_expr', [lambda env: complete_transform(e1 if complete_transform(_cond, env) else e2, env)])

    def case(self, v):
        value, res = v
        return Tree('compiled_case', [lambda env, expected: complete_transform(res, env) if complete_transform(value, env) == expected else NO_RESULT])

    def extern_expr(self, v):
        tree, = v
        if PRINT_EXTERN:
            return Tree('compiled_extern_expr', [lambda env: [print(":: " + FILE_CONTENT[tree.meta.start_pos:tree.meta.end_pos], end="\n> "), complete_transform(tree, env)][1]])
        else:
            return tree

    def map(self, v):
        tree, = v
        return Tree('compiled_map', [lambda env: AttrDict(complete_transform(tree, env.new_child()))])

class PAMLTransformer(Transformer):
    def __init__(self, env):
        super().__init__()
        self.env = env

    def start(self, v):
        return self.env.maps[0]

    def compiled_func(self, v):
        return lambda *a: v[0](self.env, *a)

    def compiled_if_expr(self, v):
        return v[0](self.env)

    def compiled_map(self, v):
        return v[0](self.env)

    def compiled_extern_expr(self, v):
        return v[0](self.env)

    def assignment(self, v):
        self.env[v[0]] = v[1]

    def literal(self, v):
        return eval(v[0])

    def method(self, v):
        obj, method = v
        if method.startswith('_'):
            raise AttributeError(f'{obj}.{method} is private and cannot be accessed.')
        return getattr(obj, method)

    def case_expr(self, v):
        e, *cases = v
        print(f'{e=}, {type(e)=}')
        expected = complete_transform(e, self.env)
        for x in cases:
            res = x.tree[0](self.env, expected)
            if res != NO_RESULT:
                return res

    def func_call(self, v):
        e, *a = v
        return e(*a)

    def get_var(self, v):
        return self.env[v[0]]

    def make_list(self, v):
        return v

def complete_transform(t, env):
    return PAMLTransformer(env).transform(FunctionTransformer().transform(t))

def run_str(s, env):
    return complete_transform(parser.parse(s), env)

def loads(s):
    global FILE_CONTENT
    FILE_CONTENT = s
    return AttrDict(run_str(FILE_CONTENT, ENV))

def load(f):
    return loads(f.read())

def import_module(filename):
    with open(filename) as f:
        return load(f)

def is_json_serializable(o):
    try:
        json.dumps(o)
        return True
    except (TypeError, OverflowError):
        return False

def _to_json(d):
    ret = {}
    for x, y in d.items():
        if isinstance(y, dict):
            ret[x] = _to_json(y)
        else:
            if is_json_serializable(y):
                ret[x] = y
    return ret

def to_json(d, filename=None):
    newd = _to_json(d)
    if filename:
        with open(filename, 'w') as f:
            json.dump(newd, f)
    else:
        return json.dumps(newd)

def run_file(f):
    d = import_module(f)
    print('\n======= DATA =======')
    pprint(d)

def repl(env=ENV):
    global PRINT_EXTERN
    print(f'Welcome to PAML {__version__}!\nType :h for help or :q to exit.')
    expr_parser = Lark(code, start='expr')
    PRINT_EXTERN = False
    while True:
        exc = None
        s = input('> ')
        if s[0] == ':':
            if s[1] == 'q': break
            elif s[1] == 'h': print('Commands: :q (exit), :h (help), :e (print environment)')
            elif s[1] == 'e': pprint(env)
        else:
            try:
                try:
                    res = complete_transform(expr_parser.parse(s), env)
                    env['_'] = res
                    pprint(res)
                except UnexpectedCharacters as e:
                    exc = e
                    run_str(s, env)
            except Exception as new_e:
                print(f'{e}')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        repl()
