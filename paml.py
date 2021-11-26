from lark import Lark, Transformer, ast_utils, Tree, Token
from collections import ChainMap
from dataclasses import dataclass
from pprint import pprint
from argparse import ArgumentParser
import itertools as it
import operator as op
import math
import json

parser = Lark(r"""
_seperated{elem, sep}: [ elem (sep elem)* ]
start: (extern_expr | assignment)*

?extern_expr: "::" expr
?expr: literal
    | method
    | expr "(" _seperated{expr, ","} ")"                    -> func_call
    | "if" expr "then" expr "else" expr "endif"             -> if_expr
    | map
    | NAME                                                  -> get_var
    | "(" expr ")"
    | "fn" _seperated{NAME, ","} "->" expr "endfn"          -> make_func

literal: STRING
       | NUMBER

method: expr "." NAME
assignment: NAME "=" expr
map: "{" start "}"

COMMENT: /#.*/
%import common.CNAME                                        -> NAME
%import common.ESCAPED_STRING                               -> STRING
%import common.SIGNED_NUMBER                                -> NUMBER
%import common.WS
%ignore WS
%ignore COMMENT
""")

def cleanup_ret(d):
    return dict(zip(map(str, d.keys()), d.values()))

class AttrDict(dict):
    def __init__(self, d):
        super().__init__(cleanup_ret(d))

    def __getattr__(self, k):
        return self[k]

ENV = ChainMap({}, {
    'true': True,
    'false': False,
    'builtins': AttrDict({
        'concat': lambda x, y: x + y,
        'trace': lambda x, y="": [print(x), y][1],
        'format': lambda s, *a: s.format(*a),
        **vars(op)
    }),
    'math': AttrDict({
        **vars(math)
    })
})

class Function:
    def __init__(self, args, tree):
        self.args = args
        self.tree = tree

    def __call__(self, env, *a):
        res = complete_transform(self.tree, env.new_child(dict(zip(self.args, a))))
        return res

class CompiledIfExpr:
    def __init__(self, cond, e1, e2):
        self.cond = cond
        self.e1 = e1
        self.e2 = e2

    def __call__(self, env):
        cond = complete_transform(self.cond, env)
        return complete_transform(self.e1 if cond else self.e2, env)

class CompiledMap:
    def __init__(self, tree):
        self.tree = tree

    def __call__(self, env):
        return AttrDict(complete_transform(self.tree, env.new_child()))

class FunctionTransformer(Transformer):
    def make_func(self, v):
        *a, e = v
        return Function(a, e)

    def if_expr(self, v):
        _cond, e1, e2 = v
        return Tree('compiled_if_expr', [CompiledIfExpr(_cond, e1, e2)])

    def map(self, v):
        tree, = v
        return Tree('compiled_map', [CompiledMap(tree)])

class PAMLTransformer(Transformer):
    def __init__(self, env):
        super().__init__()
        self.env = env

    def start(self, v):
        return self.env.maps[0]

    def compiled_if_expr(self, v):
        if_expr, = v
        return if_expr(self.env)

    def compiled_map(self, v):
        let_expr, = v
        return let_expr(self.env)

    def assignment(self, v):
        name, e = v
        self.env[name] = e

    def literal(self, v):
        return eval(v[0])

    def method(self, v):
        obj, method = v
        return getattr(obj, method)

    def func_call(self, v):
        e, *a = v
        if type(e) == Function:
            return e(self.env, *a)
        else:
            return e(*a)

    def get_var(self, v):
        name, = v
        return self.env[name]

    def map(self, v):
        return AttrDict(zip(v[::2], vp[1::2]))


def complete_transform(t, env):
    return PAMLTransformer(env).transform(FunctionTransformer().transform(t))

def import_module(filename):
    with open(filename) as f:
        return AttrDict(cleanup_ret(complete_transform(parser.parse(f.read()), ENV)))

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

n = 5
FILE = f'test/test{n}.paml'

def tester():
    sample_code = open(FILE).read()
    print(sample_code)
    parsed = parser.parse(sample_code)
    print(parsed.pretty())
    res = PAMLTransformer(ENV).transform(FunctionTransformer().transform(parsed))
    print(res)

def main():
    argparser = ArgumentParser()
    argparser.add_argument('filename')
    argparser.add_argument('--to-json')

if __name__ == '__main__':
    with open(FILE) as f:
        print(f.read())
    to_json(import_module(FILE), f'outputs/test{n}.json')
