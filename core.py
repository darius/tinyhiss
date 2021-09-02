"""
The kernel: stepping and calling.
"""

tracing = False

def trampoline(state):
    k, value = state
    while k is not None:
#        traceback((k, value))
        fn, free_var, k = k
        k, value = fn(value, free_var, k)
    return value

final_k = None

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
    if tracing:
        print '.... %14s %r' % (selector, receiver)
    return get_class(receiver).get_method(selector)(receiver, args, k)

def get_class(x):
    try:
        return x.class_         # TODO maybe call this .hiss_class or something instead
    except AttributeError:
        pass
    try:
        return class_from_type[type(x)]
    except KeyError:
        pass
    import primitive
    if isinstance(x, bool):
        return primitive.true_class if x else primitive.false_class
    if callable(x):
        return primitive.primitive_method_class
    assert False, "Classless datum"

class_from_type = {} # Filled in by the other modules which define the classes.
