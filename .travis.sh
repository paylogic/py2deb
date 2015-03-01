#!/bin/bash

cat >&2 << EOF

###########################
## Environment variables ##
###########################

EOF

export

cat >&2 << EOF

#############################
## Python shared libraries ##
#############################

EOF

find /opt/python -name 'libpython*.so*' -print0 | xargs -0 ls -ld

cat >&2 << EOF

##########################
## Output of test suite ##
##########################

EOF

python setup.py test
