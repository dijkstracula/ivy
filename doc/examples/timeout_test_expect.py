import pexpect
import sys

def run(name,opts,res):
    child = pexpect.spawn('./{}'.format(name))
    child.logfile = sys.stdout
    try:
        child.expect('foo.timeout')
        return True
    except pexpect.EOF:
        print(child.before)
        return False
