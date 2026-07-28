# -*- coding: utf-8 -*-
"""
节点注册模块
管理集群中的节点注册、心跳、发现、自动选主
"""

import os
import socket
import uuid
import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from .redis_client import redis_client
from .leader_election import leader_election


@dataclass
class NodeInfo:
    """节点信息"""
    node_id: str
    hostname: str
    ip_address: str
    port: int  # 管理 Web 端口
    role: str  # 'master' | 'worker' (自动选举决定)
    status: str  # 'online' | 'offline' | 'busy'
    registered_at: str
    last_heartbeat: str
    capacity: int  # 最大可启动实例数
    running_instances: int  # 当前运行实例数
    cpu_cores: int
    memory_mb: int
    labels: Dict[str, str]  # 自定义标签，如 zone, env 等
    is_leader: bool  # 是否是 Leader
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NodeInfo':
        # 兼容旧数据，添加 is_leader 默认值
        if 'is_leader' not in data:
            data['is_leader'] = False
        return cls(**data)


class NodeRegistry:
    """节点注册中心"""
    
    HEARTBEAT_INTERVAL = 10  # 心跳间隔（秒）
    NODE_TIMEOUT = 30  # 节点超时时间（秒）
    NODE_KEY = "locust:cluster:nodes"
    
    def __init__(self):
        self._node_id: Optional[str] = None
        self._node_info: Optional[NodeInfo] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._capacity = 10  # 保存容量配置
        
    def get_local_ip(self) -> str:
        """获取本机 IP 地址"""
        try:
            # 尝试连接外部地址获取本机出口 IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
            
    def get_system_info(self) -> Dict[str, int]:
        """获取系统信息"""
        import multiprocessing
        cpu_cores = multiprocessing.cpu_count()
        
        # 尝试获取内存信息
        memory_mb = 0
        try:
            import psutil
            memory_mb = psutil.virtual_memory().total // (1024 * 1024)
        except ImportError:
            # psutil 未安装，使用默认值
            memory_mb = 4096
            
        return {
            'cpu_cores': cpu_cores,
            'memory_mb': memory_mb
        }
        
    def generate_node_id(self) -> str:
        """生成节点 ID"""
        hostname = socket.gethostname()
        # 使用主机名 + 短 UUID 确保唯一性
        return f"{hostname}-{uuid.uuid4().hex[:8]}"
        
    def _on_become_leader(self):
        """成为 Leader 时的回调"""
        if self._node_info:
            with self._lock:
                self._node_info.role = 'master'
                self._node_info.is_leader = True
                redis_client.hset(self.NODE_KEY, self._node_id, self._node_info.to_dict())
            print(f"👑 节点 {self._node_id} 升级为 Master")
            
    def _on_lose_leadership(self):
        """失去 Leader 时的回调"""
        if self._node_info:
            with self._lock:
                self._node_info.role = 'worker'
                self._node_info.is_leader = False
                redis_client.hset(self.NODE_KEY, self._node_id, self._node_info.to_dict())
            print(f"⚠️ 节点 {self._node_id} 降级为 Worker")
        
    def register(self, port: int = 8088, capacity: int = 10) -> bool:
        """
        注册当前节点到集群（角色由自动选举决定）
        
        Args:
            port: 管理 Web 端口
            capacity: 最大可启动实例数
        """
        if not redis_client.is_connected():
            if not redis_client.connect():
                print("❌ 无法连接 Redis，节点注册失败")
                return False
                
        with self._lock:
            self._node_id = os.getenv('NODE_ID') or self.generate_node_id()
            self._capacity = capacity
            
            sys_info = self.get_system_info()
            now = datetime.now().isoformat()
            
            # 初始角色为 worker，等待选举结果
            self._node_info = NodeInfo(
                node_id=self._node_id,
                hostname=socket.gethostname(),
                ip_address=os.getenv('NODE_IP') or self.get_local_ip(),
                port=port,
                role='worker',  # 初始为 worker，选举成功后变为 master
                status='online',
                registered_at=now,
                last_heartbeat=now,
                capacity=capacity,
                running_instances=0,
                cpu_cores=sys_info['cpu_cores'],
                memory_mb=sys_info['memory_mb'],
                labels={},
                is_leader=False
            )
            
            # 写入 Redis
            redis_client.hset(self.NODE_KEY, self._node_id, self._node_info.to_dict())
            
            # 启动心跳线程
            self._start_heartbeat()
            
            # 启动 Leader 选举
            leader_election.start(
                node_id=self._node_id,
                on_become_leader=self._on_become_leader,
                on_lose_leadership=self._on_lose_leadership
            )
            
            print(f"✅ 节点注册成功: {self._node_id}")
            print(f"   IP: {self._node_info.ip_address}:{port}")
            print(f"   容量: {capacity}，等待选举...")
            
            return True
            
    def unregister(self):
        """从集群注销当前节点"""
        self._stop_heartbeat()
        
        # 停止选举
        leader_election.stop()
        
        if self._node_id and redis_client.is_connected():
            redis_client.hdel(self.NODE_KEY, self._node_id)
            print(f"✅ 节点已注销: {self._node_id}")
            
        self._node_id = None
        self._node_info = None
        
    def _start_heartbeat(self):
        """启动心跳线程"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
            
        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="NodeHeartbeat"
        )
        self._heartbeat_thread.start()
        
    def _stop_heartbeat(self):
        """停止心跳线程"""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
            self._heartbeat_thread = None
            
    def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                self._send_heartbeat()
                # 同时清理过期节点
                self._cleanup_expired_nodes()
            except Exception as e:
                print(f"心跳发送失败: {e}")
                
            time.sleep(self.HEARTBEAT_INTERVAL)
            
    def _send_heartbeat(self):
        """发送心跳"""
        if not self._node_info or not redis_client.is_connected():
            return
            
        with self._lock:
            self._node_info.last_heartbeat = datetime.now().isoformat()
            # 更新运行实例数
            from app.services.instance_manager import get_all_instances
            running = sum(1 for inst in get_all_instances() if inst.get('is_running'))
            self._node_info.running_instances = running
            # 更新 Leader 状态
            self._node_info.is_leader = leader_election.is_leader()
            self._node_info.role = 'master' if self._node_info.is_leader else 'worker'
            
            redis_client.hset(self.NODE_KEY, self._node_id, self._node_info.to_dict())
            
    def _cleanup_expired_nodes(self):
        """清理过期节点"""
        if not redis_client.is_connected():
            return
            
        nodes = redis_client.hgetall(self.NODE_KEY)
        now = datetime.now()
        
        for node_id, node_data in nodes.items():
            try:
                import json
                info = json.loads(node_data)
                last_hb = datetime.fromisoformat(info['last_heartbeat'])
                if (now - last_hb).total_seconds() > self.NODE_TIMEOUT:
                    redis_client.hdel(self.NODE_KEY, node_id)
                    print(f"⚠️ 清理过期节点: {node_id}")
            except Exception:
                continue
                
    def update_status(self, status: str):
        """更新节点状态"""
        if self._node_info:
            with self._lock:
                self._node_info.status = status
                redis_client.hset(self.NODE_KEY, self._node_id, self._node_info.to_dict())
                
    def update_running_instances(self, count: int):
        """更新运行实例数"""
        if self._node_info:
            with self._lock:
                self._node_info.running_instances = count
                redis_client.hset(self.NODE_KEY, self._node_id, self._node_info.to_dict())
                
    def get_current_node(self) -> Optional[NodeInfo]:
        """获取当前节点信息"""
        return self._node_info
        
    def get_node_id(self) -> Optional[str]:
        """获取当前节点 ID"""
        return self._node_id
        
    def get_all_nodes(self) -> List[NodeInfo]:
        """获取所有在线节点"""
        if not redis_client.is_connected():
            return []
            
        nodes = []
        data = redis_client.hgetall(self.NODE_KEY)
        
        for node_id, node_data in data.items():
            try:
                import json
                info = json.loads(node_data)
                node = NodeInfo.from_dict(info)
                nodes.append(node)
            except Exception as e:
                print(f"解析节点数据失败 [{node_id}]: {e}")
                continue
                
        return nodes
        
    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """获取指定节点信息"""
        data = redis_client.hget_json(self.NODE_KEY, node_id)
        if data:
            return NodeInfo.from_dict(data)
        return None
        
    def get_available_nodes(self, role: str = None) -> List[NodeInfo]:
        """获取可用节点（在线且有剩余容量）"""
        nodes = self.get_all_nodes()
        available = []
        
        for node in nodes:
            if node.status != 'online':
                continue
            if node.running_instances >= node.capacity:
                continue
            if role and node.role != role:
                continue
            available.append(node)
            
        # 按剩余容量排序（剩余多的优先）
        available.sort(key=lambda n: n.capacity - n.running_instances, reverse=True)
        return available
        
    def get_master_node(self) -> Optional[NodeInfo]:
        """获取 Master 节点（Leader）"""
        # 首先从选举器获取当前 Leader
        leader_id = leader_election.get_current_leader()
        if leader_id:
            node = self.get_node(leader_id)
            if node and node.status == 'online':
                return node
                
        # 如果选举器没有返回，从节点列表查找
        nodes = self.get_all_nodes()
        for node in nodes:
            if node.is_leader and node.status == 'online':
                return node
        return None
        
    def get_worker_nodes(self) -> List[NodeInfo]:
        """获取所有 Worker 节点（非 Leader）"""
        return [n for n in self.get_all_nodes() 
                if not n.is_leader and n.status == 'online']
                
    def is_current_node_leader(self) -> bool:
        """当前节点是否是 Leader"""
        return leader_election.is_leader()
        
    def force_reelection(self) -> bool:
        """强制重新选举"""
        return leader_election.force_election()


# 全局节点注册实例
node_registry = NodeRegistry()
