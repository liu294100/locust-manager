# -*- coding: utf-8 -*-
"""
压测服务管理器主应用
Flask应用入口文件
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
import requests
from app.config import config
from app.database import db_manager
from app.redis_manager import redis_manager
from app.auth import login_required, admin_required, authenticate_user, create_session, clear_session, get_current_user
from app.locust_manager import locust_manager
from app.script_manager import script_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# 配置上传文件大小限制
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# 应用初始化标志
_app_initialized = False

@app.before_request
def initialize_app():
    """应用初始化"""
    global _app_initialized
    if not _app_initialized:
        try:
            # 初始化数据库连接
            db_manager.connect()
            
            # 如果启用集群模式，启动Redis心跳
            if config.CLUSTER_MODE:
                redis_manager.start_heartbeat()
            
            logging.info("应用初始化完成")
            _app_initialized = True
        except Exception as e:
            logging.error(f"应用初始化失败: {e}")

@app.context_processor
def inject_current_user():
    """向所有模板注入current_user变量"""
    return {'current_user': get_current_user()}

@app.template_filter('format_bytes')
def format_bytes(bytes_value):
    """格式化字节数为人类可读格式"""
    if not bytes_value or bytes_value == 0:
        return "0 B"
    
    try:
        bytes_value = float(bytes_value)
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        
        while bytes_value >= 1024 and unit_index < len(units) - 1:
            bytes_value /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(bytes_value)} {units[unit_index]}"
        else:
            return f"{bytes_value:.1f} {units[unit_index]}"
    except (ValueError, TypeError):
        return "0 B"

@app.teardown_appcontext
def close_db(error):
    """关闭数据库连接"""
    try:
        if hasattr(db_manager, 'connection') and db_manager.connection and db_manager.connection.open:
            db_manager.connection.close()
    except Exception as e:
        # 忽略连接已关闭的错误
        pass

# ==================== 认证路由 ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('login.html')
        
        success, message, user_info = authenticate_user(username, password)
        if success and user_info:
            create_session(user_info)
            flash('登录成功', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """用户登出"""
    clear_session()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))

# ==================== 主页面路由 ====================

@app.route('/')
@login_required
def dashboard():
    """仪表板"""
    try:
        # 获取统计数据
        stats = db_manager.get_dashboard_stats()
        
        # 获取集群状态
        cluster_stats = {}
        if config.CLUSTER_MODE:
            cluster_stats = redis_manager.get_cluster_stats()
        
        # 获取最近的任务
        recent_tasks = db_manager.get_recent_tasks(limit=10)
        
        # 获取活跃实例
        active_instances = locust_manager.get_all_instances()
        
        return render_template('dashboard.html', 
                             stats=stats,
                             cluster_stats=cluster_stats,
                             recent_tasks=recent_tasks,
                             active_instances=active_instances)
    except Exception as e:
        logging.error(f"获取仪表板数据失败: {e}")
        flash('获取数据失败', 'error')
        # 在错误情况下提供默认的空数据
        return render_template('dashboard.html',
                             stats={'tasks': {}, 'cluster': {}, 'recent_logs': []},
                             cluster_stats={},
                             recent_tasks=[],
                             active_instances=[])

@app.route('/tasks')
@login_required
def tasks():
    """任务列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        tasks = db_manager.get_tasks_paginated(page, per_page)
        return render_template('tasks.html', tasks=tasks)
    except Exception as e:
        logging.error(f"获取任务列表失败: {e}")
        flash('获取任务列表失败', 'error')
        return render_template('tasks.html', tasks=[])

