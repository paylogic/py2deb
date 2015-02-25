#!/bin/bash

cat >&2 << EOF

###########################
## Environment variables ##
###########################

EOF

export

cat >&2 << EOF

#######################################
## Overview of libpython.so versions ##
#######################################

EOF

ls -ld /usr/lib/libpython*.so*

cat >&2 << EOF

##################################################
## Overview of installed Python system packages ##
##################################################

EOF

dpkg -l | grep python

cat >&2 << EOF

##########################
## Output of test suite ##
##########################

EOF

python setup.py test
