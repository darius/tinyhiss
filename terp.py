"""
AST interpreter
"""

from collections import namedtuple

def trampoline(value, k):
    while k is not None:
#        print value, k#.__name__
        value, k = k(value)
    return value

def call(receiver, selector, args, k):
    return (receiver, args, k), get_class(receiver).get_method(selector)

def get_class(x):
    if x is None:                        return nil_class
    elif isinstance(x, bool):            return true_class if x else false_class
    elif isinstance(x, (int, float)):    return num_class
    elif isinstance(x, (str, unicode)):  return string_class
    elif isinstance(x, Block):           return block_class
    elif isinstance(x, Class):           return class_class
    else:                                return x.class_

class Thing(namedtuple('_Thing', 'class_ data')):
    def get(self, key):
        return self.data[self.class_.ivar_index[key]]
    def put(self, key, value):
        self.data[self.class_.ivar_index[key]] = value

class Class(object):
    def __init__(self, methods, ivars):
        self.methods = methods
        self.ivars = ivars
        self.ivar_index = dict(zip(ivars, range(len(ivars))))
    def get_method(self, selector):
        try:
            return self.methods[selector]
        except KeyError:
            assert False, selector
    def make(self):
        return Thing(self, [None] * len(self.ivars))

def Method(params, local_vars, expr):
    return Block(None, None, params, local_vars, expr)

class Block(namedtuple('_Block', 'receiver env params locals expr')):
    def __call__(self, (receiver, arguments, k)):
        rib = dict(zip(self.params, arguments))
        for var in self.locals:
            rib[var] = None
        real_receiver = self.receiver or receiver
        return self.expr.eval(real_receiver, Env(rib, self.env), k)

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

def new_method((receiver, arguments, k)):
    return receiver.make(), k

class_class = Class(dict(new=new_method), ())

block_class = Class(dict(run=lambda (receiver, arguments, k): receiver((None, (), k))),
                    ())

num_methods = {'+': lambda (rcvr, (other,), k): (rcvr + as_number(other), k),
               '*': lambda (rcvr, (other,), k): (rcvr * as_number(other), k),
               '-': lambda (rcvr, (other,), k): (rcvr - as_number(other), k),
               '=': lambda (rcvr, (other,), k): (rcvr == other, k), # XXX object method
               }
num_class = Class(num_methods, ())

def as_number(thing):
    if isinstance(thing, (int, float)):
        return thing
    assert False, thing

class Self(namedtuple('_Self', '')):
    def eval(self, receiver, env, k):
        return receiver, k

class Constant(namedtuple('_Constant', 'value')):
    def eval(self, receiver, env, k):
        return self.value, k

class BlockLiteral(namedtuple('_BlockLiteral', 'params locals expr')):
    def eval(self, receiver, env, k):
        return Block(receiver, env, self.params, self.locals, self.expr), k

class VarGet(namedtuple('_VarGet', 'name')):
    def eval(self, receiver, env, k):
        try: return env.get(self.name), k
        except KeyError:
            try: return receiver.get(self.name), k
            except KeyError:
                try: return global_env[self.name], k
                except KeyError:
                    raise "Unbound variable", self.name

class VarPut(namedtuple('_VarPut', 'name expr')):
    def eval(self, receiver, env, k):
        def putting(value):
            try: env.put(self.name, value)
            except KeyError:
                try: receiver.put(self.name, value)
                except KeyError:
                    raise "Unbound variable", self.name
            return value, k
        return self.expr.eval(receiver, env, putting)

global_env = {}

class Cascade(namedtuple('_Cascade', 'subject selector operands')):
    def eval(self, receiver, env, k):
        return self.subject.eval(
            receiver, env,
            lambda subject: evrands(
                self.operands, receiver, env,
                lambda args: call(
                    subject, self.selector, args,
                    lambda _: (subject, k))))

