# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[('streamlit_app.py', '.'), ('valuation/config/routing.json', 'valuation/config'), ('.env', '.'), ('/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/streamlit', 'streamlit')],
    hiddenimports=['streamlit', 'sqlalchemy', 'psycopg2', 'pandas', 'dotenv', 'pydantic', 'ingest_all'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VN100_Valuation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='VN100_Valuation.app',
    icon=None,
    bundle_identifier=None,
)
