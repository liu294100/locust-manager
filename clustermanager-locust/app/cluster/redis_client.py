# -*- coding: utf-8 -*-
"""
Redis 客户端模块
用于集群节点注册与状态同步
"""

import os
import json
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class RedisClient:
    """Redis 客户端封装"""
    
    # Redis Key 前缀
    KEY_PREFIX = "locust:cluster:"
    NODE_KEY = KEY_PREFIX + "nodes"
    INSTANCE_KEY = KEY_PREFIX + "instances"
    LOCK_KEY = KEY_PREFIX + "lock:"
    
    def __init__(self):
        self._client: Optional['redis.Redis'] = None
        self._config: Dict[str, Any] = {}
        self._connected = False
        self._lock = threading.Lock()
        
    def configure(self, host: str = None, port: int = None, 
                  password: str = None, database: int = None):
        """配置 Redis 连接参数"""
        self._config = {
            'host': host or os.getenv('REDIS_HOST', 'localhost'),
            'port': port or int(os.getenv('REDIS_PORT', '6379')),
            'password': password or os.getenv('REDIS_PASSWORD', '') or None,
            'db': database if database is not None else int(os.getenv('REDIS_DB', '9')),
            'decode_responses': True,
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
            'retry_on_timeout': True,
        }
        # 如果密码为空字符串，设为 None
        if not self._config['password']:
            self._config['password'] = None
            
    def connect(self) -> bool:
        """建立 Redis 连接"""
        if not REDIS_AVAILABLE:
            print("❌ Redis 模块未安装，请运行: pip install redis")
            return False
            
        if not self._config:
            self.configure()
            
        with self._lock:
            try:
                self._client = redis.Redis(**self._config)
                # 测试连接
                self._client.ping()
                self._connected = True
                print(f"✅ Redis 连接成功: {self._config['host']}:{self._config['port']}, DB={self._config['db']}")
                return True
            except redis.ConnectionError as e:
                print(f"❌ Redis 连接失败: {e}")
                self._connected = False
                return False
            except Exception as e:
                print(f"❌ Redis 初始化错误: {e}")
                self._connected = False
                return False
                
    def disconnect(self):
        """断开 Redis 连接"""
        with self._lock:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            self._connected = False
            
    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._connected or not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            self._connected = False
            return False
            
    def get_client(self) -> Optional['redis.Redis']:
        """获取原始 Redis 客户端"""
        if not self._connected:
            self.connect()
        return self._client
    
    # ============ 基础操作 ============
    
    def set(self, key: str, value: Any, ex: int = None) -> bool:
        """设置值"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, default=str)
            return self._client.set(key, value, ex=ex)
        except Exception as e:
            print(f"Redis SET 错误: {e}")
            return False
            
    def get(self, key: str) -> Optional[str]:
        """获取值"""
        try:
            return self._client.get(key)
        except Exception as e:
            print(f"Redis GET 错误: {e}")
            return None
            
    def get_json(self, key: str) -> Optional[Dict]:
        """获取 JSON 值"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
        
    def delete(self, *keys) -> int:
        """删除键"""
        try:
            return self._client.delete(*keys)
        except Exception as e:
            print(f"Redis DELETE 错误: {e}")
            return 0
            
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(self._client.exists(key))
        except Exception:
            return False
            
    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        try:
            return self._client.expire(key, seconds)
        except Exception:
            return False
    
    # ============ Hash 操作 ============
    
    def hset(self, name: str, key: str, value: Any) -> int:
        """Hash 设置字段"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, default=str)
            return self._client.hset(name, key, value)
        except Exception as e:
            print(f"Redis HSET 错误: {e}")
            return 0
            
    def hget(self, name: str, key: str) -> Optional[str]:
        """Hash 获取字段"""
        try:
            return self._client.hget(name, key)
        except Exception as e:
            print(f"Redis HGET 错误: {e}")
            return None
            
    def hget_json(self, name: str, key: str) -> Optional[Dict]:
        """Hash 获取 JSON 字段"""
        value = self.hget(name, key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
            
    def hgetall(self, name: str) -> Dict[str, str]:
        """Hash 获取所有字段"""
        try:
            return self._client.hgetall(name) or {}
        except Exception as e:
            print(f"Redis HGETALL 错误: {e}")
            return {}
            
    def hdel(self, name: str, *keys) -> int:
        """Hash 删除字段"""
        try:
            return self._client.hdel(name, *keys)
        except Exception as e:
            print(f"Redis HDEL 错误: {e}")
            return 0
            
    def hkeys(self, name: str) -> List[str]:
        """Hash 获取所有键"""
        try:
            return self._client.hkeys(name) or []
        except Exception:
            return []
    
    # ============ 发布订阅 ============
    
    def publish(self, channel: str, message: Any) -> int:
        """发布消息"""
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message, ensure_ascii=False, default=str)
            return self._client.publish(channel, message)
        except Exception as e:
            print(f"Redis PUBLISH 错误: {e}")
            return 0
            
    def subscribe(self, *channels):
        """订阅频道"""
        try:
            pubsub = self._client.pubsub()
            pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            print(f"Redis SUBSCRIBE 错误: {e}")
            return None
    
    # ============ 分布式锁 ============
    
    def acquire_lock(self, lock_name: str, timeout: int = 10) -> bool:
        """获取分布式锁"""
        lock_key = self.LOCK_KEY + lock_name
        try:
            return bool(self._client.set(lock_key, "1", nx=True, ex=timeout))
        except Exception:
            return False
            
    def release_lock(self, lock_name: str) -> bool:
        """释放分布式锁"""
        lock_key = self.LOCK_KEY + lock_name
        try:
            return bool(self._client.delete(lock_key))
        except Exception:
            return False


# 全局 Redis 客户端实例
redis_client = RedisClient()
