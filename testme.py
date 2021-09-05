"""
Run the test suite.

Design criteria:
- no-fuss to add new tests from interactions, by repl or maybe by IDE
- tests can show value or exception, and Log output
- quick to run

Further wishlist, not satisfied yet:
- some tests will need new methods, or new classes
- some test isolation would be nice
- easy to investigate a failing test

TODO it's ugly that we have two code formats: change files and these transcripts
"""

import sys

import hiss, tinyhiss

loud = False

def main():
    hiss.start_up()
    for line, outputs in group(chunks(nonempties(iter(sys.stdin)))):
        if loud: print repr(line), repr(outputs)

        comment, result = tinyhiss.print_it(line, show_traceback=False)
        expected_outputs = []
        log = spill_log()
        if log: expected_outputs.append(('--.', log))
        expected_outputs.append(('-->', result))

        if outputs != expected_outputs:
            print 'mismatch for', line
            print '  expected:', repr(expected_outputs)
            print '   but got:', repr(outputs)

# XXX code dupe
def spill_log():
    s = tinyhiss.workspace_run("|s| s := Log show. Log clear. s")  # TODO no simpler code?
    return s

def group(chunks):
    "Group each input chunk with its output chunks."
    # TODO itertools?
    line, outputs = None, []
    for mark, item in chunks:
        if mark == '>':
            if line is not None: yield line, outputs
            line, outputs = item, []
        else:
            outputs.append((mark, item))
    if line is not None: yield line, outputs

def nonempties(lines):
    for line in lines:
        line = line.rstrip('\n')
        if line: yield line

def chunks(lines):
    "Split each line into mark and item; group successive lines by mark."
    # TODO use itertools?
    prefix = None
    chunk = []
    for line in lines:
        mark, remainder = line.split(' ', 1)
        if mark == prefix:
            chunk.append(remainder)
        else:
            if chunk: yield prefix, '\n'.join(chunk)
            prefix, chunk = mark, [remainder]
    if chunk: yield prefix, '\n'.join(chunk)

if __name__ == '__main__':
    main()
