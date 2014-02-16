"""
AST interpreter
"""

from collections import namedtuple
import itertools

def trampoline(state):
    k, value = state
    while k is not None:
#        traceback((k, value))
        fn, free_var, k = k
        k, value = fn(value, free_var, k)
    return value

def traceback(state):
    k, value = state
    print ':', value
    while k:
        fn, free_var, k = k
        if isinstance(free_var, tuple) and free_var:
            for i, element in enumerate(free_var):
                print '%-18s %r' % (('' if i else fn.__name__), element)
        else:
            print '%-18s %r' % (fn.__name__, free_var)

def call(receiver, selector, args, k):
    return get_class(receiver).get_method(selector)(receiver, args, k)

def get_class(x):
    if   isinstance(x, Thing):     return x.class_
    elif isinstance(x, bool):      return true_class if x else false_class
    elif isinstance(x, num_types): return num_class
    elif isinstance(x, str_types): return string_class # TODO: define
    elif isinstance(x, Block):     return block_class
    elif isinstance(x, Class):     return class_class # TODO: define .class_ on these?
    elif callable(x):              return primitive_method_class # TODO: define this
    elif x is None:                return nil_class # TODO: define
    else:                          assert False

str_types = (str, unicode)
num_types = (int, long, float)

class Thing(namedtuple('_Thing', 'class_ data')):
    def get(self, key):
        return self.data[self.class_.slot_index[key]]
    def put(self, key, value):
        self.data[self.class_.slot_index[key]] = value

class Class(namedtuple('_Class', 'methods slots')):
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
        for k, v in global_env.items():
            if self is v:
                return k
        return '<<Class %s | %s>>' % (' '.join(self.slots),
                                      self.methods)

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

class Block(namedtuple('_Block', 'receiver env code')):
    def enter(self, arguments, k):
        return self.code.enter(self.receiver, arguments, self.env, k)
    def __repr__(self):
        return 'Block(%r, %r, %r)' % (self.receiver, self.env, self.code)

class Env(namedtuple('_Env', 'rib container')):
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
    def __repr__(self):
        return 'Env(%r, %r)' % (self.rib, self.container)

def new_method(receiver, arguments, k):
    return k, receiver.make()

class_class = Class(dict(new=new_method), ())

block_class = Class(dict(value=lambda receiver, arguments, k: receiver.enter((), k)),
                    ())

num_methods = {'+': lambda rcvr, (other,), k: (k, rcvr + as_number(other)),
               '*': lambda rcvr, (other,), k: (k, rcvr * as_number(other)),
               '-': lambda rcvr, (other,), k: (k, rcvr - as_number(other)),
               '=': lambda rcvr, (other,), k: (k, rcvr == other), # XXX object method
               '<': lambda rcvr, (other,), k: (k, rcvr < other),
               }
num_class = Class(num_methods, ())

def as_number(thing):
    if isinstance(thing, num_types):
        return thing
    assert False, "Not a number: %r" % (thing,)

string_methods = {'+': lambda rcvr, (other,), k: (k, rcvr + as_string(other)),
                  '=': lambda rcvr, (other,), k: (k, rcvr == other), # XXX object method
                  '<': lambda rcvr, (other,), k: (k, rcvr < other),
              }
string_class = Class(string_methods, ())

def as_string(thing):
    if isinstance(thing, str_types):
        return thing
    assert False, "Not a string: %r" % (thing,)

class Self(namedtuple('_Self', '')):
    def eval(self, receiver, env, k):
        return k, receiver
    def __repr__(self):
        return 'I'

class Constant(namedtuple('_Constant', 'value')):
    def eval(self, receiver, env, k):
        return k, self.value
    def __repr__(self):
        return repr(self.value)

class Code(namedtuple('_Code', 'params locals expr')):
    def eval(self, receiver, env, k):
        return k, Block(receiver, env, self)
    def enter(self, receiver, arguments, parent_env, k):
        rib = dict(zip(self.params, arguments))
        for name in self.locals:
            rib[name] = None
        return self.expr.eval(receiver, Env(rib, parent_env), k)
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
    def eval(self, receiver, env, k):
        return with_key(self.name, lambda: (k, global_env[self.name]))
    def __repr__(self):
        return str(self.name)

class LocalGet(namedtuple('_LocalGet', 'name')):
    def eval(self, receiver, env, k):
        return with_key(self.name, lambda: (k, env.get(self.name)))
    def __repr__(self):
        return str(self.name)

class LocalPut(namedtuple('_LocalPut', 'name expr')):
    def eval(self, receiver, env, k):
        return self.expr.eval(receiver, env, (putting_k, (self.name, env), k))
    def __repr__(self):
        return '%s <- %r' % (self.name, self.expr)

def putting_k(value, (name, thing), k):
    with_key(name, lambda: thing.put(name, value))
    return k, value

class SlotGet(namedtuple('_SlotGet', 'name')):
    def eval(self, receiver, env, k):
        return with_key(self.name,
                        lambda: (k, as_slottable(receiver).get(self.name)))
    def __repr__(self):
        return 'my ' + str(self.name)

