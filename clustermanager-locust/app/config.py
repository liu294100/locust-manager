# -*- coding: utf-8 -*-
"""
统一配置模块
从 Nacos 读取所有配置（数据库、Redis、集群等）
"""

import os
import requests
import yaml
from typing import Dict, Optional

# ============== Nacos 默认配置 ==============
NACOS_DEFAULT_URL = "http://localhost:8848"
NACOS_DEFAULT_USER = "nacos"
NACOS_DEFAULT_PASS = "nacos"

# 环境 → Nacos namespaceId 映射
NAMESPACES = {
    "local": "local",
    "dev": "dev",
    "test": "test",
    "pre": "dev",
    "prod": "prod",
}

DEFAULT_DATA_ID = "locust-platform-config.yaml"
DEFAULT_GROUP = "DEFAULT_GROUP"
DEFAULT_NAMESPACE = "test"  # test 命名空间的实际 ID


class NacosClient:
    """Nacos 配置客户端"""
    
    def __init__(self, base_url=None, username=None, password=None):
        self.base_url = (base_url or NACOS_DEFAULT_URL).rstrip("/")
        self.username = username or NACOS_DEFAULT_USER
        self.password = password or NACOS_DEFAULT_PASS
        self.token = None
        
    def _get_token(self) -> Optional[str]:
        """获取认证 Token"""
        try:
            url = f"{self.base_url}/nacos/v1/auth/login"
            resp = requests.post(url, data={
                "username": self.username,
                "password": self.password
            }, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("accessToken")
                return self.token
        except Exception as e:
            print(f"Nacos 登录失败: {e}")
        return None
        
    def _ensure_token(self):
        if not self.token:
            self._get_token()
            
    def get_config(self, data_id: str = None, group: str = None, 
                   namespace_id: str = None) -> Optional[Dict]:
        """获取 Nacos 配置"""
        self._ensure_token()
        
        url = f"{self.base_url}/nacos/v2/cs/config"
        params = {
            "dataId": data_id or DEFAULT_DATA_ID,
            "group": group or DEFAULT_GROUP,
            "namespaceId": namespace_id or DEFAULT_NAMESPACE,
        }
        if self.token:
            params["accessToken"] = self.token
            
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    content = result.get("data", "")
                    if content:
                        return yaml.safe_load(content)
        except Exception as e:
            print(f"从 Nacos 获取配置失败: {e}")
        return None


# 全局 Nacos 客户端
_nacos_client = NacosClient()
_config_cache: Optional[Dict] = None


def get_nacos_config(force_refresh: bool = False) -> Dict:
    """获取 Nacos 配置（带缓存）"""
    global _config_cache
    if _config_cache is None or force_refresh:
        _config_cache = _nacos_client.get_config() or {}
    return _config_cache


def refresh_config() -> Dict:
    """刷新配置"""
    return get_nacos_config(force_refresh=True)


# ============== 集群配置 ==============
def get_cluster_config() -> Dict:
    """获取集群配置"""
    config = get_nacos_config()
    return config.get("cluster", {})


def is_cluster_enabled() -> bool:
    """是否启用集群"""
    return get_cluster_config().get("enabled", False)


def get_redis_config() -> Dict:
    """获取 Redis 配置"""
    cluster = get_cluster_config()
    return cluster.get("redis", {
        "host": "localhost",
        "port": 6379,
        "password": "",
        "db": 9
    })


def get_node_capacity() -> int:
    """获取节点容量"""
    cluster = get_cluster_config()
    return cluster.get("capacity", 10)


def get_instance_cleanup_interval() -> int:
    """获取实例清理间隔（秒），默认 60 秒"""
    cluster = get_cluster_config()
    return cluster.get("cleanup_interval", 60)


def get_pending_timeout() -> int:
    """获取 pending 超时时间（秒），超时后自动清理，默认 60 秒"""
    cluster = get_cluster_config()
    return cluster.get("pending_timeout", 60)


def get_worker_processes() -> int:
    """获取每个 Worker 节点启动的进程数，默认 1"""
    cluster = get_cluster_config()
    return max(1, int(cluster.get("worker_processes", 1)))


# ============== 数据库配置 ==============
class DatabaseConfig:
    """数据库配置类"""
    
    def __init__(self):
        self._db_config: Optional[Dict] = None
        self.use_mysql = os.getenv('USE_MYSQL', 'false').lower() == 'true'
    
    def get_database_config(self) -> Dict:
        """获取数据库配置"""
        if self._db_config is None:
            nacos_config = get_nacos_config()
            
            if self.use_mysql and 'database' in nacos_config:
                self._db_config = nacos_config['database']
            elif self.use_mysql:
                self._db_config = {
                    'type': 'mysql',
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'port': int(os.getenv('DB_PORT', '3306')),
                    'database': os.getenv('DB_NAME', 'locust_auth'),
                    'user': os.getenv('DB_USER', 'root'),
                    'password': os.getenv('DB_PASSWORD', 'root'),
                    'charset': 'utf8mb4',
                    'autocommit': True,
                    'connect_timeout': 10
                }
            else:
                self._db_config = {
                    'type': 'sqlite',
                    'database': os.getenv('SQLITE_DB', 'locust_auth.db')
                }
        
        return self._db_config
    
    def refresh_config(self):
        """刷新配置"""
        refresh_config()
        self._db_config = None
        return self.get_database_config()


# 全局数据库配置
db_config = DatabaseConfig()


# ============== 调试信息 ==============
def print_config_status():
    """打印配置状态"""
    print(f"📋 Nacos 配置中心: {NACOS_DEFAULT_URL}")
    print(f"   命名空间: {DEFAULT_NAMESPACE}")
    print(f"   DataId: {DEFAULT_DATA_ID}")
    
    config = get_nacos_config()
    if config:
        print("✅ Nacos 配置加载成功")
        if is_cluster_enabled():
            redis = get_redis_config()
            print(f"   集群模式: 已启用")
            print(f"   Redis: {redis.get('host')}:{redis.get('port')}")
        else:
            print(f"   集群模式: 未启用")
    else:
        print("⚠️ Nacos 配置加载失败，使用默认配置")


def get_nacos_info() -> Dict:
    """获取 Nacos 连接信息"""
    return {
        'server': NACOS_DEFAULT_URL,
        'namespace': DEFAULT_NAMESPACE,
        'group': DEFAULT_GROUP,
        'data_id': DEFAULT_DATA_ID
    }
