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

APP="dist/Claude Usage.app"
FRAMEWORKS="$APP/Contents/Frameworks"

# py2app on Homebrew/conda Python often misses libffi.8.dylib, which _ctypes
# (and therefore rumps -> pyobjc) needs. dyld already searches Contents/
# Frameworks, so copying it there resolves the load. Locate it next to the
# base interpreter, falling back to a broad search.
echo "==> Bundling libffi.8.dylib"
BASE_PREFIX="$(python -c 'import sys; print(sys.base_prefix)')"
FFI="$BASE_PREFIX/lib/libffi.8.dylib"
if [ ! -f "$FFI" ]; then
  FFI="$(find "$BASE_PREFIX" -name 'libffi.8.dylib' 2>/dev/null | head -1 || true)"
fi
if [ -z "${FFI:-}" ] || [ ! -f "$FFI" ]; then
  FFI="$(find /opt/homebrew /usr/local -name 'libffi.8.dylib' 2>/dev/null | head -1 || true)"
fi
if [ -n "${FFI:-}" ] && [ -f "$FFI" ]; then
  mkdir -p "$FRAMEWORKS"
  cp -f "$FFI" "$FRAMEWORKS/"
  echo "    copied $FFI"
else
  echo "    WARNING: libffi.8.dylib not found — app may fail to launch." >&2
fi

deactivate

# Modifying the bundle invalidates any signature; ad-hoc re-sign so the
# libraries load on Apple Silicon (unsigned code is killed on arm64).
echo "==> Ad-hoc re-signing"
codesign --force --deep --sign - "$APP" 2>/dev/null || \
  echo "    (codesign skipped/failed — usually fine for local use)"

echo ""
echo "==> Done.  Built: $APP"
echo "    Install it with:  cp -R '$APP' /Applications/"
