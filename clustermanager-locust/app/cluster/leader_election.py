# -*- coding: utf-8 -*-
"""
Leader 选举模块
基于 Redis 实现自动选主，支持主节点故障自动切换
"""

import threading
import time
from typing import Optional, Callable
from datetime import datetime

from .redis_client import redis_client


class LeaderElection:
    """Leader 选举器"""
    
    # Redis Key
    LEADER_KEY = "locust:cluster:leader"
    LEADER_LOCK_KEY = "locust:cluster:leader_lock"
    
    # 选举配置
    LEADER_TTL = 15  # Leader 租约时间（秒）
    RENEW_INTERVAL = 5  # 续租间隔（秒）
    ELECTION_INTERVAL = 3  # 选举检查间隔（秒）
    
    def __init__(self):
        self._node_id: Optional[str] = None
        self._is_leader = False
        self._election_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        
        # 回调函数
        self._on_become_leader: Optional[Callable] = None
        self._on_lose_leadership: Optional[Callable] = None
        
    def start(self, node_id: str, 
              on_become_leader: Callable = None,
              on_lose_leadership: Callable = None):
        """
        启动选举
        
        Args:
            node_id: 当前节点 ID
            on_become_leader: 成为 Leader 时的回调
            on_lose_leadership: 失去 Leader 时的回调
        """
        self._node_id = node_id
        self._on_become_leader = on_become_leader
        self._on_lose_leadership = on_lose_leadership
        self._running = True
        
        self._election_thread = threading.Thread(
            target=self._election_loop,
            daemon=True,
            name="LeaderElection"
        )
        self._election_thread.start()
        
        print(f"🗳️ 节点 {node_id} 已加入选举")
        
    def stop(self):
        """停止选举"""
        self._running = False
        
        # 如果是 Leader，释放领导权
        if self._is_leader:
            self._release_leadership()
            
        if self._election_thread:
            self._election_thread.join(timeout=5)
            
    def _election_loop(self):
        """选举主循环"""
        while self._running:
            try:
                if self._is_leader:
                    # 当前是 Leader，续租
                    if not self._renew_leadership():
                        # 续租失败，失去领导权
                        self._handle_lose_leadership()
                else:
                    # 当前不是 Leader，尝试竞选
                    if self._try_become_leader():
                        self._handle_become_leader()
                    else:
                        # 检查当前 Leader 是否存活
                        self._check_leader_alive()
                        
            except Exception as e:
                print(f"选举循环异常: {e}")
                
            # 等待下一次检查
            interval = self.RENEW_INTERVAL if self._is_leader else self.ELECTION_INTERVAL
            time.sleep(interval)
            
    def _try_become_leader(self) -> bool:
        """尝试成为 Leader"""
        if not redis_client.is_connected():
            return False
            
        try:
            client = redis_client.get_client()
            
            # 使用 SET NX 原子操作竞选
            # 只有当 Key 不存在时才能设置成功
            result = client.set(
                self.LEADER_KEY,
                self._node_id,
                nx=True,  # 只在 Key 不存在时设置
                ex=self.LEADER_TTL  # 设置过期时间
            )
            
            return bool(result)
            
        except Exception as e:
            print(f"竞选 Leader 失败: {e}")
            return False
            
    def _renew_leadership(self) -> bool:
        """续租 Leader"""
        if not redis_client.is_connected():
            return False
            
        try:
            client = redis_client.get_client()
            
            # 检查当前 Leader 是否还是自己
            current_leader = client.get(self.LEADER_KEY)
            if current_leader != self._node_id:
                return False
                
            # 续租
            return client.expire(self.LEADER_KEY, self.LEADER_TTL)
            
        except Exception as e:
            print(f"续租 Leader 失败: {e}")
            return False
            
    def _release_leadership(self):
        """释放领导权"""
        if not redis_client.is_connected():
            return
            
        try:
            client = redis_client.get_client()
            
            # 使用 Lua 脚本确保只删除自己持有的 Leader Key
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            client.eval(lua_script, 1, self.LEADER_KEY, self._node_id)
            
        except Exception as e:
            print(f"释放领导权失败: {e}")
            
    def _check_leader_alive(self):
        """检查当前 Leader 是否存活"""
        # Leader Key 有 TTL，如果 Leader 故障，Key 会自动过期
        # 这里可以添加额外的健康检查逻辑
        pass
        
    def _handle_become_leader(self):
        """处理成为 Leader"""
        with self._lock:
            self._is_leader = True
            print(f"👑 节点 {self._node_id} 成为 Leader")
            
        if self._on_become_leader:
            try:
                self._on_become_leader()
            except Exception as e:
                print(f"on_become_leader 回调异常: {e}")
                
    def _handle_lose_leadership(self):
        """处理失去领导权"""
        with self._lock:
            self._is_leader = False
            print(f"⚠️ 节点 {self._node_id} 失去 Leader 身份")
            
        if self._on_lose_leadership:
            try:
                self._on_lose_leadership()
            except Exception as e:
                print(f"on_lose_leadership 回调异常: {e}")
                
    def is_leader(self) -> bool:
        """当前节点是否是 Leader"""
        return self._is_leader
        
    def get_current_leader(self) -> Optional[str]:
        """获取当前 Leader 节点 ID"""
        if not redis_client.is_connected():
            return None
            
        try:
            return redis_client.get(self.LEADER_KEY)
        except Exception:
            return None
            
    def force_election(self):
        """强制重新选举（仅用于调试）"""
        if not redis_client.is_connected():
            return False
            
        try:
            # 删除当前 Leader Key，触发重新选举
            redis_client.delete(self.LEADER_KEY)
            print("🔄 已触发重新选举")
            return True
        except Exception as e:
            print(f"强制选举失败: {e}")
            return False


# 全局选举器实例
leader_election = LeaderElection()
