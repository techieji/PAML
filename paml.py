from lark import Lark, Transformer, ast_utils, Tree, Token
from collections import ChainMap
from dataclasses import dataclass
from pprint import pprint
from argparse import ArgumentParser
import itertools as it, operator as op, math, json, platform

__version__ = '0.2.4'

parser = Lark(r"""
_seperated{elem, sep}: [ elem (sep elem)* ]
start: (extern_expr | assignment)*

extern_expr: "::" expr
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
""", propagate_positions=True)

class AttrDict(dict):
    __init__ = lambda self, d: super().__init__(dict(zip(map(str, d.keys()), d.values())))
    __getattr__ = lambda self, k: self[k]

FILE_CONTENT = ''
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

class FunctionTransformer(Transformer):
    def make_func(self, v):
        *args, tree = v
        return (lambda env, *a: complete_transform(tree, env.new_child(dict(zip(args, a)))))

    def if_expr(self, v):
        _cond, e1, e2 = v
        return Tree('compiled_if_expr', [lambda env: complete_transform(e1 if complete_transform(_cond, env) else e2, env)])

    def extern_expr(self, v):
        tree, = v
        return Tree('compiled_extern_expr', [lambda env: [print(":: " + FILE_CONTENT[tree.meta.start_pos:tree.meta.end_pos]), complete_transform(tree, env)][1]])

    def map(self, v):
        tree, = v
        return Tree('compiled_map', [lambda env: AttrDict(complete_transform(tree, env.new_child()))])

class PAMLTransformer(Transformer):
    def __init__(self, env):
        super().__init__()
        self.env = env

    def start(self, v):
        return self.env.maps[0]

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
        return getattr(obj, method)

    def func_call(self, v):
        e, *a = v
        if 'env' in e.__code__.co_varnames:     # Hacky, but who cares when brevity is on the line?
            return e(self.env, *a)
        else:
            return e(*a)

    def get_var(self, v):
        return self.env[v[0]]

def complete_transform(t, env):
    return PAMLTransformer(env).transform(FunctionTransformer().transform(t))

def run_str(s, env):
    return complete_transform(parser.parse(s), env)

def import_module(filename):
    global FILE_CONTENT
    with open(filename) as f:
        FILE_CONTENT = f.read()
    return AttrDict(run_str(FILE_CONTENT, ENV))

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

def repl(env=ENV):   # TODO: UNSTABLE, FIX
    print(f'Welcome to PAML {__version__}!\nType :h for help or :q to exit.')
    while True:
        s = input('> ')
        if s[0] == ':':
            if s[1] == 'q': break
            elif s[1] == 'h': print('Commands: :q (exit), :h (help), :e (print environment)')
            elif s[1] == 'e': pprint(env)
        else:
            while not s.endswith(';;'):
                s += input('  ')
            s = s[:-2]
            try:
                res = run_str(s, env)
            except:
                res = run_str(':: ' + s, env)
            env['_'] = res
            pprint(res)
        s = ''

# Testing code

n = 5
FILE = f'test/test{n}.paml'

def tester():
    sample_code = open(FILE).read()
    print(sample_code)
    parsed = parser.parse(sample_code)
    print(parsed.pretty())
    # res = PAMLTransformer(ENV).transform(FunctionTransformer().transform(parsed))
    res = AttrDict(complete_transform(parsed, ENV))
    print(res)

def main():
    argparser = ArgumentParser()
    argparser.add_argument('filename')
    argparser.add_argument('--to-json')

if __name__ == '__main__':
    # tester()
    # run_file(FILE)
    repl()
