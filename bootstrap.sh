#!/bin/bash -e

# Bootstrap script for py2deb.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: October 1, 2013
# URL: https://github.com/paylogic/py2deb
#
# This shell script can be used to convert py2deb and its dependencies to
# Debian packages using py2deb. This bootstrapping process uses a temporary
# py2deb installation in a virtual environment.

main () {

  # Create a temporary directory tree where we can put the intermediate Python
  # source distributions, virtual environment and generated Debian packages.
  local temporary_directory="$(mktemp -d)"
  local build_directory="$(ensure_directory "$temporary_directory/build")"
  local environment_directory="$(ensure_directory "$temporary_directory/environment")"
  local deb_pkg_tools_cmd="$environment_directory/bin/deb-pkg-tools"
  local packages_directory="$(ensure_directory "$temporary_directory/packages")"
  local local_source_index="$(ensure_directory "$temporary_directory/index")"

  # Prepare the system for running py2deb.
  msg "Making sure python-stdeb is not installed .."
  sudo apt-get purge --yes python-stdeb
  msg "Installing prerequisites for bootstrapping py2deb .."
  sudo apt-get install --yes apt-file dpkg-dev python-pkg-resources python-virtualenv
  msg "Making sure apt-file cache has been initialized .."
  sudo apt-file update

  # Generate a Python source distribution archive of py2deb and move the
  # resulting archive to the temporary local source index directory.
  msg "Preparing py2deb source distribution .."
  local script_name="$0"
  if [ ! -f "$script_name" ]; then
    msg "Error: Failed to locate py2deb source distribution directory!" >&2
    return 1
  fi
  local script_path="$(readlink -f "$script_name")"
  cd "$(dirname "$script_path")"
  rm -Rf dist
  python setup.py sdist
  mkdir -p "$local_source_index"
  mv dist/*.tar.gz "$local_source_index"

  # Create a Python virtual environment and install py2deb in it.
  msg "Preparing virtual environment .."
  virtualenv --no-site-packages "$environment_directory"
  source "$environment_directory/bin/activate"
  msg "Installing py2deb and dependencies in virtual environment .."
  pip install --ignore-installed "--find-links=file://$local_source_index" "--build=$build_directory" py2deb

  # Use py2deb to convert itself and its dependencies to Debian packages.
  msg "Converting py2deb and dependencies to Debian packages .."
  py2deb --verbose "--repo=$packages_directory" -- "--find-links=file://$local_source_index" py2deb

  # Improvise a trivial package repository for installation.
  msg "Generating trivial Debian package repository .."
  sudo -i "$deb_pkg_tools_cmd" --update-repo "$packages_directory" --verbose
  msg "Activating trivial Debian package repository .."
  sudo -i "$deb_pkg_tools_cmd" --activate-repo "$packages_directory" --verbose

  # Install py2deb as a Debian package using the trivial package repository.
  if dpkg-query --show --showformat='${Status}' python-all | grep -q 'install ok installed'; then
    # First remove the previously installed Debian package?
    msg "Removing previously installed py2deb Debian package and dependencies .."
    sudo apt-get autoremove --yes python-py2deb
  fi
  msg "Installing py2deb using Debian packages .."
  sudo apt-get install --yes python-py2deb

  # Clean up the trivial package repository.
  msg "Cleaning up trivial Debian package repository .."
  sudo -i "$deb_pkg_tools_cmd" --deactivate-repo "$packages_directory" --verbose

  # Clean up the temporary directory tree.
  msg "Cleaning up temporary directory: $temporary_directory"
  sudo rm -Rf "$temporary_directory"

}

ensure_directory () {
  mkdir -p "$1"
  echo "$1"
}

msg () {
  echo "[bootstrap] $*" >&2
}

main "$@"