@app.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task():
    """创建任务"""
    if request.method == 'POST':
        try:
            user = get_current_user()
            task_data = {
                'task_name': request.form.get('name'),
                'description': request.form.get('description', ''),
                'script_file': request.form.get('script_file'),
                'target_host': request.form.get('target_host'),
                'users': request.form.get('users', type=int),
                'spawn_rate': request.form.get('spawn_rate', type=float),
                'run_time': request.form.get('run_time', type=int),
                'created_by': user['id']
            }
            
            # 验证必填字段
            if not all([task_data['task_name'], task_data['script_file'], task_data['target_host']]):
                flash('请填写所有必填字段', 'error')
                return redirect(url_for('create_task'))
            
            task_id = db_manager.create_test_task(task_data)
            if task_id:
                flash('任务创建成功', 'success')
                return redirect(url_for('task_detail', task_id=task_id))
            else:
                flash('任务创建失败', 'error')
                
        except Exception as e:
            logging.error(f"创建任务失败: {e}")
            flash('创建任务失败', 'error')
    
    # 获取可用脚本
    try:
        scripts = script_manager.get_all_scripts()
    except Exception as e:
        logging.error(f"获取脚本列表失败: {e}")
        scripts = []
        flash('获取脚本列表失败', 'warning')
    
    return render_template('create_task.html', scripts=scripts)

@app.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    """任务详情"""
    try:
        task = db_manager.get_test_task(task_id)
        if not task:
            flash('任务不存在', 'error')
            return redirect(url_for('tasks'))
        
        # 获取任务实例
        instances = locust_manager.get_instances_by_task(task_id)
        
        # 获取任务结果
        results = db_manager.get_task_results(task_id)
        
        return render_template('task_detail.html', 
                             task=task, 
                             instances=instances, 
                             results=results)
    except Exception as e:
        logging.error(f"获取任务详情失败: {e}")
        flash('获取任务详情失败', 'error')
        return redirect(url_for('tasks'))

@app.route('/tasks/<int:task_id>/start', methods=['POST'])
@login_required
def start_task(task_id):
    """启动任务"""
    try:
        task = db_manager.get_test_task(task_id)
        if not task:
            return jsonify({'success': False, 'message': '任务不存在'})
        
        # 获取脚本文件
        script = script_manager.get_script(task['script_id'])
        if not script:
            return jsonify({'success': False, 'message': '脚本文件不存在'})
        
        # 创建实例
        instance_id = locust_manager.create_instance(
            task_id=task_id,
            script_file=script['file_path'],
            target_host=task['target_host'],
            users=task['users'],
            spawn_rate=task['spawn_rate'],
            run_time=task['run_time']
        )
        
        if instance_id:
            # 启动实例
            if locust_manager.start_instance(instance_id):
                # 更新任务状态
                db_manager.update_task_status(task_id, 'running')
                return jsonify({'success': True, 'instance_id': instance_id})
            else:
                return jsonify({'success': False, 'message': '启动实例失败'})
        else:
            return jsonify({'success': False, 'message': '创建实例失败'})
            
    except Exception as e:
        logging.error(f"启动任务失败: {e}")
        return jsonify({'success': False, 'message': '启动任务失败'})

@app.route('/tasks/<int:task_id>/stop', methods=['POST'])
@login_required
def stop_task(task_id):
    """停止任务"""
    try:
        # 获取任务的所有实例
        instances = locust_manager.get_instances_by_task(task_id)
        stopped_count = 0
        
        for instance in instances:
            if locust_manager.stop_instance(instance['instance_id']):
                stopped_count += 1
        
        # 更新任务状态
        db_manager.update_task_status(task_id, 'stopped')
        
        return jsonify({
            'success': True, 
            'message': f'已停止 {stopped_count} 个实例'
        })
        
    except Exception as e:
        logging.error(f"停止任务失败: {e}")
        return jsonify({'success': False, 'message': '停止任务失败'})

# ==================== 脚本管理路由 ====================

@app.route('/scripts')
@login_required
def scripts():
    """脚本列表"""
    try:
        user = get_current_user()
        # 管理员可以看到所有脚本，普通用户只能看到自己的
        user_id = None if user.get('role') == 'admin' else user['id']
        scripts = script_manager.get_all_scripts(user_id)
        return render_template('scripts.html', scripts=scripts)
    except Exception as e:
        logging.error(f"获取脚本列表失败: {e}")
        flash('获取脚本列表失败', 'error')
        return render_template('scripts.html', scripts=[])

