#!/bin/bash -e

# This Bash script is responsible for running the py2deb test suite on the
# Travis CI hosted continuous integration service. Some notes about this
# script:
#
# 1. Travis CI provides Python 2.6, 2.7 and 3.4 installations based on a Chef
#    cookbook that uses pyenv which means that the Python installations used
#    are custom compiled and not managed using Debian packages. This is a
#    problem for py2deb because it depends on the correct functioning of
#    dpkg-shlibdeps which expects Python to be installed using Debian
#    packages.
#
# 2. A dozen convoluted workarounds can be constructed to work around this.
#    I've decided to go with a fairly simple one that I know very well and
#    which has worked very well for the local testing that I've been doing for
#    months: Using the `deadsnakes PPA' to install various Python versions
#    using Debian packages.

# The following Debian system packages are required for all builds.
REQUIRED_SYSTEM_PACKAGES="dpkg-dev fakeroot lintian"

main () {
  msg "Preparing Travis CI test environment .."
  case "$TOXENV" in
    py27)
      # At the time of writing Travis CI workers are running Ubuntu 12.04 which
      # includes Python 2.7 as the default system wide Python version so we
      # don't need the deadsnakes PPA.
      install_with_apt_get python2.7 python2.7-dev
      ;;
    py35)
      # We need to get Python 3.5 from the deadsnakes PPA.
      install_with_deadsnakes_ppa python3.5 python3.5-dev
      ;;
    py36)
      # We need to get Python 3.6 from the deadsnakes PPA.
      install_with_deadsnakes_ppa python3.6 python3.6-dev
      ;;
    py37)
      # We need to get Python 3.7 from the deadsnakes PPA.
      install_with_deadsnakes_ppa python3.7 python3.7-dev
      ;;
    pypy)
      # Get PyPy 2 from the official PyPy PPA.
      install_with_pypy_ppa pypy pypy-dev
      ;;
    pypy3)
      # Get PyPy 3 from the official PyPy PPA.
      install_with_pypy_ppa pypy3 pypy3-dev
      ;;
    *)
      # Make sure .travis.yml and .travis.sh don't get out of sync.
      die "Unsupported Python version requested! (\$TOXENV not set)"
      ;;
  esac
}

install_with_deadsnakes_ppa () {
  msg "Installing deadsnakes PPA .."
  sudo add-apt-repository --yes ppa:deadsnakes/ppa
  install_with_apt_get "$@"
}

install_with_pypy_ppa () {
  msg "Installing PyPy PPA .."
  sudo add-apt-repository --yes ppa:pypy/ppa
  install_with_apt_get "$@"
}

install_with_apt_get () {
  export DEBIAN_FRONTEND=noninteractive
  msg "Installing with apt-get: $REQUIRED_SYSTEM_PACKAGES $*"
  sudo apt-get update --quiet --quiet
  sudo apt-get install --yes --quiet $REQUIRED_SYSTEM_PACKAGES "$@"
}

die () {
  msg "Error: $*"
  exit 1
}

msg () {
  echo "[travis.sh] $*" >&2
}

main "$@"
