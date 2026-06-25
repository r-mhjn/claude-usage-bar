#!/bin/bash
# Build a standalone "Claude Usage.app" using py2app, in an isolated venv
# so nothing is installed into your system Python.
#
#   ./build_app.sh
#
# Result: dist/Claude Usage.app  — drag it into /Applications.
set -euo pipefail

cd "$(dirname "$0")"

VENV=".build-venv"

echo "==> Creating build venv ($VENV)"
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> Installing build dependencies (rumps, py2app)"
pip install --quiet --upgrade pip
pip install --quiet rumps py2app

echo "==> Cleaning previous build"
rm -rf build dist

echo "==> Building app"
python setup.py py2app

deactivate
echo ""
echo "==> Done.  Built: dist/Claude Usage.app"
echo "    Install it with:  cp -R 'dist/Claude Usage.app' /Applications/"