@app.route('/scripts/upload', methods=['GET', 'POST'])
@login_required
def upload_script():
    """上传脚本"""
    if request.method == 'POST':
        try:
            # 检查是否为AJAX请求
            is_ajax = request.headers.get('Content-Type', '').startswith('multipart/form-data') and \
                     request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                     'application/json' in request.headers.get('Accept', '')
            
            if 'file' not in request.files:
                if is_ajax:
                    return jsonify({'error': '请选择文件'})
                flash('请选择文件', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                if is_ajax:
                    return jsonify({'error': '请选择文件'})
                flash('请选择文件', 'error')
                return redirect(request.url)
            
            description = request.form.get('description', '')
            user = get_current_user()
            
            script = script_manager.upload_script(file, user['id'], description)
            if script:
                if is_ajax:
                    return jsonify({'success': True, 'message': '脚本上传成功', 'script': script})
                flash('脚本上传成功', 'success')
                return redirect(url_for('scripts'))
            else:
                if is_ajax:
                    return jsonify({'error': '脚本上传失败'})
                flash('脚本上传失败', 'error')
                
        except Exception as e:
            logging.error(f"上传脚本失败: {e}")
            error_msg = f'上传失败: {str(e)}'
            if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
                return jsonify({'error': error_msg})
            flash(error_msg, 'error')
    
    return render_template('upload_script.html')

@app.route('/scripts/<int:script_id>/view')
@login_required
def view_script(script_id):
    """查看脚本"""
    try:
        script = script_manager.get_script(script_id)
        if not script:
            flash('脚本不存在', 'error')
            return redirect(url_for('scripts'))
        
        content = script_manager.get_script_content(script_id)
        return render_template('view_script.html', script=script, content=content)
    except Exception as e:
        logging.error(f"查看脚本失败: {e}")
        flash('查看脚本失败', 'error')
        return redirect(url_for('scripts'))

@app.route('/scripts/view/<filename>')
@login_required
def view_script_by_filename(filename):
    """通过文件名查看脚本"""
    try:
        script = script_manager.get_script_by_filename(filename)
        if not script:
            flash('脚本不存在', 'error')
            return redirect(url_for('scripts'))
        
        content = script_manager.get_script_content_by_filename(filename)
        return render_template('view_script.html', script=script, content=content)
    except Exception as e:
        logging.error(f"查看脚本失败: {e}")
        flash('查看脚本失败', 'error')
        return redirect(url_for('scripts'))

@app.route('/scripts/<filename>/content')
@login_required
def get_script_content(filename):
    """获取脚本内容（API）"""
    try:
        content = script_manager.get_script_content_by_filename(filename)
        if content is None:
            return jsonify({'error': '脚本不存在'}), 404
        return jsonify({'content': content})
    except Exception as e:
        logging.error(f"获取脚本内容失败: {e}")
        return jsonify({'error': '获取脚本内容失败'}), 500

@app.route('/scripts/<int:script_id>/delete', methods=['POST'])
@login_required
def delete_script(script_id):
    """删除脚本"""
    try:
        user = get_current_user()
        # 管理员可以删除任何脚本，普通用户只能删除自己的
        user_id = None if user.get('role') == 'admin' else user['id']
        
        if script_manager.delete_script(script_id, user_id):
            flash('脚本删除成功', 'success')
        else:
            flash('脚本删除失败', 'error')
            
    except Exception as e:
        logging.error(f"删除脚本失败: {e}")
        flash('删除脚本失败', 'error')
    
    return redirect(url_for('scripts'))

# ==================== 实例管理路由 ====================

@app.route('/instances')
@login_required
def instances():
    """实例列表"""
    try:
        instances = locust_manager.get_all_instances()
        # 计算实例统计信息
        stats = {
            'total': len(instances),
            'running': len([i for i in instances if i.get('status') == 'running']),
            'stopped': len([i for i in instances if i.get('status') == 'stopped']),
            'error': len([i for i in instances if i.get('status') == 'error'])
        }
        return render_template('instances.html', instances=instances, stats=stats)
    except Exception as e:
        logging.error(f"获取实例列表失败: {e}")
        flash('获取实例列表失败', 'error')
        # 提供默认的空统计信息
        stats = {'total': 0, 'running': 0, 'stopped': 0, 'error': 0}
        return render_template('instances.html', instances=[], stats=stats)

@app.route('/instances/<instance_id>/stop', methods=['POST'])
@login_required
def stop_instance(instance_id):
    """停止实例"""
    try:
        if locust_manager.stop_instance(instance_id):
            return jsonify({'success': True, 'message': '实例已停止'})
        else:
            return jsonify({'success': False, 'message': '停止实例失败'})
    except Exception as e:
        logging.error(f"停止实例失败: {e}")
        return jsonify({'success': False, 'message': '停止实例失败'})

@app.route('/instances/<instance_id>/proxy')
@login_required
def proxy_instance(instance_id):
    """代理到Locust实例"""
    try:
        instance = locust_manager.get_instance(instance_id)
        if not instance or not instance.is_running():
            flash('实例不存在或未运行', 'error')
            return redirect(url_for('instances'))
        
        # 重定向到Locust Web UI
        locust_url = f"http://localhost:{instance.port}"
        return redirect(locust_url)
        
    except Exception as e:
        logging.error(f"代理实例失败: {e}")
        flash('访问实例失败', 'error')
        return redirect(url_for('instances'))

# ==================== 集群管理路由 ====================

@app.route('/cluster')
@login_required
def cluster():
    """集群状态"""
    if not config.CLUSTER_MODE:
        flash('集群模式未启用', 'warning')
        return redirect(url_for('dashboard'))
    
    try:
        cluster_stats = redis_manager.get_cluster_stats()
        nodes = redis_manager.get_cluster_nodes()
        return render_template('cluster.html', 
                             cluster_stats=cluster_stats, 
                             nodes=nodes)
    except Exception as e:
        logging.error(f"获取集群状态失败: {e}")
        flash('获取集群状态失败', 'error')
        # 提供默认的空数据
        cluster_stats = {
            'total_nodes': 0,
            'active_nodes': 0,
            'total_instances': 0,
            'running_instances': 0
        }
        return render_template('cluster.html', 
                             cluster_stats=cluster_stats, 
                             nodes=[])

# ==================== 系统管理路由 ====================

@app.route('/admin')
@admin_required
def admin():
    """系统管理"""
    try:
        # 获取系统统计
        stats = db_manager.get_dashboard_stats()
        
        # 获取最近日志
        logs = db_manager.get_recent_logs(limit=50)
        
        return render_template('admin.html', stats=stats, logs=logs)
    except Exception as e:
        logging.error(f"获取管理页面数据失败: {e}")
        flash('获取数据失败', 'error')
        return render_template('admin.html')

@app.route('/admin/cleanup', methods=['POST'])
@admin_required
def cleanup():
    """清理系统"""
    try:
        # 清理孤立文件
        deleted_files = script_manager.cleanup_orphaned_files()
        
        # 停止所有实例
        stopped_instances = locust_manager.stop_all_instances()
        
        flash(f'清理完成：删除 {deleted_files} 个孤立文件，停止 {stopped_instances} 个实例', 'success')
        
    except Exception as e:
        logging.error(f"系统清理失败: {e}")
        flash('系统清理失败', 'error')
    
    return redirect(url_for('admin'))

# ==================== API路由 ====================

@app.route('/api/stats')
@login_required
def api_stats():
    """获取统计数据API"""
    try:
        stats = db_manager.get_dashboard_stats()
        if config.CLUSTER_MODE:
            stats['cluster'] = redis_manager.get_cluster_stats()
        return jsonify(stats)
    except Exception as e:
        logging.error(f"获取统计数据失败: {e}")
        return jsonify({'error': '获取数据失败'}), 500

@app.route('/api/instances')
@login_required
def api_instances():
    """获取实例列表API"""
    try:
        instances = locust_manager.get_all_instances()
        return jsonify(instances)
    except Exception as e:
        logging.error(f"获取实例列表失败: {e}")
        return jsonify({'error': '获取数据失败'}), 500

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message='页面不存在'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', 
                         error_code=500, 
                         error_message='服务器内部错误'), 500

@app.errorhandler(413)
def file_too_large(error):
    flash('文件太大，请选择小于10MB的文件', 'error')
    return redirect(request.url)

if __name__ == '__main__':
    app.run(
        host=config.APP_HOST,
        port=config.APP_PORT,
        debug=config.FLASK_DEBUG
    )