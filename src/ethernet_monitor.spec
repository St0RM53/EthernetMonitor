# ethernet_monitor.spec

# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

import os
script_path = os.path.abspath("ethernet_monitor.py")

a = Analysis(
    [script_path],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.png', '.'),
        ('icon_warning.png', '.'),
    ],
    hiddenimports=[
        "pystray._win32",
        "win32com.client",
        "win32com.shell",
        "pythoncom",
        "win32con",
        "winotify",
        "win32timezone"
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EthernetMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='ethernet_monitor_icon.ico',  # ✅ set EXE icon
    single_file=True                   # ✅ one-file mode
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="EthernetMonitor"
)
