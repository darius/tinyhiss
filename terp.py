"""
AST interpreter
"""

from collections import namedtuple
import itertools

from core import call, class_from_type

class Thing(namedtuple('_Thing', 'class_ data')):
    def get(self, key):
        return self.data[self.class_.slot_index[key]]
    def put(self, key, value):
        self.data[self.class_.slot_index[key]] = value
    def __repr__(self):
        return '%r(%s)' % (self.class_,
                           ', '.join(map(repr, self.data)))

class Class(namedtuple('_Class', 'methods slots')):
    class_ = None  # (stub, filled in below)
    def __init__(self, methods, slots):
        self.slot_index = dict(zip(slots, range(len(slots))))
    def get_method(self, selector):
        try:
            return self.methods[selector]
        except KeyError:
            assert False, "Unknown method: %r" % (selector,)
    def put_method(self, selector, method):
        self.methods[selector] = method
    def make(self):
        return Thing(self, [None] * len(self.slots))
    def next_method(self, selector, reverse=False):
        if selector not in self.methods:
            name = min(self.methods or (None,))
        else:
            keys = sorted(self.methods.keys())
            if reverse: keys.reverse()
            name = cyclic_next(selector, keys)
        return (None, None) if name is None else (name, self.methods[name])
    def __repr__(self):
        name = global_env.find_value(self)
        if name is not None: return name
        return '<<Class %s | %s>>' % (' '.join(self.slots),
                                      self.methods)

def new_method(receiver, arguments, k):
    return k, receiver.make()

Class.class_ = Class(dict(new=new_method), ())

def cyclic_next(key, lot):
    it = itertools.cycle(lot)
    for x in it:
        if key == x:
            result = next(it)
            return result
        
def make_method(params, locals, expr, source=None):
    return Method(source, Code(params, locals, expr))

class Method(namedtuple('_Method', 'source code')):
    def __call__(self, receiver, arguments, k):
        return self.code.enter(receiver, arguments, None, k)
    def __repr__(self):
        return repr(self.code)

block_methods = {
    'value':  lambda receiver, arguments, k: receiver.enter(arguments, k),
    'value:': lambda receiver, arguments, k: receiver.enter(arguments, k),
}
block_class = Class(block_methods, ())

class Block(namedtuple('_Block', 'me env code')):
    class_ = block_class
    def enter(self, arguments, k):
        return self.code.enter(self.me, arguments, self.env, k)
    def __repr__(self):
        return 'Block(%r, %r, %r)' % (self.me, self.env, self.code)

class Env(namedtuple('_Env', 'rib container')):
    # The following two methods are meant only for the global env and
    # the workspace:
    def adjoin(self, key, value):
        self.rib[key] = value
    def enter(self, key, default): # XXX rename this method
        try:
            return self.get(key)
        except KeyError:
            result = self.rib[key] = default
            return result
    def get(self, key):
        return self.find(key)[key]
    def put(self, key, value):
        self.find(key)[key] = value
    def find(self, key):
        if key in self.rib:
            return self.rib
        elif self.container is not None:
            return self.container.find(key)
        else:
            raise KeyError(key)
    def find_value(self, value):
        for k, v in self.rib.items():
            if value is v:
                return k
        if self.container is None:
            return None
        else:
            return self.container.find_value(value)
    def __repr__(self):
        return 'Env(%r, %r)' % (self.rib, self.container)

num_types = (int, long, float)

def as_number(thing):
    if isinstance(thing, num_types):
        return thing
    assert False, "Not a number: %r" % (thing,)

num_methods = {
    '+': lambda rcvr, (other,), k: (k, rcvr + as_number(other)),
    '*': lambda rcvr, (other,), k: (k, rcvr * as_number(other)),
    '-': lambda rcvr, (other,), k: (k, rcvr - as_number(other)),
    '=': lambda rcvr, (other,), k: (k, rcvr == other), # XXX object method
    '<': lambda rcvr, (other,), k: (k, rcvr < other),
}
num_class = Class(num_methods, ())
for nt in num_types:
    class_from_type[nt] = num_class

def find_default(rcvr, (other, default), k):
    try:
        return k, rcvr.index(other)
    except ValueError:
        return call(default, 'value', (), k)

def has(rcvr, (other,), k):  return (k, other in rcvr)
def at(rcvr, (i,), k):       return (k, rcvr[i])
def find(rcvr, (other,), k): return (k, rcvr.index(other))
def size(rcvr, _, k):        return (k, len(rcvr))
def add(rcvr, (other,), k):  return (k, rcvr + other)
def eq(rcvr, (other,), k):   return (k, rcvr == other)
def lt(rcvr, (other,), k):   return (k, rcvr < other)

str_types = (str, unicode)

def as_string(thing):           # TODO not used?
    if isinstance(thing, str_types):
        return thing
    assert False, "Not a string: %r" % (thing,)

string_methods = {
    'has:':  has,
    'at:':   at,
    'find:': find,
    'find:default:': find_default,
    'size':  size,
    '++':    add,
    '=':     eq,
    '<':     lt,
}
string_class = Class(string_methods, ())
class_from_type[str] = string_class
class_from_type[unicode] = string_class

def array_append(receiver, (arg,), k):
    receiver.append(arg)
    return k, None

array_methods = {
    'has:':  has,
    'at:':   at,
    'find:': find,
    'find:default:': find_default,
    'size':  size,
    '++':    add,
    '=':     eq,
    '<':     lt,
    'append:': array_append,
}
array_class = Class(array_methods, ())
class_from_type[list] = array_class

