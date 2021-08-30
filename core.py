"""
The kernel: stepping and calling.
"""

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
    return get_class(receiver).get_method(selector)(receiver, args, k)

def get_class(x):
    try:
        return x.class_         # TODO maybe call this .hiss_class or something instead
    except AttributeError:
        pass
    if isinstance(x, bool):
        import terp
        return terp.true_class if x else terp.false_class
    try:
        return class_from_type[type(x)]
    except KeyError:
        pass
    if callable(x):
        import terp
        return terp.primitive_method_class # TODO: define this
    assert False, "Classless datum"

class_from_type = {} # Filled in by the other modules which define the classes.
