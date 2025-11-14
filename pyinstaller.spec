# pyinstaller.spec
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 自动收集 qfluentwidgets 资源
qfluent_datas = collect_data_files('qfluentwidgets')

a = Analysis(
    ['FFmpegAssistantGUI.py'],
    pathex=[],
    binaries=[],
    datas=qfluent_datas,
    hiddenimports=[
        'PyQt5.sip',
        'qfluentwidgets',
        'qfluentwidgets.components',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'tkinter', 'numpy', 'scipy', 'pandas',
        'PIL', 'cv2', 'torch', 'tensorflow', 'opencv-python'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # 单文件
    name='FFmpegAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,              # 隐藏控制台
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='FFmpegAssistant'
)
