# -*- coding: utf-8 -*-
"""实例管理API路由"""

import os
from flask import Blueprint, request, jsonify, redirect, send_file
from app.auth import login_required
from app.services.instance_manager import (
    get_all_instances, get_instance, start_locust_instance,
    stop_locust_instance, stop_all_instances, remove_instance,
    cleanup_stopped_instances
)

instance_bp = Blueprint('instance', __name__)


@instance_bp.route('/api/instances')
def get_instances_api():
    """获取所有实例信息"""
    try:
        from app.config import is_cluster_enabled
        
        if is_cluster_enabled():
            # 集群模式：获取所有节点的实例
            try:
                from app.cluster import cluster_manager, node_registry
                
                # 获取集群实例
                cluster_instances = cluster_manager.get_all_cluster_instances()
                
                # 同时获取当前节点的本地实例（兼容旧数据）
                local_instances = get_all_instances()
                
                # 当前节点 ID
                current_node_id = node_registry.get_node_id()
                
                # 合并去重：按 instance_id 和 port 双重去重
                # 只展示已就绪的集群实例（pending 的还没真正启动，不显示）
                ready_cluster_instances = [ci for ci in cluster_instances if ci.status in ('running', 'error')]
                cluster_ids = {ci.instance_id for ci in ready_cluster_instances}
                # 收集集群实例中当前节点的端口号，用于过滤本地重复
                cluster_ports = set()
                for ci in ready_cluster_instances:
                    if ci.node_id == current_node_id and ci.port and ci.port > 0:
                        cluster_ports.add(ci.port)
                
                all_instances = [ci.to_dict() for ci in ready_cluster_instances]
                
                # 添加本地实例中不在集群记录中的（按 ID 和端口双重过滤）
                for inst in local_instances:
                    if inst['instance_id'] in cluster_ids:
                        continue
                    # 端口已被集群实例占用，说明是同一个进程的重复记录
                    if inst.get('port') and inst['port'] in cluster_ports:
                        continue
                    inst['node_id'] = current_node_id
                    all_instances.append(inst)
                
                return jsonify({'instances': all_instances})
            except Exception as e:
                print(f"获取集群实例失败，降级为本地: {e}")
                # 降级为本地实例
                instances = get_all_instances()
                return jsonify({'instances': instances})
        else:
            # 单机模式
            instances = get_all_instances()
            return jsonify({'instances': instances})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@instance_bp.route('/api/start', methods=['POST'])
