# -*- coding: utf-8 -*-
"""Locust实例管理服务"""

import threading
import uuid
from app.models.locust_instance import LocustInstance

BASE_PORT = 8089
MASTER_PORT = 5557  # Locust Master 通信端口

# 多实例管理
locust_instances = {}
instances_lock = threading.Lock()


def get_next_available_port():
    """获取下一个可用端口"""
    with instances_lock:
        used_ports = {inst.port for inst in locust_instances.values()}
        port = BASE_PORT
        while port in used_ports:
            port += 1
        return port


def get_next_master_port():
    """获取下一个可用的 Master 通信端口"""
    with instances_lock:
        used_ports = set()
        for inst in locust_instances.values():
            if hasattr(inst, 'master_bind_port') and inst.master_bind_port:
                used_ports.add(inst.master_bind_port)
        port = MASTER_PORT
        while port in used_ports:
            port += 2  # 每个 master 使用两个端口
        return port


def create_instance(script_file, target_host=None, users=None,
                    spawn_rate=None, run_time=None, mode='standalone',
                    master_host=None, master_port=None, expect_workers=0,
                    worker_processes=1):
    """创建新的Locust实例
    
    Args:
        script_file: 脚本文件路径
        target_host: 目标主机
        users: 用户数
        spawn_rate: 生成速率
        run_time: 运行时间
        mode: 运行模式 ('standalone' | 'master' | 'worker')
        master_host: Master 主机地址（Worker 模式时使用）
        master_port: Master 端口（Worker 模式时使用）
        expect_workers: 期望的 Worker 数量（Master 模式时使用）
        worker_processes: Worker 模式下每个节点启动的进程数
    """
    instance_id = str(uuid.uuid4())[:8]
    
    # Worker 模式不需要 Web 端口
    if mode == 'worker':
        port = 0
    else:
        port = get_next_available_port()
    
    # Master 模式需要分配通信端口
    master_bind_port = None
    if mode == 'master':
        master_bind_port = get_next_master_port()

    instance = LocustInstance(
        instance_id=instance_id,
        script_file=script_file,
        port=port,
        target_host=target_host,
        users=users,
        spawn_rate=spawn_rate,
        run_time=run_time,
        mode=mode,
        master_host=master_host,
        master_port=master_port,
        master_bind_port=master_bind_port,
        expect_workers=expect_workers,
        worker_processes=worker_processes
    )

    with instances_lock:
        locust_instances[instance_id] = instance

    return instance


def get_instance(instance_id):
    """获取指定实例"""
    with instances_lock:
        return locust_instances.get(instance_id)


def get_all_instances():
    """获取所有实例信息"""
    with instances_lock:
        return [inst.get_info() for inst in locust_instances.values()]


def remove_instance(instance_id):
    """移除实例"""
    with instances_lock:
        instance = locust_instances.get(instance_id)
        if instance:
            if instance.is_running():
                instance.stop()
            del locust_instances[instance_id]
            return True
        return False


def cleanup_stopped_instances():
    """清理已停止的实例"""
    with instances_lock:
        stopped = [iid for iid, inst in locust_instances.items()
                   if not inst.is_running() and inst.status == 'stopped']
        for iid in stopped:
            del locust_instances[iid]
        return len(stopped)


def start_locust_instance(script_file, target_host=None, users=None,
                          spawn_rate=None, run_time=None, mode='standalone',
                          master_host=None, master_port=None, expect_workers=0,
                          worker_processes=1):
    """启动新的Locust实例
    
    Args:
        script_file: 脚本文件路径
        target_host: 目标主机
        users: 用户数
        spawn_rate: 生成速率
        run_time: 运行时间
        mode: 运行模式 ('standalone' | 'master' | 'worker')
        master_host: Master 主机地址（Worker 模式时使用）
        master_port: Master 端口（Worker 模式时使用）
        expect_workers: 期望的 Worker 数量（Master 模式时使用）
        worker_processes: Worker 模式下每个节点启动的进程数
    """
    try:
        users = int(users) if users else None
        spawn_rate = int(spawn_rate) if spawn_rate else None

        instance = create_instance(
            script_file, target_host, users,
            spawn_rate, run_time, mode,
            master_host, master_port, expect_workers,
            worker_processes
        )
        success, message = instance.start()

        if success:
            return True, message, instance.instance_id, instance.port
        else:
            remove_instance(instance.instance_id)
            return False, message, None, None
    except ValueError:
        return False, "用户数和生成速率必须是数字", None, None
    except Exception as e:
        return False, f"创建实例失败: {str(e)}", None, None


def stop_locust_instance(instance_id):
    """停止指定的Locust实例"""
    instance = get_instance(instance_id)
    if not instance:
        return False, "实例不存在"
    return instance.stop()


def stop_all_instances():
    """停止所有实例"""
    with instances_lock:
        results = []
        for instance_id, instance in locust_instances.items():
            if instance.is_running():
                success, message = instance.stop()
                results.append(f"实例 {instance_id}: {message}")
        return results
