# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集所有必要的隐藏导入
hiddenimports = [
    # Server 核心模块（用户模型管理工具所需）
    'server',
    'server.config',
    'server.database',
    'server.models',
    'server.schemas',
    
    # Pydantic 相关（用于数据验证）
    'pydantic',
    'pydantic_settings',
    'pydantic_settings.main',
    'pydantic_settings.sources',
    'pydantic._internal',
    'pydantic._internal._config',
    'pydantic_core',
    'pydantic_core._pydantic_core',
    
    # SQLAlchemy 相关（数据库操作）
    'sqlalchemy',
    'sqlalchemy.orm',
    'sqlalchemy.engine',
    'sqlalchemy.pool',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.sql',
    'sqlalchemy.inspection',
    
    # Python 标准库（确保包含）
    'argparse',
    'datetime',
    'typing',
    'os',
    'sys',
]

# 收集所有子模块
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('pydantic_settings')
hiddenimports += collect_submodules('sqlalchemy')

# 收集二进制文件和数据文件
binaries = []
datas = []

# 收集 pydantic 的所有资源
try:
    tmp_ret = collect_all('pydantic')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except:
    pass

# 收集 pydantic_settings 的所有资源
try:
    tmp_ret = collect_all('pydantic_settings')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except:
    pass

# 收集 sqlalchemy 的所有资源
try:
    tmp_ret = collect_all('sqlalchemy')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except:
    pass

a = Analysis(
    ['user_model_manager.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'IPython',
        'jupyter',
        'pytest',
        'sphinx',
        'setuptools',
        'distutils',
        'fastapi',
        'uvicorn',
        'starlette',
        'watchfiles',
        'jose',
        'passlib',
        'bcrypt',
        'email_validator',
        'multipart',
    ],
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
    name='user_model_manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 关闭 UPX 压缩，避免兼容性问题
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 命令行工具，使用控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

