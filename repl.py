"""
Read-eval-print loop, to aid debugging till the fancier UI is working.
"""

import sys, traceback
import core, hiss, parser, tinyhiss

def main(argv):
    hiss.start_up()
    repl()

def repl(show_traceback=True, show_parse=False):
    while True:
        try:
            line = raw_input('> ')
        except EOFError:
            break
        if line.startswith('.'): # Command
            cmd = line[1:2]
            arg = line[2:].strip()
            if cmd == '?':
                cmd_help()
            elif cmd == '.':
                hiss.start_up()
            elif cmd == 'p':
                # TODO this will exec in this here local env;
                #  do you have a better idea for which env?
                try:
                    exec arg
                except Exception:
                    print traceback.format_exc()
            elif cmd == 't':
                if arg == '':
                    core.tracing = not core.tracing
                    print "Tracing %s" % ({True: 'on', False: 'off'}[core.tracing])
                else:
                    tracing = {'on': True, 'off': False}.get(arg)
                    if tracing is not None:
                        core.tracing = tracing
                    else:
                        print "Unknown arg: %r" % arg
            else:
                print "Unknown command."
                cmd_help()
            continue
        if show_parse:
            code = parser.parse_code(line)
            print '#', code
        comment, result = tinyhiss.print_it(line, show_traceback)
        print comment + ' ' + result

def cmd_help():
    print """\
  .? help
  ..        Reload startup.hiss
  .p stmt   Exec python stmt
  .t arg?   Tracing on/off/toggle
"""

if __name__ == '__main__':
    main(sys.argv)
