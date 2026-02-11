# -*- coding: utf-8 -*-
"""Locust实例管理服务"""

import threading
import uuid
from app.models.locust_instance import LocustInstance

BASE_PORT = 8089

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


def create_instance(script_file, target_host=None, users=None,
                    spawn_rate=None, run_time=None):
    """创建新的Locust实例"""
    instance_id = str(uuid.uuid4())[:8]
    port = get_next_available_port()

    instance = LocustInstance(
        instance_id=instance_id,
        script_file=script_file,
        port=port,
        target_host=target_host,
        users=users,
        spawn_rate=spawn_rate,
        run_time=run_time
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
                          spawn_rate=None, run_time=None):
    """启动新的Locust实例"""
    try:
        users = int(users) if users else None
        spawn_rate = int(spawn_rate) if spawn_rate else None

        instance = create_instance(script_file, target_host, users,
                                   spawn_rate, run_time)
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