class Send(namedtuple('_Send', 'subject selector operands')):
    def eval(self, receiver, env, k):
        return self.subject.eval(
            receiver, env,
            lambda subject: evrands(
                self.operands, receiver, env,
                lambda args: call(subject, self.selector, args, k)))

def evrands(operands, receiver, env, k):
    if not operands:
        return (), k
    else:
        return operands[0].eval(receiver, env,
                                lambda val: evrands(operands[1:], receiver, env,
                                                    lambda vals: ((val,)+vals, k)))


class Then(namedtuple('_Then', 'expr1 expr2')):
    def eval(self, receiver, env, k):
        return self.expr1.eval(
            receiver, env,
            lambda _: self.expr2.eval(receiver, env, k))

true_class = Class({'ifTrue:ifFalse:': Method(('trueBlock', 'falseBlock'), (),
                                              Send(VarGet('trueBlock'), 'run', ()))},
                   ())
false_class = Class({'ifTrue:ifFalse:': Method(('trueBlock', 'falseBlock'), (),
                                               Send(VarGet('falseBlock'), 'run', ()))},
                    ())

final_k = lambda result: (result, None)


# Testing

smoketest_expr = Send(Constant(2), '+', (Constant(3),))
smoketest = smoketest_expr.eval(None, None, final_k)
## trampoline(*smoketest)
#. 5

def make(class_, k):
    return call(class_, 'new', (),
                lambda instance: call(instance, 'init', (),
                                      lambda _: (instance, k)))

object_init = Method((), (), Self())

eg_init_with = Method(('value',), (), VarPut('whee', VarGet('value')))
eg_get_whee = Method((), (), VarGet('whee'))
eg_yay_body = Send(Send(Self(), 'get_whee', ()), '+', (VarGet('x'),))
eg_yay = Method(('x',), ('v',), eg_yay_body)
eg_class = Class(dict(yay=eg_yay,
                      get_whee=eg_get_whee,
                      init_with=eg_init_with),
                 ('whee',))
eg = call(eg_class, 'new', (),
          lambda instance: call(instance, 'init_with', (42,),
                                lambda _: (instance, final_k)))
eg = trampoline(*eg)
eg_result = call(eg, 'yay', (137,), final_k)
## trampoline(*eg_result)
#. 179

make_eg = Block(None, None, (), (),
                Send(Cascade(Send(Constant(eg_class), 'new', ()),
                             'init_with', (Constant(42),)),
                     'yay', (Constant(137),)))
make_eg_result = (None, (), final_k), make_eg
## trampoline(*make_eg_result)
#. 179

# TODO: make this a method on Number
factorial_body = Send(Send(VarGet('n'), '=', (Constant(0),)),
                      'ifTrue:ifFalse:',
                      (BlockLiteral((), (), Constant(1)),
                       BlockLiteral((), (),
                                    # n * (self factorial: (n - 1))
                                    Send(VarGet('n'), '*',
                                         (Send(Self(), 'factorial:',
                                               (Send(VarGet('n'), '-', (Constant(1),)),)),)))))
factorial_class = Class({'factorial:': Method(('n',), (), factorial_body)},
                        ())
factorial = Block(None, None, (), (),
                  Send(Send(Constant(factorial_class), 'new', ()),
                       'factorial:',
                       (Constant(5),)))
try_factorial = (None, (), final_k), factorial
## trampoline(*try_factorial)
#. 120

                  
"""
to do:
- inheritance
- Object class with default 'init', '=', etc.
- reflection
  - smalltalk access to instance vars of kernel classes
    - none such for num_class, etc.
  - PrimitiveMethod class
  - smalltalk methods for methods of kernel classes
    Thing get, put, get_class
    Class get_method, make, get_instance_variables, get_superclass
    Block __call__
    Env get, put
    <Expr> eval
  - reify coninuations
  - messageNotUnderstood
  - other exception handling
- strings
- arrays
- nonlocal return
- exceptions
- assignment
"""
