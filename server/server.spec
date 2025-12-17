# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集所有必要的隐藏导入
hiddenimports = [
    # Server 核心模块
    'server',
    'server.main',
    'server.config',
    'server.database',
    'server.models',
    'server.schemas',
    'server.auth',
    'server.utils',
    'server.routers',
    'server.routers.auth',
    'server.routers.models',
    'server.services',
    'server.services.model_sync',
    
    # Pydantic 相关（解决 PanicException）
    'pydantic',
    'pydantic_settings',
    'pydantic_settings.main',
    'pydantic_settings.sources',
    'pydantic._internal',
    'pydantic._internal._config',
    'pydantic._internal._generate_schema',
    'pydantic._internal._model_construction',
    'pydantic._internal._core_utils',
    'pydantic._internal._fields',
    'pydantic._internal._validators',
    'pydantic_core',
    'pydantic_core._pydantic_core',
    
    # FastAPI 相关
    'fastapi',
    'fastapi.applications',
    'fastapi.routing',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.responses',
    'fastapi.security',
    'starlette',
    'starlette.applications',
    'starlette.middleware',
    'starlette.routing',
    'starlette.responses',
    
    # Uvicorn 相关
    'uvicorn',
    'uvicorn.main',
    'uvicorn.config',
    'uvicorn.server',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.websockets',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.logging',
    
    # SQLAlchemy 相关
    'sqlalchemy',
    'sqlalchemy.orm',
    'sqlalchemy.engine',
    'sqlalchemy.pool',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.sql',
    
    # JWT 认证相关
    'jose',
    'jose.jwt',
    'jose.exceptions',
    'passlib',
    'passlib.context',
    'passlib.hash',
    'bcrypt',
    
    # 其他依赖
    'watchfiles',
    'watchfiles.main',
    'watchfiles.watcher',
    'email_validator',
    'multipart',
    'multipart.multipart',
    
    # Python 标准库（确保包含）
    'hashlib',
    'json',
    'pathlib',
    'datetime',
    'threading',
    'typing',
    'os',
    'sys',
]

# 收集所有子模块
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('pydantic_settings')
hiddenimports += collect_submodules('fastapi')
hiddenimports += collect_submodules('starlette')
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('sqlalchemy')
hiddenimports += collect_submodules('jose')
hiddenimports += collect_submodules('watchfiles')

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

# 收集 fastapi 的所有资源
try:
    tmp_ret = collect_all('fastapi')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except:
    pass

# 收集 uvicorn 的所有资源
try:
    tmp_ret = collect_all('uvicorn')
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

# 收集 watchfiles 的所有资源
try:
    tmp_ret = collect_all('watchfiles')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except:
    pass

a = Analysis(
    ['run.py'],
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
    name='server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 关闭 UPX 压缩，避免兼容性问题
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

