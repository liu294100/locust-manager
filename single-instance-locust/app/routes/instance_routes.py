# -*- coding: utf-8 -*-
"""实例管理API路由"""

import os
from flask import Blueprint, request, jsonify, redirect
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

        # 优先使用 script_full_path（树形控件传入的完整相对路径）
        if script_full_path:
            full_script_path = os.path.normpath(os.path.join('scripts', script_full_path))
        elif script_directory and script_file:
            # 兼容旧的 directory + file 方式
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

        success, message, instance_id, port = start_locust_instance(
            script_file=full_script_path,
            target_host=target_host,
            users=int(users) if users else None,
            spawn_rate=int(spawn_rate) if spawn_rate else 1,
            run_time=run_time
        )

        if success:
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


@instance_bp.route('/api/stop/<instance_id>', methods=['POST'])
def stop_instance_api(instance_id):
    """停止指定的Locust实例"""
    try:
        success, message = stop_locust_instance(instance_id)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止失败: {str(e)}'}), 500


@instance_bp.route('/api/remove/<instance_id>', methods=['DELETE'])
def remove_instance_api(instance_id):
    """删除指定的Locust实例"""
    try:
        instance = get_instance(instance_id)
        if not instance:
            return jsonify({'success': False, 'message': '实例不存在'}), 404

        if instance.is_running():
            stop_locust_instance(instance_id)

        remove_instance(instance_id)
        return jsonify({'success': True, 'message': f'实例 {instance_id} 已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


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
