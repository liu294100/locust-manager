# -*- coding: utf-8 -*-
"""
集群管理模块
管理分布式 Locust 实例的创建、调度、状态同步
"""

import os
import json
import threading
import time
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from .redis_client import redis_client
from .node_registry import node_registry, NodeInfo


@dataclass
class ClusterInstance:
    """集群实例信息"""
    instance_id: str
    node_id: str
    script_file: str
    port: int
    target_host: Optional[str]
    users: Optional[int]
    spawn_rate: Optional[int]
    run_time: Optional[str]
    mode: str  # 'standalone' | 'master' | 'worker'
    master_host: Optional[str]  # worker 模式时的 master 地址
    master_port: Optional[int]  # worker 模式时的 master 端口
    status: str  # 'pending' | 'starting' | 'running' | 'stopped' | 'error'
    created_at: str
    updated_at: str
    web_url: Optional[str]
    workers: List[str]  # worker 实例 ID 列表（master 模式时使用）
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ClusterInstance':
        return cls(**data)


class ClusterManager:
    """集群管理器"""
    
    INSTANCE_KEY = "locust:cluster:instances"
    CHANNEL_COMMAND = "locust:cluster:commands"
    CHANNEL_STATUS = "locust:cluster:status"
    
    def __init__(self):
        self._subscriber = None
        self._sub_thread: Optional[threading.Thread] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._command_handlers = {}
        
    def start(self):
        """启动集群管理器"""
        if not redis_client.is_connected():
            print("⚠️ Redis 未连接，集群管理器未启动")
            return False
            
        self._running = True
        self._start_subscriber()
        self._start_cleanup_task()
        
        # 启动时立即清理：
        # 1. 清理当前节点的遗留实例（重启/重新部署后旧进程已死）
        # 2. 清理离线节点的实例
        try:
            self._cleanup_current_node_instances()
            self._cleanup_stale_instances()
        except Exception as e:
            print(f"⚠️ 启动时清理失败: {e}")
            
        print("✅ 集群管理器已启动")
        return True
        
    def stop(self):
        """停止集群管理器"""
        self._running = False
        if self._subscriber:
            try:
                self._subscriber.unsubscribe()
                self._subscriber.close()
            except Exception:
                pass
        if self._sub_thread:
            self._sub_thread.join(timeout=5)
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        print("✅ 集群管理器已停止")
        
    def _start_subscriber(self):
        """启动命令订阅"""
        self._subscriber = redis_client.subscribe(self.CHANNEL_COMMAND)
        if self._subscriber:
            self._sub_thread = threading.Thread(
                target=self._listen_commands,
                daemon=True,
                name="ClusterCommandListener"
            )
            self._sub_thread.start()
            
    def _start_cleanup_task(self):
        """启动定时清理任务"""
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="ClusterInstanceCleanup"
        )
        self._cleanup_thread.start()
        
    def _cleanup_loop(self):
        """定时清理循环"""
        from app.config import get_instance_cleanup_interval
        
        while self._running:
            try:
                interval = get_instance_cleanup_interval()
                time.sleep(interval)
                
                if not self._running:
                    break
                    
                self._cleanup_stale_instances()
            except Exception as e:
                print(f"⚠️ 清理任务异常: {e}")
                time.sleep(60)
                
    def _cleanup_stale_instances(self):
        """清理过期实例（离线节点 + 已停止的实例）"""
        if not redis_client.is_connected():
            return
            
        # 获取在线节点
        online_node_ids = set()
        try:
            all_nodes = node_registry.get_all_nodes()
            for node in all_nodes:
                online_node_ids.add(node.node_id)
        except Exception:
            return
            
        if not online_node_ids:
            return
            
        data = redis_client.hgetall(self.INSTANCE_KEY)
        cleaned = 0
        
        for inst_id, inst_data in data.items():
            try:
                info = json.loads(inst_data)
                node_id = info.get('node_id', '')
                status = info.get('status', '')
                
                should_remove = False
                reason = ''
                
                # 节点不在线 -> 清理
                if node_id not in online_node_ids:
                    should_remove = True
                    reason = f"节点离线({node_id})"
                    
                # 已停止的实例 -> 清理
                elif status in ('stopped', 'error'):
                    should_remove = True
                    reason = f"状态={status}"
                    
                # pending 超过配置时间 -> 清理（启动失败）
                elif status == 'pending':
                    created_at = info.get('created_at', '')
                    if created_at:
                        try:
                            from app.config import get_pending_timeout
                            pending_timeout = get_pending_timeout()
                            created_time = datetime.fromisoformat(created_at)
                            if (datetime.now() - created_time).total_seconds() > pending_timeout:
                                should_remove = True
                                reason = f"pending超时(>{pending_timeout}s)"
                        except Exception:
                            pass
                    
                if should_remove:
                    redis_client.hdel(self.INSTANCE_KEY, inst_id)
                    cleaned += 1
                    print(f"🗑️ 清理实例 {inst_id}: {reason}")
                else:
                    # 过滤 workers 列表中离线的节点
                    workers = info.get('workers', [])
                    if workers:
                        alive_workers = [w for w in workers if w in online_node_ids]
                        if len(alive_workers) != len(workers):
                            info['workers'] = alive_workers
                            redis_client.hset(self.INSTANCE_KEY, inst_id, info)
                            
            except Exception:
                continue
                
        if cleaned > 0:
            print(f"✅ 清理任务完成: 清理了 {cleaned} 个过期实例")
            
    def _cleanup_current_node_instances(self):
        """清理当前节点的遗留实例（重启/部署后旧进程已经不存在了）"""
        if not redis_client.is_connected():
            return
            
        current_node_id = node_registry.get_node_id()
        if not current_node_id:
            return
            
        # 获取当前本地真正在运行的实例 ID
        from app.services.instance_manager import get_all_instances
        local_instances = get_all_instances()
        local_running_ids = {inst['instance_id'] for inst in local_instances if inst.get('is_running')}
        
        data = redis_client.hgetall(self.INSTANCE_KEY)
        cleaned = 0
        
        for inst_id, inst_data in data.items():
            try:
                info = json.loads(inst_data)
                # 只处理属于当前节点的实例
                if info.get('node_id') != current_node_id:
                    continue
                    
                # 如果 Redis 里记录为 running，但本地实际没有这个进程 -> 清理
                if info.get('status') == 'running' and inst_id not in local_running_ids:
                    redis_client.hdel(self.INSTANCE_KEY, inst_id)
                    cleaned += 1
                    print(f"🗑️ 清理遗留实例 {inst_id}: 本地进程不存在")
            except Exception:
                continue
                
        if cleaned > 0:
            print(f"✅ 启动清理: 清理了当前节点 {cleaned} 个遗留实例")
            
    def _listen_commands(self):
        """监听集群命令"""
        if not self._subscriber:
            return
            
        for message in self._subscriber.listen():
            if not self._running:
                break
                
            if message['type'] != 'message':
                continue
                
            try:
                data = json.loads(message['data'])
                self._handle_command(data)
            except Exception as e:
                print(f"处理集群命令失败: {e}")
                
    def _handle_command(self, data: Dict):
        """处理集群命令"""
        cmd = data.get('command')
        target_node = data.get('target_node')
        current_node = node_registry.get_node_id()
        
        # 检查命令是否针对当前节点
        if target_node and target_node != current_node and target_node != '*':
            return
            
        if cmd == 'start_instance':
            self._handle_start_instance(data)
        elif cmd == 'stop_instance':
            self._handle_stop_instance(data)
        elif cmd == 'sync_status':
            self._handle_sync_status(data)
            
    def _handle_start_instance(self, data: Dict):
        """处理启动实例命令"""
        import os
        from app.services.instance_manager import start_locust_instance
        from app.config import get_worker_processes
        
        instance_id = data.get('instance_id')
        script_file = data.get('script_file')
        target_host = data.get('target_host')
        users = data.get('users')
        spawn_rate = data.get('spawn_rate')
        run_time = data.get('run_time')
        mode = data.get('mode', 'standalone')
        master_host = data.get('master_host')
        master_port = data.get('master_port')
        expect_workers = data.get('expect_workers', 0)
        
        # 补全脚本路径：如果不是绝对路径且不以 scripts/ 开头，加上前缀
        if script_file and not os.path.isabs(script_file):
            if not script_file.startswith('scripts/') and not script_file.startswith('scripts\\'):
                script_file = os.path.normpath(os.path.join('scripts', script_file))
        
        print(f"📋 处理启动命令: instance={instance_id}, script={script_file}, mode={mode}")
        
        # 检查脚本文件是否存在
        if not os.path.exists(script_file):
            print(f"❌ 脚本文件不存在: {script_file}")
            self._broadcast_status({
                'instance_id': instance_id,
                'node_id': node_registry.get_node_id(),
                'success': False,
                'message': f'脚本文件不存在: {script_file}',
                'status': 'error'
            })
            return
        
        # 启动本地实例
        success, message, local_id, port = start_locust_instance(
            script_file=script_file,
            target_host=target_host,
            users=users,
            spawn_rate=spawn_rate,
            run_time=run_time,
            mode=mode,
            master_host=master_host,
            master_port=master_port,
            expect_workers=expect_workers,
            worker_processes=get_worker_processes() if mode == 'worker' else 1
        )
        
        print(f"📋 启动结果: success={success}, message={message}, local_id={local_id}, port={port}")
        
        # 更新 Redis 中的实例状态
        if success:
            node = node_registry.get_current_node()
            web_url = f"http://{node.ip_address}:{port}" if node and port else None
            self.update_instance_status(instance_id, 'running', port=port, web_url=web_url)
            print(f"✅ 实例 {instance_id} 启动成功，端口: {port}")
            
            # 如果是 Master 模式，启动后需要通知 Worker 启动
            print(f"🔍 检查是否需要启动 Worker: mode={mode}, port={port}, expect_workers={expect_workers}")
            if mode == 'master' and port:
                # 获取 Master 的 bind 端口（用于 Worker 连接）
                from app.services.instance_manager import get_instance
                local_inst = get_instance(local_id)
                print(f"🔍 获取本地实例: local_id={local_id}, local_inst={local_inst}")
                if local_inst:
                    print(f"🔍 本地实例信息: master_bind_port={local_inst.master_bind_port}, mode={local_inst.mode}")
                
                if local_inst and local_inst.master_bind_port:
                    node_ip = node.ip_address if node else '127.0.0.1'
                    print(f"📡 Master 就绪，通知 Worker 连接到 {node_ip}:{local_inst.master_bind_port}")
                    self.start_workers_for_master(instance_id, node_ip, local_inst.master_bind_port)
                else:
                    print(f"⚠️ 无法启动 Worker: local_inst={local_inst is not None}, master_bind_port={local_inst.master_bind_port if local_inst else 'N/A'}")
        else:
            self.update_instance_status(instance_id, 'error')
            print(f"❌ 实例 {instance_id} 启动失败: {message}")
        
        # 广播状态（供其他节点监听）
        self._broadcast_status({
            'instance_id': instance_id,
            'local_id': local_id,
            'node_id': node_registry.get_node_id(),
            'success': success,
            'message': message,
            'port': port,
            'status': 'running' if success else 'error'
        })
        
    def _handle_stop_instance(self, data: Dict):
        """处理停止实例命令"""
        from app.services.instance_manager import stop_locust_instance, get_all_instances
        
        instance_id = data.get('instance_id')
        local_id = data.get('local_id')
        
        # 如果没有 local_id，通过端口或集群 instance_id 查找本地进程
        if not local_id:
            # 先从 Redis 获取实例端口
            inst_data = redis_client.hget_json(self.INSTANCE_KEY, instance_id)
            target_port = inst_data.get('port') if inst_data else None
            
            # 在本地实例中找匹配的进程
            local_instances = get_all_instances()
            for inst in local_instances:
                # 按端口匹配
                if target_port and inst.get('port') == target_port and inst.get('is_running'):
                    local_id = inst['instance_id']
                    break
                # 按 instance_id 直接匹配（standalone 模式）
                if inst['instance_id'] == instance_id:
                    local_id = instance_id
                    break
        
        if local_id:
            success, message = stop_locust_instance(local_id)
        else:
            success, message = False, f"未找到本地进程: {instance_id}"
            
        self._broadcast_status({
            'instance_id': instance_id,
            'local_id': local_id,
            'node_id': node_registry.get_node_id(),
            'success': success,
            'message': message,
            'status': 'stopped' if success else 'error'
        })
            
    def _handle_sync_status(self, data: Dict):
        """处理状态同步命令"""
        from app.services.instance_manager import get_all_instances
        
        instances = get_all_instances()
        self._broadcast_status({
            'node_id': node_registry.get_node_id(),
            'instances': instances,
            'timestamp': datetime.now().isoformat()
        })
        
    def _broadcast_status(self, status: Dict):
        """广播状态更新"""
        redis_client.publish(self.CHANNEL_STATUS, status)
        
    # ============ 集群实例管理 ============
    
    def create_cluster_instance(
        self,
        script_file: str,
        target_host: str = None,
        users: int = None,
        spawn_rate: int = None,
        run_time: str = None,
        worker_count: int = 0,
        preferred_nodes: List[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        创建集群实例
        
        Args:
            script_file: 压测脚本路径
            target_host: 目标主机
            users: 用户数
            spawn_rate: 生成速率
            run_time: 运行时间
            worker_count: Worker 数量（0 表示单机模式）
            preferred_nodes: 优先使用的节点 ID 列表
            
        Returns:
            (成功标志, 消息, 实例ID)
        """
        import uuid
        
        # 生成集群实例 ID
        instance_id = f"cluster-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        if worker_count == 0:
            # 单机模式 - 选择一个可用节点
            nodes = node_registry.get_available_nodes()
            if preferred_nodes:
                nodes = [n for n in nodes if n.node_id in preferred_nodes] or nodes
                
            if not nodes:
                return False, "没有可用节点", None
                
            target_node = nodes[0]
            
            # 创建集群实例记录
            cluster_inst = ClusterInstance(
                instance_id=instance_id,
                node_id=target_node.node_id,
                script_file=script_file,
                port=0,  # 由节点分配
                target_host=target_host,
                users=users,
                spawn_rate=spawn_rate,
                run_time=run_time,
                mode='standalone',
                master_host=None,
                master_port=None,
                status='pending',
                created_at=now,
                updated_at=now,
                web_url=None,
                workers=[]
            )
            
            # 保存到 Redis
            redis_client.hset(self.INSTANCE_KEY, instance_id, cluster_inst.to_dict())
            
            # 发送启动命令
            self._send_command({
                'command': 'start_instance',
                'target_node': target_node.node_id,
                'instance_id': instance_id,
                'script_file': script_file,
                'target_host': target_host,
                'users': users,
                'spawn_rate': spawn_rate,
                'run_time': run_time,
                'mode': 'standalone'
            })
            
            return True, f"实例创建中，目标节点: {target_node.node_id}", instance_id
            
        else:
            # 分布式模式 - 需要 1 个 Master + N 个 Worker
            available_nodes = node_registry.get_available_nodes()
            
            if len(available_nodes) < 1:
                return False, "没有可用节点", None
                
            # 选择 Master 节点（优先选择 master 角色或容量最大的节点）
            master_nodes = [n for n in available_nodes if n.role == 'master']
            master_node = master_nodes[0] if master_nodes else available_nodes[0]
            
            # 选择 Worker 节点
            worker_nodes = [n for n in available_nodes if n.node_id != master_node.node_id]
            worker_nodes = worker_nodes[:worker_count]
            
            if len(worker_nodes) < worker_count:
                print(f"⚠️ 请求 {worker_count} 个 Worker，但只有 {len(worker_nodes)} 个可用节点")
                
            # 创建 Master 实例记录
            cluster_inst = ClusterInstance(
                instance_id=instance_id,
                node_id=master_node.node_id,
                script_file=script_file,
                port=0,
                target_host=target_host,
                users=users,
                spawn_rate=spawn_rate,
                run_time=run_time,
                mode='master',
                master_host=None,
                master_port=None,
                status='pending',
                created_at=now,
                updated_at=now,
                web_url=None,
                workers=[n.node_id for n in worker_nodes]
            )
            
            redis_client.hset(self.INSTANCE_KEY, instance_id, cluster_inst.to_dict())
            
            # 发送 Master 启动命令
            # expect_workers 需要乘以 worker_processes，因为每个节点会启动多个进程
            from app.config import get_worker_processes
            total_worker_processes = len(worker_nodes) * get_worker_processes()
            
            self._send_command({
                'command': 'start_instance',
                'target_node': master_node.node_id,
                'instance_id': instance_id,
                'script_file': script_file,
                'target_host': target_host,
                'users': users,
                'spawn_rate': spawn_rate,
                'run_time': run_time,
                'mode': 'master',
                'expect_workers': total_worker_processes
            })
            
            # Worker 启动会在 Master 就绪后由状态监听触发
            
            return True, f"集群实例创建中，Master: {master_node.node_id}, Workers: {len(worker_nodes)}", instance_id
    
    def _sync_script_to_node(self, node: NodeInfo, script_path: str) -> bool:
        """
        同步脚本文件到指定节点
        
        Args:
            node: 目标节点
            script_path: 相对于 scripts/ 的脚本路径
            
        Returns:
            是否同步成功
        """
        import os
        
        # 读取脚本内容
        full_path = os.path.join('scripts', script_path) if not script_path.startswith('scripts') else script_path
        
        # 计算相对路径（用于同步）
        if script_path.startswith('scripts/') or script_path.startswith('scripts\\'):
            rel_path = script_path[8:]  # 移除 'scripts/' 前缀
        else:
            rel_path = script_path
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ 读取脚本失败: {full_path}, 错误: {e}")
            return False
        
        # 同步到目标节点
        try:
            url = f"http://{node.ip_address}:{node.port}/api/script/sync"
            resp = requests.post(
                url,
                json={
                    'path': rel_path,
                    'content': content,
                    'source_node': node_registry.get_node_id()
                },
                headers={'X-Cluster-Sync': 'locust-cluster'},
                timeout=10
            )
            
            result = resp.json()
            if result.get('success'):
                print(f"✅ 脚本同步成功: {rel_path} -> {node.node_id}")
                return True
            else:
                print(f"❌ 脚本同步失败: {rel_path} -> {node.node_id}, 错误: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ 脚本同步请求失败: {node.node_id}, 错误: {e}")
            return False
            
    def start_workers_for_master(self, instance_id: str, master_host: str, master_port: int):
        """为 Master 启动 Worker 节点"""
        print(f"🚀 start_workers_for_master 被调用: instance_id={instance_id}, master_host={master_host}, master_port={master_port}")
        
        inst_data = redis_client.hget_json(self.INSTANCE_KEY, instance_id)
        if not inst_data:
            print(f"⚠️ 在 Redis 中找不到实例: {instance_id}")
            return
        
        print(f"📦 从 Redis 获取实例数据: {inst_data}")
        inst = ClusterInstance.from_dict(inst_data)
        
        print(f"👷 Workers 列表: {inst.workers}")
        
        if not inst.workers:
            print(f"⚠️ 没有配置 Worker 节点")
            return
        
        # 先同步脚本到所有 Worker 节点
        for worker_node_id in inst.workers:
            worker_node = node_registry.get_node(worker_node_id)
            if worker_node:
                print(f"📤 同步脚本到 Worker: {worker_node_id}")
                self._sync_script_to_node(worker_node, inst.script_file)
            else:
                print(f"⚠️ 找不到 Worker 节点: {worker_node_id}")
        
        # 然后启动 Worker
        for i, worker_node_id in enumerate(inst.workers):
            worker_instance_id = f"{instance_id}-worker-{i}"
            print(f"📨 发送 Worker 启动命令: {worker_instance_id} -> {worker_node_id}")
            
            self._send_command({
                'command': 'start_instance',
                'target_node': worker_node_id,
                'instance_id': worker_instance_id,
                'script_file': inst.script_file,
                'target_host': inst.target_host,
                'mode': 'worker',
                'master_host': master_host,
                'master_port': master_port
            })
            
    def _send_command(self, command: Dict):
        """发送集群命令"""
        redis_client.publish(self.CHANNEL_COMMAND, command)
        
    def stop_cluster_instance(self, instance_id: str) -> Tuple[bool, str]:
        """停止集群实例"""
        inst_data = redis_client.hget_json(self.INSTANCE_KEY, instance_id)
        if not inst_data:
            return False, "实例不存在"
            
        inst = ClusterInstance.from_dict(inst_data)
        
        # 停止 Master/Standalone
        self._send_command({
            'command': 'stop_instance',
            'target_node': inst.node_id,
            'instance_id': instance_id
        })
        
        # 如果有 Worker，也停止
        if inst.workers:
            for i, worker_node_id in enumerate(inst.workers):
                worker_instance_id = f"{instance_id}-worker-{i}"
                self._send_command({
                    'command': 'stop_instance',
                    'target_node': worker_node_id,
                    'instance_id': worker_instance_id
                })
                
        # 直接从 Redis 删除实例记录
        redis_client.hdel(self.INSTANCE_KEY, instance_id)
        
        return True, "已停止并清理"
        
    def remove_cluster_instance(self, instance_id: str) -> Tuple[bool, str]:
        """删除集群实例记录"""
        inst_data = redis_client.hget_json(self.INSTANCE_KEY, instance_id)
        if not inst_data:
            return False, "实例不存在"
            
        inst = ClusterInstance.from_dict(inst_data)
        
        # 如果还在运行，先停止
        if inst.status in ('running', 'starting'):
            self.stop_cluster_instance(instance_id)
            time.sleep(1)
            
        # 删除记录
        redis_client.hdel(self.INSTANCE_KEY, instance_id)
        
        # 删除 Worker 记录
        for i in range(len(inst.workers)):
            worker_instance_id = f"{instance_id}-worker-{i}"
            redis_client.hdel(self.INSTANCE_KEY, worker_instance_id)
            
        return True, "实例已删除"
        
    def get_cluster_instance(self, instance_id: str) -> Optional[ClusterInstance]:
        """获取集群实例信息"""
        data = redis_client.hget_json(self.INSTANCE_KEY, instance_id)
        if data:
            return ClusterInstance.from_dict(data)
        return None
        
    def get_all_cluster_instances(self) -> List[ClusterInstance]:
        """获取所有集群实例（已停止和离线的会被定时任务清理）"""
        if not redis_client.is_connected():
            return []
            
        instances = []
        data = redis_client.hgetall(self.INSTANCE_KEY)
        
        for inst_id, inst_data in data.items():
            try:
                info = json.loads(inst_data)
                inst = ClusterInstance.from_dict(info)
                instances.append(inst)
            except Exception:
                continue
                
        return instances
        
    def update_instance_status(self, instance_id: str, status: str, 
                               port: int = None, web_url: str = None):
        """更新实例状态"""
        inst_data = redis_client.hget_json(self.INSTANCE_KEY, instance_id)
        if not inst_data:
            return
            
        inst = ClusterInstance.from_dict(inst_data)
        inst.status = status
        inst.updated_at = datetime.now().isoformat()
        
        if port:
            inst.port = port
        if web_url:
            inst.web_url = web_url
            
        redis_client.hset(self.INSTANCE_KEY, instance_id, inst.to_dict())
        
    def sync_all_status(self):
        """请求所有节点同步状态"""
        self._send_command({
            'command': 'sync_status',
            'target_node': '*'
        })
        
    # ============ 远程节点操作 ============
    
    def call_remote_node(self, node: NodeInfo, endpoint: str, 
                         method: str = 'GET', data: Dict = None) -> Optional[Dict]:
        """调用远程节点 API"""
        try:
            url = f"http://{node.ip_address}:{node.port}{endpoint}"
            
            if method == 'GET':
                resp = requests.get(url, timeout=10)
            elif method == 'POST':
                resp = requests.post(url, json=data, timeout=10)
            elif method == 'DELETE':
                resp = requests.delete(url, timeout=10)
            else:
                return None
                
            return resp.json()
        except Exception as e:
            print(f"调用远程节点失败 [{node.node_id}]: {e}")
            return None
            
    def get_cluster_stats(self) -> Dict[str, Any]:
        """获取集群统计信息"""
        nodes = node_registry.get_all_nodes()
        instances = self.get_all_cluster_instances()
        
        online_nodes = [n for n in nodes if n.status == 'online']
        running_instances = [i for i in instances if i.status == 'running']
        
        total_capacity = sum(n.capacity for n in online_nodes)
        total_running = sum(n.running_instances for n in online_nodes)
        
        return {
            'total_nodes': len(nodes),
            'online_nodes': len(online_nodes),
            'total_capacity': total_capacity,
            'running_instances': len(running_instances),
            'total_running_local': total_running,
            'cluster_instances': len(instances),
            'nodes': [n.to_dict() for n in nodes],
            'timestamp': datetime.now().isoformat()
        }


# 全局集群管理器实例
cluster_manager = ClusterManager()
