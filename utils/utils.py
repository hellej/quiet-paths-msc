import sys

def print_progress(idx, count):
    sys.stdout.write(str(idx+1)+'/'+str(count)+' ')
    sys.stdout.flush()