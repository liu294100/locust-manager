# -*- coding: utf-8 -*-
"""
Locust实例管理模块
负责启动、停止和管理Locust压测实例
"""

import os
import signal
import subprocess
import threading
import time
import uuid
import psutil
from datetime import datetime
from typing import Dict, List, Optional
import logging
from .config import config
from .database import db_manager
from .redis_manager import redis_manager

class LocustInstance:
    """Locust实例类"""
    
    def __init__(self, instance_id: str, task_id: int, script_file: str, port: int, 
                 target_host: str = None, users: int = None, spawn_rate: float = None, 
                 run_time: int = None):
        self.instance_id = instance_id
        self.task_id = task_id
        self.script_file = script_file
        self.port = port
        self.target_host = target_host
        self.users = users
        self.spawn_rate = spawn_rate
        self.run_time = run_time
        self.process = None
        self.pid = None
        self.status = 'starting'
        self.created_at = datetime.now()
        self.started_at = None
        self.stopped_at = None
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """启动Locust实例"""
        try:
            # 构建Locust命令
            cmd = [
                'locust',
                '-f', self.script_file,
                '--web-port', str(self.port),
                '--host', self.target_host or 'http://localhost',
                '--headless' if self.users else '--web'
            ]
            
            # 如果指定了用户数和生成速率，使用无头模式
            if self.users and self.spawn_rate:
                cmd.extend([
                    '--users', str(self.users),
                    '--spawn-rate', str(self.spawn_rate)
                ])
                
                if self.run_time:
                    cmd.extend(['--run-time', f'{self.run_time}s'])
            
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(self.script_file) if os.path.dirname(self.script_file) else '.'
            )
            
            self.pid = self.process.pid
            self.status = 'running'
            self.started_at = datetime.now()
            
            # 更新数据库状态
            db_manager.update_instance_status(self.instance_id, 'running', self.pid)
            
            # 更新Redis状态
            if config.CLUSTER_MODE:
                redis_manager.update_instance_status(self.instance_id, 'running', pid=self.pid)
            
            self.logger.info(f"Locust实例 {self.instance_id} 已启动，PID: {self.pid}, 端口: {self.port}")
            return True
            
        except Exception as e:
            self.status = 'failed'
            self.logger.error(f"启动Locust实例失败: {e}")
            db_manager.update_instance_status(self.instance_id, 'failed')
            return False
    
    def stop(self):
        """停止Locust实例"""
        try:
            if self.process and self.process.poll() is None:
                # 尝试优雅关闭
                self.process.terminate()
                
                # 等待进程结束
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # 强制杀死进程
                    self.process.kill()
                    self.process.wait()
            
            # 如果有PID，确保进程被杀死
            if self.pid:
                try:
                    if psutil.pid_exists(self.pid):
                        proc = psutil.Process(self.pid)
                        proc.terminate()
                        proc.wait(timeout=10)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    pass
            
            self.status = 'stopped'
            self.stopped_at = datetime.now()
            
            # 更新数据库状态
            db_manager.update_instance_status(self.instance_id, 'stopped')
            
            # 更新Redis状态
            if config.CLUSTER_MODE:
                redis_manager.update_instance_status(self.instance_id, 'stopped')
            
            self.logger.info(f"Locust实例 {self.instance_id} 已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止Locust实例失败: {e}")
            return False
    
    def is_running(self):
        """检查实例是否正在运行"""
        if self.process:
            return self.process.poll() is None
        return False
    
    def get_info(self):
        """获取实例信息"""
        return {
            'instance_id': self.instance_id,
            'task_id': self.task_id,
            'script_file': self.script_file,
            'port': self.port,
            'target_host': self.target_host,
            'users': self.users,
            'spawn_rate': self.spawn_rate,
            'run_time': self.run_time,
            'pid': self.pid,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None,
            'is_running': self.is_running()
        }

