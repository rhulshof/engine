# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

added_files = [
    ('./resources/', 'resources/'),
    ("./LICENSE", "."),
    ("./TA-Lib-LICENSE", ".")
]

a = Analysis(['main.py'],
             binaries=[],
             datas=added_files,
             hiddenimports=["talib"],
             hookspath=["./hooks"],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='engine',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='engine')
