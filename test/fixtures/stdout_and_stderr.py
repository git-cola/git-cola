#!/usr/bin/env python
import sys
if sys.argv[2] == 'stdout':
    sys.stdout.write('\0' * int(sys.argv[1]))
    sys.stderr.write('\0' * int(sys.argv[1]))
else:
    sys.stderr.write('\0' * int(sys.argv[1]))
    sys.stdout.write('\0' * int(sys.argv[1]))
