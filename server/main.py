"""FastAPI应用主入口"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.database import init_db
from server.routers import auth, models, invitation
from server.config import settings

# 创建FastAPI应用
app = FastAPI(
    title="RVC模型服务API",
    description="用户认证和模型管理API",
    version="1.0.0",
    redirect_slashes=False  # 禁用自动重定向，避免307错误
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(models.router)
app.include_router(invitation.router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    import os
    # 确保模型目录存在
    os.makedirs(settings.models_base_path, exist_ok=True)
    
    # 确保数据库目录存在
    db_path = settings.database_url.replace("sqlite:///", "")
    if db_path and not db_path.startswith(":memory:"):
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    # 初始化数据库
    try:
        init_db()
        print(f"数据库初始化完成")
        print(f"数据库文件路径: {os.path.abspath(db_path) if db_path else '内存数据库'}")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        raise
    
    # 同步模型到数据库
    try:
        from server.services.model_sync import model_sync_service
        # 打印模型文件路径（使用model_sync_service中的实际路径）
        print(f"模型文件路径: {model_sync_service.models_base_path}")
        print("开始同步模型到数据库...")
        stats = model_sync_service.sync()
        print(f"模型同步完成: 总计={stats['total']}, "
              f"新建={stats['created']}, 更新={stats['updated']}, "
              f"跳过={stats['skipped']}, 错误={stats['errors']}")
    except Exception as e:
        print(f"模型同步失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 启动文件监听（后台任务）
    try:
        from server.services.model_sync import start_file_watcher
        start_file_watcher()
        print("文件监听已启动")
    except Exception as e:
        print(f"启动文件监听失败: {e}")
        import traceback
        traceback.print_exc()


@app.get("/")
def root():
    """根路径 - 返回HTML测试页面"""
    from fastapi.responses import HTMLResponse
    
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RVC模型服务API - 测试页面</title>
        <style>
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
            }
            .container {
                background: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }
            h1 {
                color: #667eea;
                text-align: center;
                margin-bottom: 30px;
            }
            .status {
                background: #f0f9ff;
                border-left: 4px solid #3b82f6;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }
            .status.ok {
                background: #f0fdf4;
                border-left-color: #22c55e;
            }
            .status.error {
                background: #fef2f2;
                border-left-color: #ef4444;
            }
            .endpoint {
                background: #f8fafc;
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
            }
            .endpoint a {
                color: #667eea;
                text-decoration: none;
            }
            .endpoint a:hover {
                text-decoration: underline;
            }
            .info {
                background: #fff7ed;
                border-left: 4px solid #f59e0b;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }
            button {
                background: #667eea;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
                margin: 5px;
            }
            button:hover {
                background: #5568d3;
            }
            #testResult {
                margin-top: 20px;
                padding: 15px;
                border-radius: 5px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 RVC模型服务API</h1>
            
            <div class="status ok">
                <strong>✅ 服务器运行正常</strong>
                <p>版本: 1.0.0</p>
                <p>服务器地址: <span id="serverUrl"></span></p>
            </div>
            
            <div class="info">
                <h3>📚 API文档</h3>
                <p>访问 <a href="/docs" target="_blank">/docs</a> 查看完整的API文档（Swagger UI）</p>
                <p>访问 <a href="/redoc" target="_blank">/redoc</a> 查看ReDoc格式的API文档</p>
            </div>
            
            <div>
                <h3>🔗 主要API端点</h3>
                <div class="endpoint">
                    <strong>健康检查:</strong> <a href="/health" target="_blank">GET /health</a>
                </div>
                <div class="endpoint">
                    <strong>用户注册:</strong> POST /api/auth/register
                </div>
                <div class="endpoint">
                    <strong>用户登录:</strong> POST /api/auth/login
                </div>
                <div class="endpoint">
                    <strong>获取当前用户:</strong> GET /api/auth/me
                </div>
                <div class="endpoint">
                    <strong>获取模型列表:</strong> GET /api/models/
                </div>
            </div>
            
            <div>
                <h3>🧪 快速测试</h3>
                <button onclick="testHealth()">测试健康检查</button>
                <button onclick="testLogin()">测试登录端点</button>
                <div id="testResult"></div>
            </div>
        </div>
        
        <script>
            // 显示当前服务器URL
            document.getElementById('serverUrl').textContent = window.location.origin;
            
            async function testHealth() {
                const resultDiv = document.getElementById('testResult');
                resultDiv.style.display = 'block';
                resultDiv.className = 'status';
                resultDiv.innerHTML = '<strong>测试中...</strong>';
                
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    resultDiv.className = 'status ok';
                    resultDiv.innerHTML = `<strong>✅ 健康检查成功</strong><pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch (error) {
                    resultDiv.className = 'status error';
                    resultDiv.innerHTML = `<strong>❌ 测试失败</strong><p>${error.message}</p>`;
                }
            }
            
            async function testLogin() {
                const resultDiv = document.getElementById('testResult');
                resultDiv.style.display = 'block';
                resultDiv.className = 'status';
                resultDiv.innerHTML = '<strong>测试中...</strong>';
                
                try {
                    const response = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            username: 'test',
                            password: 'test',
                            mac: '00:00:00:00:00:00'
                        })
                    });
                    const data = await response.json();
                    resultDiv.className = response.ok ? 'status ok' : 'status error';
                    resultDiv.innerHTML = `<strong>${response.ok ? '✅' : '❌'} 登录测试完成</strong><pre>${JSON.stringify(data, null, 2)}</pre>`;
                } catch (error) {
                    resultDiv.className = 'status error';
                    resultDiv.innerHTML = `<strong>❌ 测试失败</strong><p>${error.message}</p>`;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    # 开发环境可以使用 reload，方便调试；
    # 但如果被 PyInstaller 等打包成 exe（sys.frozen 为 True），必须关闭 reload，
    # 否则 reloader 会在冻结环境里不断拉起子进程，出现多次 “Started reloader process ...”
    reload_flag = settings.debug
    if getattr(sys, "frozen", False):
        reload_flag = False

    # 直接运行应用实例，而不是通过字符串引用
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=reload_flag
    )

