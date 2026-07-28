#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Locust Management Web Interface
提供Web界面来启动、停止和管理多个Locust压测进程
支持多实例并行压测、代理功能和集群模式
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
    # 修复 Windows 控制台 GBK 编码无法输出 emoji/中文的问题
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def create_app():
    """应用工厂函数"""
    app = Flask(__name__)

    # 会话配置
    app.secret_key = os.environ.get('SECRET_KEY', 'locust-management-secret-key-2024')
    app.permanent_session_lifetime = timedelta(hours=24)

    # 上传配置
    app.config['UPLOAD_FOLDER'] = 'scripts/tmp'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # 过滤健康检查日志（/ok 太频繁，刷屏）
    import logging
    
    class HealthCheckFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            # 过滤高频轮询请求日志
            if '"GET /ok ' in msg:
                return False
            if '"GET /api/instances ' in msg:
                return False
            return True
    
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(HealthCheckFilter())

    # 注册蓝图
    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp
    from app.routes.instance_routes import instance_bp
    from app.routes.script_routes import script_bp
    from app.routes.proxy_routes import proxy_bp
    from app.routes.account_routes import account_bp
    from app.routes.cluster_routes import cluster_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(instance_bp)
    app.register_blueprint(script_bp)
    app.register_blueprint(proxy_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(cluster_bp)
    
    # 初始化主节点代理（从节点自动转发请求到主节点）
    try:
        from app.cluster.master_proxy import master_proxy
        master_proxy.init_app(app)
    except Exception as e:
        print(f"⚠️ 主节点代理初始化失败: {e}")

    return app


def init_cluster():
    """初始化集群功能"""
    from app.config import is_cluster_enabled, get_redis_config, get_node_capacity, print_config_status
    
    # 打印 Nacos 配置状态
    print_config_status()
    
    # 检查集群是否启用
    if not is_cluster_enabled():
        print("📋 集群模式已禁用（在 Nacos 中设置 cluster.enabled: true 启用）")
        return False
        
    print("🔗 正在初始化集群...")
    
    try:
        from app.cluster import redis_client, node_registry, cluster_manager
        
        # 获取 Redis 配置
        redis_cfg = get_redis_config()
        capacity = get_node_capacity()
        
        # 配置 Redis 连接
        redis_client.configure(
            host=redis_cfg.get('host', 'localhost'),
            port=redis_cfg.get('port', 6379),
            password=redis_cfg.get('password') or None,
            database=redis_cfg.get('db', 9)
        )
        
        # 连接 Redis
        if not redis_client.connect():
            print("❌ Redis 连接失败，集群功能不可用")
            return False
            
        # 注册当前节点（角色由自动选举决定）
        success = node_registry.register(
            port=8088,
            capacity=capacity
        )
        
        if not success:
            print("❌ 节点注册失败")
            return False
            
        # 启动集群管理器
        cluster_manager.start()
        
        print("✅ 集群初始化完成")
        return True
        
    except ImportError as e:
        print(f"❌ 集群模块导入失败: {e}")
        print("💡 请确保已安装 redis: pip install redis")
        return False
    except Exception as e:
        print(f"❌ 集群初始化失败: {e}")
        return False


def init_application():
    """初始化应用程序"""
    print("🚀 正在启动Locust多实例管理系统...")

    os.makedirs('scripts/tmp', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

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

    # 初始化集群
    cluster_ok = init_cluster()
    
    print("\n🌐 Web服务启动信息:")
    print("   管理界面: http://localhost:8088")
    print("   健康检查: http://localhost:8088/ok")
    if cluster_ok:
        print("   集群状态: http://localhost:8088/api/cluster/status")
        print("   节点列表: http://localhost:8088/api/cluster/nodes")
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
            
        # 注销集群节点
        try:
            from app.cluster import node_registry, cluster_manager
            cluster_manager.stop()
            node_registry.unregister()
        except Exception:
            pass
            
        print("✅ 应用程序已安全关闭")
    except Exception as e:
        print(f"\n❌ 应用程序运行错误: {e}")
        exit(1)
