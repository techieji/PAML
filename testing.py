import sys
from functools import reduce
import io

class StreamReplaceWrapper(io.TextIOWrapper):
    def __init__(self, stream, d={}):
        super().__init__(stream)
        self.d = d

    def write(self, _s):
        s = reduce(lambda x, y: x.replace(y[0], y[1]), self.d.items(), _s)
        print(s)
        super().write(s)

sys.stdout = StreamReplaceWrapper(sys.__stdout__, {'e': '!e!'})

sys.stdout.write('test')