def start_api():
    """启动新的Locust实例"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400

        script_full_path = data.get('script_full_path', '').strip()
        script_directory = data.get('script_directory', '').strip()
        script_file = data.get('script_file', '').strip()
        target_host = data.get('target_host')
        users = data.get('users')
        spawn_rate = data.get('spawn_rate', 1)
        run_time = data.get('run_time')
        load_mode = data.get('load_mode', 'fixed')

        # 优先使用 script_full_path（树形控件传入的完整相对路径）
        if script_full_path:
            full_script_path = os.path.normpath(os.path.join('scripts', script_full_path))
        elif script_directory and script_file:
            if script_directory == '根目录':
                full_script_path = os.path.join('scripts', script_file)
            elif script_directory == '临时文件':
                full_script_path = os.path.join('scripts', 'tmp', script_file)
            else:
                normalized_directory = os.path.normpath(script_directory)
                full_script_path = os.path.join('scripts', normalized_directory, script_file)
            full_script_path = os.path.normpath(full_script_path)
        else:
            return jsonify({'success': False, 'message': '请选择脚本文件'}), 400

        if not os.path.exists(full_script_path):
            return jsonify({'success': False, 'message': f'脚本文件不存在: {full_script_path}'}), 400

        # 递增模式：生成 LoadTestShape 包装脚本
        if load_mode == 'step':
            step_users = data.get('step_users') or 100
            step_increment = data.get('step_increment') or 10
            step_interval = data.get('step_interval_seconds') or data.get('step_interval') or 60
            
            # 转换为整数，处理空字符串
            step_users = int(step_users) if step_users else 100
            step_increment = int(step_increment) if step_increment else 10
            step_interval = int(step_interval) if step_interval else 60
            step_spawn_rate = step_increment  # 每秒生成的用户数 = 每次递增用户数

            wrapper_path = _generate_step_wrapper(
                full_script_path, step_users, step_increment, step_interval, step_spawn_rate
            )
            full_script_path = wrapper_path
            # 递增模式不传 users/spawn_rate，由 Shape 控制
            users = None
            spawn_rate = None

        success, message, instance_id, port = start_locust_instance(
            script_file=full_script_path,
            target_host=target_host,
            users=int(users) if users else None,
            spawn_rate=int(spawn_rate) if spawn_rate else 1,
            run_time=run_time
        )

        if success:
            # 集群模式下，将实例注册到 Redis
            _register_instance_to_cluster(instance_id, full_script_path, port, target_host, users, spawn_rate, run_time)
            
            return jsonify({
                'success': True,
                'message': f'实例启动成功！实例ID: {instance_id}，端口: {port}',
                'instance_id': instance_id,
                'port': port
            })
        else:
            return jsonify({'success': False, 'message': message}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动失败: {str(e)}'}), 500


def _register_instance_to_cluster(instance_id, script_file, port, target_host, users, spawn_rate, run_time):
    """将实例注册到集群 Redis"""
    try:
        from app.config import is_cluster_enabled
        if not is_cluster_enabled():
            return
            
        from app.cluster import node_registry
        from app.cluster.cluster_manager import ClusterInstance
        from app.cluster.redis_client import redis_client
        from datetime import datetime
        
        node_id = node_registry.get_node_id()
        node = node_registry.get_current_node()
        now = datetime.now().isoformat()
        
        cluster_inst = ClusterInstance(
            instance_id=instance_id,
            node_id=node_id,
            script_file=script_file,
            port=port,
            target_host=target_host,
            users=users,
            spawn_rate=spawn_rate,
            run_time=run_time,
            mode='standalone',
            master_host=None,
            master_port=None,
            status='running',
            created_at=now,
            updated_at=now,
            web_url=f"http://{node.ip_address}:{port}" if node else None,
            workers=[]
        )
        
        redis_client.hset("locust:cluster:instances", instance_id, cluster_inst.to_dict())
        print(f"✅ 实例 {instance_id} 已注册到集群")
    except Exception as e:
        print(f"⚠️ 注册实例到集群失败: {e}")


def _generate_step_wrapper(original_script, max_users, step_increment, step_interval, spawn_rate):
    """生成递增压测的 LoadTestShape 包装脚本"""
    import tempfile
    wrapper_content = f'''# 自动生成的递增压测包装脚本
import importlib.util, os, sys

# 导入原始脚本
_spec = importlib.util.spec_from_file_location("original", r"{os.path.abspath(original_script)}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["original"] = _mod
_spec.loader.exec_module(_mod)

# 把原始脚本的所有 locust 类导入当前模块
for _name in dir(_mod):
    _obj = getattr(_mod, _name)
    if isinstance(_obj, type) and hasattr(_obj, 'wait_time'):
        globals()[_name] = _obj

from locust import LoadTestShape

class StepLoadShape(LoadTestShape):
    """递增压测：从0开始，每 {step_interval}s 增加 {step_increment} 用户，最多 {max_users} 用户"""
    max_users = {max_users}
    step_increment = {step_increment}
    step_interval = {step_interval}
    spawn_rate = {spawn_rate}

    def tick(self):
        run_time = self.get_run_time()
        current_step = int(run_time // self.step_interval) + 1
        target_users = min(current_step * self.step_increment, self.max_users)
        return (target_users, self.spawn_rate)
'''
    # 写到临时目录
    tmp_dir = os.path.join(os.getcwd(), 'scripts', 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    wrapper_path = os.path.join(tmp_dir, f'_step_wrapper_{os.getpid()}.py')
    with open(wrapper_path, 'w', encoding='utf-8') as f:
        f.write(wrapper_content)
    return wrapper_path


@instance_bp.route('/api/stop/<instance_id>', methods=['POST'])
def stop_instance_api(instance_id):
    """停止指定的Locust实例"""
    try:
        from app.config import is_cluster_enabled
        
        # 集群实例（cluster- 开头）走集群停止逻辑
        if is_cluster_enabled() and instance_id.startswith('cluster-'):
            from app.cluster import cluster_manager
            success, message = cluster_manager.stop_cluster_instance(instance_id)
            return jsonify({'success': success, 'message': message})
        
        # 本地实例走本地停止
        success, message = stop_locust_instance(instance_id)
        
        # 集群模式下，同时从 Redis 删除实例记录
        if success:
            _remove_cluster_instance(instance_id)
        
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止失败: {str(e)}'}), 500


def _update_cluster_instance_status(instance_id, status):
    """更新集群实例状态（已废弃，停止时直接删除）"""
    try:
        from app.config import is_cluster_enabled
        if not is_cluster_enabled():
            return
            
        from app.cluster.redis_client import redis_client
        from datetime import datetime
        import json
        
        data = redis_client.hget_json("locust:cluster:instances", instance_id)
        if data:
            data['status'] = status
            data['updated_at'] = datetime.now().isoformat()
            redis_client.hset("locust:cluster:instances", instance_id, data)
    except Exception as e:
        print(f"⚠️ 更新集群实例状态失败: {e}")


@instance_bp.route('/api/remove/<instance_id>', methods=['DELETE'])
def remove_instance_api(instance_id):
    """删除指定的Locust实例"""
    try:
        instance = get_instance(instance_id)
        if not instance:
            # 可能是其他节点的实例，尝试从集群中删除
            _remove_cluster_instance(instance_id)
            return jsonify({'success': True, 'message': f'实例 {instance_id} 已从集群删除'})

        if instance.is_running():
            stop_locust_instance(instance_id)

        remove_instance(instance_id)
        _remove_cluster_instance(instance_id)
        
        return jsonify({'success': True, 'message': f'实例 {instance_id} 已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


def _remove_cluster_instance(instance_id):
    """从集群中删除实例记录"""
    try:
        from app.config import is_cluster_enabled
        if not is_cluster_enabled():
            return
            
        from app.cluster.redis_client import redis_client
        redis_client.hdel("locust:cluster:instances", instance_id)
    except Exception as e:
        print(f"⚠️ 从集群删除实例失败: {e}")


@instance_bp.route('/api/stop_all', methods=['POST'])
def stop_all_api():
    """停止所有Locust实例"""
    try:
        results = stop_all_instances()
        return jsonify({'success': True, 'message': f'已停止 {len(results)} 个实例', 'stopped_count': len(results)})
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止失败: {str(e)}'}), 500


@instance_bp.route('/api/cleanup', methods=['POST'])
@login_required
def cleanup_api():
    """清理已停止的实例"""
    count = cleanup_stopped_instances()
    return jsonify({'success': True, 'message': f'已清理 {count} 个停止的实例'})


@instance_bp.route('/instances')
@login_required
def get_instances_page():
    """获取所有实例状态（旧路由兼容）"""
    from datetime import datetime
    instances = get_all_instances()
    return jsonify({
        'instances': instances,
        'count': len(instances),
        'timestamp': datetime.now().isoformat()
    })


@instance_bp.route('/open/<instance_id>')
def open_instance_ui(instance_id):
    """重定向到指定实例的Web UI"""
    instance = get_instance(instance_id)
    if not instance:
        return jsonify({'error': '实例不存在'}), 404
    if not instance.is_running():
        return jsonify({'error': '实例未运行'}), 503
    return redirect(f'http://localhost:{instance.port}')


@instance_bp.route('/api/logs/<instance_id>')
@login_required
def download_logs(instance_id):
    """下载指定实例的完整日志"""
    try:
        instance = get_instance(instance_id)
        if not instance:
            return jsonify({'error': '实例不存在'}), 404

        log_file = getattr(instance, 'log_file', None)
        if not log_file or not os.path.exists(log_file):
            return jsonify({'error': '日志文件不存在'}), 404

        return send_file(
            log_file,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'locust_{instance_id}.log'
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500
