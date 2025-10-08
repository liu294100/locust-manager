# -*- coding: utf-8 -*-
"""
Redis集群管理模块
负责集群节点管理、任务分发、状态同步等功能
"""

import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import redis
from .config import config

class RedisClusterManager:
    """Redis集群管理器"""
    
    def __init__(self):
        self.redis_client = None
        self.node_id = config.CLUSTER_NODE_ID
        self.heartbeat_interval = config.CLUSTER_HEARTBEAT_INTERVAL
        self.logger = logging.getLogger(__name__)
        self._heartbeat_thread = None
        self._running = False
        
        # Redis键前缀
        self.KEYS = {
            'nodes': 'cluster:nodes',
            'tasks': 'cluster:tasks',
            'instances': 'cluster:instances',
            'heartbeat': f'cluster:heartbeat:{self.node_id}',
            'node_info': f'cluster:node:{self.node_id}',
            'task_queue': 'cluster:task_queue',
            'result_queue': 'cluster:result_queue'
        }
        
        self.connect()
    
    def connect(self):
        """连接Redis"""
        try:
            self.redis_client = redis.Redis(**config.get_redis_config())
            # 测试连接
            self.redis_client.ping()
            self.logger.info("Redis连接成功")
            return True
        except Exception as e:
            self.logger.error(f"Redis连接失败: {e}")
            return False
    
    def start_heartbeat(self):
        """启动心跳线程"""
        if not self._running:
            self._running = True
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
            self._heartbeat_thread.start()
            self.logger.info(f"节点 {self.node_id} 心跳线程已启动")
    
    def stop_heartbeat(self):
        """停止心跳线程"""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        self.logger.info(f"节点 {self.node_id} 心跳线程已停止")
    
    def _heartbeat_worker(self):
        """心跳工作线程"""
        while self._running:
            try:
                self.send_heartbeat()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                self.logger.error(f"心跳发送失败: {e}")
                time.sleep(5)  # 错误时短暂等待
    
    def send_heartbeat(self):
        """发送心跳信息"""
        try:
            heartbeat_data = {
                'node_id': self.node_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'online',
                'cpu_usage': self._get_cpu_usage(),
                'memory_usage': self._get_memory_usage(),
                'active_instances': self.get_node_instance_count()
            }
            
            # 设置心跳信息，过期时间为心跳间隔的3倍
            self.redis_client.setex(
                self.KEYS['heartbeat'], 
                self.heartbeat_interval * 3, 
                json.dumps(heartbeat_data)
            )
            
            # 更新节点信息到集群节点列表
            self.redis_client.hset(self.KEYS['nodes'], self.node_id, json.dumps(heartbeat_data))
            
        except Exception as e:
            self.logger.error(f"发送心跳失败: {e}")
    
    def _get_cpu_usage(self) -> float:
        """获取CPU使用率（简化实现）"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """获取内存使用率（简化实现）"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
    
    def get_online_nodes(self) -> List[Dict]:
        """获取在线节点列表"""
        try:
            nodes = []
            node_data = self.redis_client.hgetall(self.KEYS['nodes'])
            
            for node_id, data in node_data.items():
                try:
                    node_info = json.loads(data)
                    # 检查心跳是否过期
                    heartbeat_time = datetime.fromisoformat(node_info['timestamp'])
                    if datetime.now() - heartbeat_time < timedelta(seconds=self.heartbeat_interval * 3):
                        nodes.append(node_info)
                    else:
                        # 移除过期节点
                        self.redis_client.hdel(self.KEYS['nodes'], node_id)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
            
            return nodes
        except Exception as e:
            self.logger.error(f"获取在线节点失败: {e}")
            return []
    
    def register_task(self, task_id: int, task_data: Dict) -> bool:
        """注册压测任务到集群"""
        try:
            task_info = {
                'task_id': task_id,
                'created_by_node': self.node_id,
                'created_at': datetime.now().isoformat(),
                'status': 'pending',
                **task_data
            }
            
            self.redis_client.hset(self.KEYS['tasks'], str(task_id), json.dumps(task_info))
            
            # 如果是集群模式，添加到任务队列
            if task_data.get('cluster_mode', False):
                self.redis_client.lpush(self.KEYS['task_queue'], json.dumps(task_info))
            
            self.logger.info(f"任务 {task_id} 已注册到集群")
            return True
        except Exception as e:
            self.logger.error(f"注册任务失败: {e}")
            return False
    
    def update_task_status(self, task_id: int, status: str, **kwargs) -> bool:
        """更新任务状态"""
        try:
            task_key = str(task_id)
            task_data = self.redis_client.hget(self.KEYS['tasks'], task_key)
            
            if task_data:
                task_info = json.loads(task_data)
                task_info['status'] = status
                task_info['updated_at'] = datetime.now().isoformat()
                task_info.update(kwargs)
                
                self.redis_client.hset(self.KEYS['tasks'], task_key, json.dumps(task_info))
                return True
            return False
        except Exception as e:
            self.logger.error(f"更新任务状态失败: {e}")
            return False
    
    def get_pending_tasks(self) -> List[Dict]:
        """获取待处理的任务"""
        try:
            tasks = []
            # 从任务队列获取待处理任务
            while True:
                task_data = self.redis_client.rpop(self.KEYS['task_queue'])
                if not task_data:
                    break
                
                try:
                    task_info = json.loads(task_data)
                    tasks.append(task_info)
                except json.JSONDecodeError:
                    continue
            
            return tasks
        except Exception as e:
            self.logger.error(f"获取待处理任务失败: {e}")
            return []
    
    def register_instance(self, instance_id: str, instance_data: Dict) -> bool:
        """注册压测实例"""
        try:
            instance_info = {
                'instance_id': instance_id,
                'node_id': self.node_id,
                'created_at': datetime.now().isoformat(),
                'last_heartbeat': datetime.now().isoformat(),
                **instance_data
            }
            
            self.redis_client.hset(self.KEYS['instances'], instance_id, json.dumps(instance_info))
            self.logger.info(f"实例 {instance_id} 已注册到集群")
            return True
        except Exception as e:
            self.logger.error(f"注册实例失败: {e}")
            return False
    
    def update_instance_status(self, instance_id: str, status: str, **kwargs) -> bool:
        """更新实例状态"""
        try:
            instance_data = self.redis_client.hget(self.KEYS['instances'], instance_id)
            
            if instance_data:
                instance_info = json.loads(instance_data)
                instance_info['status'] = status
                instance_info['last_heartbeat'] = datetime.now().isoformat()
                instance_info.update(kwargs)
                
                self.redis_client.hset(self.KEYS['instances'], instance_id, json.dumps(instance_info))
                return True
            return False
        except Exception as e:
            self.logger.error(f"更新实例状态失败: {e}")
            return False
    
    def remove_instance(self, instance_id: str) -> bool:
        """移除实例"""
        try:
            self.redis_client.hdel(self.KEYS['instances'], instance_id)
            self.logger.info(f"实例 {instance_id} 已从集群移除")
            return True
        except Exception as e:
            self.logger.error(f"移除实例失败: {e}")
            return False
    
    def get_node_instances(self, node_id: str = None) -> List[Dict]:
        """获取节点的实例列表"""
        try:
            if node_id is None:
                node_id = self.node_id
            
            instances = []
            instance_data = self.redis_client.hgetall(self.KEYS['instances'])
            
            for instance_id, data in instance_data.items():
                try:
                    instance_info = json.loads(data)
                    if instance_info.get('node_id') == node_id:
                        instances.append(instance_info)
                except json.JSONDecodeError:
                    continue
            
            return instances
        except Exception as e:
            self.logger.error(f"获取节点实例失败: {e}")
            return []
    
    def get_node_instance_count(self, node_id: str = None) -> int:
        """获取节点的实例数量"""
        return len(self.get_node_instances(node_id))
    
    def get_cluster_nodes(self) -> List[Dict]:
        """获取集群节点列表"""
        try:
            return self.get_online_nodes()
        except Exception as e:
            self.logger.error(f"获取集群节点失败: {e}")
            return []
    
    def get_cluster_stats(self) -> Dict:
        """获取集群统计信息"""
        try:
            online_nodes = self.get_online_nodes()
            total_instances = len(self.redis_client.hgetall(self.KEYS['instances']))
            total_tasks = len(self.redis_client.hgetall(self.KEYS['tasks']))
            pending_tasks = self.redis_client.llen(self.KEYS['task_queue'])
            
            return {
                'online_nodes': len(online_nodes),
                'total_instances': total_instances,
                'total_tasks': total_tasks,
                'pending_tasks': pending_tasks,
                'nodes': online_nodes
            }
        except Exception as e:
            self.logger.error(f"获取集群统计失败: {e}")
            return {}
    
    def publish_message(self, channel: str, message: Dict) -> bool:
        """发布消息到指定频道"""
        try:
            self.redis_client.publish(channel, json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"发布消息失败: {e}")
            return False
    
    def subscribe_channel(self, channel: str, callback):
        """订阅频道消息"""
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(channel)
            
            def message_handler():
                for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            callback(data)
                        except json.JSONDecodeError:
                            continue
            
            thread = threading.Thread(target=message_handler, daemon=True)
            thread.start()
            return pubsub
        except Exception as e:
            self.logger.error(f"订阅频道失败: {e}")
            return None
    
    def cleanup_expired_data(self):
        """清理过期数据"""
        try:
            # 清理过期的实例
            instance_data = self.redis_client.hgetall(self.KEYS['instances'])
            for instance_id, data in instance_data.items():
                try:
                    instance_info = json.loads(data)
                    last_heartbeat = datetime.fromisoformat(instance_info['last_heartbeat'])
                    if datetime.now() - last_heartbeat > timedelta(minutes=5):
                        self.redis_client.hdel(self.KEYS['instances'], instance_id)
                        self.logger.info(f"清理过期实例: {instance_id}")
                except (json.JSONDecodeError, KeyError, ValueError):
                    self.redis_client.hdel(self.KEYS['instances'], instance_id)
            
            # 清理过期的节点
            node_data = self.redis_client.hgetall(self.KEYS['nodes'])
            for node_id, data in node_data.items():
                try:
                    node_info = json.loads(data)
                    heartbeat_time = datetime.fromisoformat(node_info['timestamp'])
                    if datetime.now() - heartbeat_time > timedelta(seconds=self.heartbeat_interval * 3):
                        self.redis_client.hdel(self.KEYS['nodes'], node_id)
                        self.logger.info(f"清理过期节点: {node_id}")
                except (json.JSONDecodeError, KeyError, ValueError):
                    self.redis_client.hdel(self.KEYS['nodes'], node_id)
                    
        except Exception as e:
            self.logger.error(f"清理过期数据失败: {e}")

# 创建Redis集群管理器实例
redis_manager = RedisClusterManager()