"""py2app build script.

Build a standalone macOS .app:

    ./build_app.sh

or manually:

    python3 setup.py py2app

Produces  dist/Claude Usage.app  — drag it into /Applications.
"""

from setuptools import setup

APP = ["app.py"]
# Local modules app.py imports — py2app follows these, listed for clarity.
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,  # off for menu bar apps (Carbon event loop issues)
    "plist": {
        "CFBundleName": "Claude Usage",
        "CFBundleDisplayName": "Claude Usage",
        "CFBundleIdentifier": "com.local.claude-usage-bar",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        # LSUIElement: run as a menu bar agent — no Dock icon, no app menu.
        "LSUIElement": True,
        "NSHumanReadableCopyright": "Local build",
    },
    "packages": ["rumps"],
    "includes": ["usage_reader", "pricing"],
}

setup(
    app=APP,
    name="Claude Usage",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