class LocustManager:
    """Locust管理器"""
    
    def __init__(self):
        self.instances = {}  # {instance_id: LocustInstance}
        self.instances_lock = threading.Lock()
        self.base_port = config.BASE_LOCUST_PORT
        self.logger = logging.getLogger(__name__)
        
        # 启动清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def _get_next_available_port(self) -> int:
        """获取下一个可用端口"""
        port = self.base_port
        used_ports = {instance.port for instance in self.instances.values()}
        
        while port in used_ports or self._is_port_in_use(port):
            port += 1
        
        return port
    
    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def create_instance(self, task_id: int, script_file: str, **kwargs) -> Optional[str]:
        """创建Locust实例"""
        try:
            instance_id = str(uuid.uuid4())
            port = self._get_next_available_port()
            
            instance = LocustInstance(
                instance_id=instance_id,
                task_id=task_id,
                script_file=script_file,
                port=port,
                **kwargs
            )
            
            with self.instances_lock:
                self.instances[instance_id] = instance
            
            # 保存到数据库
            instance_data = {
                'instance_id': instance_id,
                'task_id': task_id,
                'node_id': config.CLUSTER_NODE_ID,
                'port': port,
                'status': 'starting'
            }
            db_manager.create_test_instance(instance_data)
            
            # 注册到Redis集群
            if config.CLUSTER_MODE:
                redis_manager.register_instance(instance_id, instance_data)
            
            self.logger.info(f"创建Locust实例: {instance_id}")
            return instance_id
            
        except Exception as e:
            self.logger.error(f"创建Locust实例失败: {e}")
            return None
    
    def start_instance(self, instance_id: str) -> bool:
        """启动实例"""
        with self.instances_lock:
            instance = self.instances.get(instance_id)
            if instance:
                return instance.start()
        return False
    
    def stop_instance(self, instance_id: str) -> bool:
        """停止实例"""
        with self.instances_lock:
            instance = self.instances.get(instance_id)
            if instance:
                success = instance.stop()
                if success:
                    # 从Redis集群移除
                    if config.CLUSTER_MODE:
                        redis_manager.remove_instance(instance_id)
                return success
        return False
    
    def remove_instance(self, instance_id: str) -> bool:
        """移除实例"""
        try:
            # 先停止实例
            self.stop_instance(instance_id)
            
            # 从内存中移除
            with self.instances_lock:
                if instance_id in self.instances:
                    del self.instances[instance_id]
            
            # 从Redis集群移除
            if config.CLUSTER_MODE:
                redis_manager.remove_instance(instance_id)
            
            self.logger.info(f"移除Locust实例: {instance_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"移除Locust实例失败: {e}")
            return False
    
    def get_instance(self, instance_id: str) -> Optional[LocustInstance]:
        """获取实例"""
        with self.instances_lock:
            return self.instances.get(instance_id)
    
    def get_all_instances(self) -> List[Dict]:
        """获取所有实例信息"""
        with self.instances_lock:
            return [instance.get_info() for instance in self.instances.values()]
    
    def get_instances_by_task(self, task_id: int) -> List[Dict]:
        """获取指定任务的实例"""
        with self.instances_lock:
            return [
                instance.get_info() 
                for instance in self.instances.values() 
                if instance.task_id == task_id
            ]
    
    def stop_all_instances(self) -> int:
        """停止所有实例"""
        stopped_count = 0
        with self.instances_lock:
            for instance in list(self.instances.values()):
                if instance.stop():
                    stopped_count += 1
        
        self.logger.info(f"停止了 {stopped_count} 个Locust实例")
        return stopped_count
    
    def _cleanup_worker(self):
        """清理工作线程"""
        while True:
            try:
                self._cleanup_stopped_instances()
                time.sleep(60)  # 每分钟清理一次
            except Exception as e:
                self.logger.error(f"清理线程错误: {e}")
                time.sleep(10)
    
    def _cleanup_stopped_instances(self):
        """清理已停止的实例"""
        with self.instances_lock:
            stopped_instances = []
            for instance_id, instance in self.instances.items():
                if not instance.is_running() and instance.status in ['stopped', 'failed']:
                    # 检查是否已停止超过5分钟
                    if (instance.stopped_at and 
                        (datetime.now() - instance.stopped_at).total_seconds() > 300):
                        stopped_instances.append(instance_id)
            
            for instance_id in stopped_instances:
                del self.instances[instance_id]
                self.logger.info(f"清理已停止的实例: {instance_id}")

# 创建Locust管理器实例
locust_manager = LocustManager()