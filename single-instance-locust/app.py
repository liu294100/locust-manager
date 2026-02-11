#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Locust Management Web Interface
提供Web界面来启动、停止和管理多个Locust压测进程
支持多实例并行压测和代理功能
"""

import os
import sys
from datetime import timedelta

# 修复 zope namespace package 路径问题（Anaconda 环境兼容）
def _fix_zope_namespace():
    """确保 zope namespace package 能找到所有子包"""
    try:
        import site
        user_site = site.getusersitepackages()
        if user_site and os.path.isdir(user_site):
            user_zope = os.path.join(user_site, 'zope')
            if os.path.isdir(user_zope):
                try:
                    import zope
                    if user_zope not in getattr(zope, '__path__', []):
                        zope.__path__.append(user_zope)
                except ImportError:
                    pass
    except Exception:
        pass

_fix_zope_namespace()

from flask import Flask

# 设置文件系统编码
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'


def create_app():
    """应用工厂函数"""
    app = Flask(__name__)

    # 会话配置
    app.secret_key = os.environ.get('SECRET_KEY', 'locust-management-secret-key-2024')
    app.permanent_session_lifetime = timedelta(hours=24)

    # 上传配置
    app.config['UPLOAD_FOLDER'] = 'scripts/tmp'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # 注册蓝图
    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp
    from app.routes.instance_routes import instance_bp
    from app.routes.script_routes import script_bp
    from app.routes.proxy_routes import proxy_bp
    from app.routes.account_routes import account_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(instance_bp)
    app.register_blueprint(script_bp)
    app.register_blueprint(proxy_bp)
    app.register_blueprint(account_bp)

    return app


def init_application():
    """初始化应用程序"""
    print("🚀 正在启动Locust多实例管理系统...")

    os.makedirs('scripts/tmp', exist_ok=True)

    print("📋 正在初始化数据库...")
    try:
        from app.config import db_config
        from app.database import db_manager

        config = db_config.get_database_config()
        db_type = config.get('type', 'sqlite')

        if db_type == 'mysql':
            print(f"🔗 使用MySQL数据库: {config['host']}:{config['port']}/{config['database']}")
        else:
            print("🔗 使用SQLite本地数据库")

        db_manager.init_database()
        print("✅ 数据库初始化成功")

    except ImportError as e:
        if 'pymysql' in str(e):
            print("❌ MySQL支持需要安装pymysql")
            print("💡 请运行: pip install pymysql")
        else:
            print(f"❌ 数据库模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False

    print("\n🌐 Web服务启动信息:")
    print("   管理界面: http://localhost:8088")
    print("   健康检查: http://localhost:8088/ok")
    print("\n" + "=" * 50)

    return True


# 创建应用实例
app = create_app()

if __name__ == '__main__':
    if not init_application():
        print("\n❌ 应用程序初始化失败，退出...")
        exit(1)

    try:
        from app.services.instance_manager import stop_all_instances

        print("📊 启动优化的Flask服务器...")
        print("💡 提示：生产环境建议使用 gunicorn --workers 4 --threads 8 --bind 0.0.0.0:8088 app:app")

        app.run(
            host='0.0.0.0',
            port=8088,
            debug=False,
            threaded=True,
            processes=1,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n\n👋 正在关闭应用程序...")
        try:
            stopped = stop_all_instances()
            if stopped:
                print(f"✅ 已停止 {len(stopped)} 个Locust实例")
        except Exception:
            pass
        print("✅ 应用程序已安全关闭")
    except Exception as e:
        print(f"\n❌ 应用程序运行错误: {e}")
        exit(1)
