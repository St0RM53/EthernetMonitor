# ethernet_monitor.spec

# -*- mode: python ; coding: utf-8 -*-

import pathlib
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

project_dir = str(pathlib.Path().resolve())

a = Analysis(
    ['ethernet_monitor.py'],
    pathex=[project_dir],
    binaries=[],
    datas=[
        ('ethernet_monitor_icon.ico', '.'),
        ('icon.png', '.'),
        ('icon_warning.png', '.'),
        ('config.json', '.'),
    ] + collect_data_files('pystray') + collect_data_files('winotify'),
    hiddenimports=[
        'win32com.client',
        'ctypes',
        'psutil._psutil_windows',
        'psutil._common'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EthernetMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='ethernet_monitor_icon.ico',
	version='version_info.txt',
    manifest='app.manifest',
    onefile=True
)