nil_methods = {}
nil_class = Class(nil_methods, ())
class_from_type[type(None)] = nil_class

class Self(namedtuple('_Self', '')):
    def eval(self, me, env, k):
        return k, me
    def __repr__(self):
        return 'I'

class Constant(namedtuple('_Constant', 'value')):
    def eval(self, me, env, k):
        return k, self.value
    def __repr__(self):
        return repr(self.value)

class Code(namedtuple('_Code', 'params locals expr')):
    def eval(self, me, env, k):
        return k, Block(me, env, self)
    def enter(self, me, arguments, parent_env, k):
        rib = dict(zip(self.params, arguments))
        for name in self.locals:
            rib[name] = None
        return self.expr.eval(me, Env(rib, parent_env), k)
    def __repr__(self):
        params = ' '.join(':'+param for param in self.params)
        if params: params += ' | '
        locs = ' '.join(self.locals)
        if locs: locs = '|%s| ' % locs
        return '{%s%s%r}' % (params, locs, self.expr)

def with_key(key, thunk):
    try: return thunk()
    except KeyError:
        raise Exception("Unbound", key)

class GlobalGet(namedtuple('_GlobalGet', 'name')):
    def eval(self, me, env, k):
        return with_key(self.name, lambda: (k, global_env.get(self.name)))
    def __repr__(self):
        return str(self.name)

class LocalGet(namedtuple('_LocalGet', 'name')):
    def eval(self, me, env, k):
        return with_key(self.name, lambda: (k, env.get(self.name)))
    def __repr__(self):
        return str(self.name)

class LocalPut(namedtuple('_LocalPut', 'name expr')):
    def eval(self, me, env, k):
        return self.expr.eval(me, env, (putting_k, (self.name, env), k))
    def __repr__(self):
        return '%s <- %r' % (self.name, self.expr)

def putting_k(value, (name, thing), k):
    with_key(name, lambda: thing.put(name, value))
    return k, value

class SlotGet(namedtuple('_SlotGet', 'name')):
    def eval(self, me, env, k):
        return with_key(self.name,
                        lambda: (k, as_slottable(me).get(self.name)))
    def __repr__(self):
        return 'my ' + str(self.name)

class SlotPut(namedtuple('_SlotPut', 'name expr')):
    def eval(self, me, env, k):
        return self.expr.eval(me, env,
                              (putting_k, (self.name, as_slottable(me)), k))
    def __repr__(self):
        return 'my %s <- %r' % (self.name, self.expr)

def as_slottable(thing):
    if not isinstance(thing, Thing):
        raise KeyError
    return thing
    
global_env = Env({}, None)

class Cascade(namedtuple('_Cascade', 'subject selector operands')):
    def eval(self, me, env, k):
        return self.subject.eval(me, env,
                                 (cascade_evrands_k, (self, me, env), k))
    def __repr__(self):
        return send_repr(self, ';')

def cascade_evrands_k(subject, (cascade, me, env), k):
    return evrands(cascade.operands, me, env,
                   (call_k, (subject, cascade),
                    (ignore_k, subject, k)))

def ignore_k(_, result, k):
    return k, result

class Send(namedtuple('_Send', 'subject selector operands')):
    def eval(self, me, env, k):
        return self.subject.eval(me, env,
                                 (evrands_k, (self, me, env), k))
    def __repr__(self):
        return send_repr(self)

def send_repr(self, sep=''):
    subject = repr(self.subject) + sep
    if len(self.operands) == 0:
        return '(%s %s)' % (subject, self.selector)
    elif len(self.operands) == 1:
        return '(%s %s %r)' % (subject, self.selector, self.operands[0])
    else:
        pairs = zip(self.selector.split(':'), self.operands)
        return '(%s%s)' % (subject, ''.join(' %s: %r' % pair for pair in pairs))

def evrands_k(subject, (send, me, env), k):
    return evrands(send.operands, me, env,
                   (call_k, (subject, send), k))

def call_k(args, (subject, send_or_cascade), k):
    return call(subject, send_or_cascade.selector, args, k)

def evrands(operands, me, env, k):
    if not operands:
        return k, ()
    else:
        return operands[0].eval(me, env,
                                (evrands_more_k, (operands[1:], me, env), k))

def evrands_more_k(val, (operands, me, env), k):
    return evrands(operands, me, env, (evrands_cons_k, val, k))

def evrands_cons_k(vals, val, k):
    return k, (val,)+vals

class Then(namedtuple('_Then', 'expr1 expr2')):
    def eval(self, me, env, k):
        return self.expr1.eval(me, env, (then_k, (self, me, env), k))
    def __repr__(self):
        return '%r. %r' % (self.expr1, self.expr2)

def then_k(_, (then_, me, env), k):
    return then_.expr2.eval(me, env, k)

def MakeArray(exprs):
    subject = Send(GlobalGet('Make-array'), 'empty', ())
    for e in exprs:
        subject = Cascade(subject, 'append:', (e,))
    return subject

def make_array_empty_method(receiver, arguments, k): return k, []
make_array_class = Class({'empty': make_array_empty_method},
                         ())
global_env.adjoin('Make-array', Thing(make_array_class, ()))

true_class = Class({}, ())   # Filled in at startup
false_class = Class({}, ())  # ditto



#global_env.adjoin('Object', thing_class)
global_env.adjoin('Class',  Class.class_)
global_env.adjoin('Block',  block_class)
global_env.adjoin('Number', num_class)
global_env.adjoin('String', string_class)
global_env.adjoin('False',  false_class)
global_env.adjoin('True',   true_class)
global_env.adjoin('Array',  array_class)

final_k = None