class SlotPut(namedtuple('_SlotPut', 'name expr')):
    def eval(self, receiver, env, k):
        return self.expr.eval(receiver, env,
                              (putting_k, (self.name, as_slottable(receiver)), k))
    def __repr__(self):
        return 'my %s <- %r' % (self.name, self.expr)

def as_slottable(thing):
    if not isinstance(thing, Thing):
        raise KeyError
    return thing
    
global_env = {}

class Cascade(namedtuple('_Cascade', 'subject selector operands')):
    def eval(self, receiver, env, k):
        return self.subject.eval(receiver, env,
                                 (cascade_evrands_k, (self, receiver, env), k))
    def __repr__(self):
        return send_repr(self, ';')

def cascade_evrands_k(subject, (self, receiver, env), k):
    return evrands(self.operands, receiver, env,
                   (call_k, (subject, self),
                    (ignore_k, subject, k)))

def ignore_k(_, result, k):
    return k, result

class Send(namedtuple('_Send', 'subject selector operands')):
    def eval(self, receiver, env, k):
        return self.subject.eval(receiver, env,
                                 (evrands_k, (self, receiver, env), k))
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

def evrands_k(subject, (self, receiver, env), k):
    return evrands(self.operands, receiver, env,
                   (call_k, (subject, self), k))

def call_k(args, (subject, self), k):
    return call(subject, self.selector, args, k)

def evrands(operands, receiver, env, k):
    if not operands:
        return k, ()
    else:
        return operands[0].eval(receiver, env,
                                (evrands_more_k, (operands[1:], receiver, env), k))

def evrands_more_k(val, (operands, receiver, env), k):
    return evrands(operands, receiver, env, (evrands_cons_k, val, k))

def evrands_cons_k(vals, val, k):
    return k, (val,)+vals

class Then(namedtuple('_Then', 'expr1 expr2')):
    def eval(self, receiver, env, k):
        return self.expr1.eval(receiver, env, (then_k, (self, receiver, env), k))
    def __repr__(self):
        return '%r. %r' % (self.expr1, self.expr2)

def then_k(_, (self, receiver, env), k):
    return self.expr2.eval(receiver, env, k)

true_class = Class({'if-so:if-not:': make_method(('true-block', 'false-block'), (),
                                                 Send(LocalGet('true-block'), 'value', ()),
                                                 source="""\
if-so: true-block if-not: false-block
  true-block value""")},
                   ())
false_class = Class({'if-so:if-not:': make_method(('true-block', 'false-block'), (),
                                                  Send(LocalGet('false-block'), 'value', ()),
                                                 source="""\
if-so: true-block if-not: false-block
  false-block value""")},
                    ())

#global_env['Object'] = thing_class
global_env['Class']  = class_class
global_env['Block']  = block_class
global_env['Number'] = num_class
global_env['String'] = string_class
global_env['False']  = false_class
global_env['True']   = true_class

final_k = None


# Testing

smoketest_expr = Send(Constant(2), '+', (Constant(3),))
smoketest = smoketest_expr.eval(None, None, final_k)
## trampoline(smoketest)
#. 5

def make(class_, k):
    return call(class_, 'new', (),
                (make_new_k, None, k))

def make_new_k(instance, _, k):
    return call(instance, 'init', (),
                (ignore_k, instance, k))

object_init = make_method((), (), Self())

eg_init_with = make_method(('value',), (), SlotPut('whee', LocalGet('value')))
eg_get_whee = make_method((), (), SlotGet('whee'))
eg_yay_body = Send(Send(Self(), 'get_whee', ()), '+', (LocalGet('x'),))
eg_yay = make_method(('x',), ('v',), eg_yay_body)
eg_class = Class(dict(yay=eg_yay,
                      get_whee=eg_get_whee,
                      init_with=eg_init_with),
                 ('whee',))
def eg_init_with_k(instance, _, k):
    return call(instance, 'init_with', (42,),
                (ignore_k, instance, k))
eg = call(eg_class, 'new', (),
          (eg_init_with_k, None, final_k))
eg = trampoline(eg)
eg_result = call(eg, 'yay', (137,), final_k)
## trampoline(eg_result)
#. 179

make_eg = make_method((), (),
                      Send(Cascade(Send(Constant(eg_class), 'new', ()),
                                   'init_with', (Constant(42),)),
                           'yay', (Constant(137),)))
make_eg_result = make_eg(None, (), final_k)
## trampoline(make_eg_result)
#. 179

# TODO: make this a method on Number
factorial_body = Send(Send(LocalGet('n'), '=', (Constant(0),)),
                      'if-so:if-not:',
                      (Code((), (), Constant(1)),
                       Code((), (),
                            # n * (self factorial: (n - 1))
                            Send(LocalGet('n'), '*',
                                 (Send(Self(), 'factorial:',
                                       (Send(LocalGet('n'), '-', (Constant(1),)),)),)))))
factorial_class = Class({'factorial:': make_method(('n',), (), factorial_body)},
                        ())
factorial = make_method((), (),
                        Send(Send(Constant(factorial_class), 'new', ()),
                             'factorial:',
                             (Constant(5),)))
try_factorial = factorial(None, (), final_k)
## trampoline(try_factorial)
#. 120
