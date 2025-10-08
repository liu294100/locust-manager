#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Locust Management Web Interface
提供Web界面来启动、停止和管理多个Locust压测进程
支持多实例并行压测和代理功能
"""

import os
import signal
import subprocess
import threading
import time
import uuid
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, session
from werkzeug.utils import secure_filename

# 导入认证模块
from app.auth import login_required, authenticate_user, create_session, clear_session, get_current_user
from app.database import db_manager

app = Flask(__name__)

# 会话配置
app.secret_key = os.environ.get('SECRET_KEY', 'locust-management-secret-key-2024')
app.permanent_session_lifetime = timedelta(hours=24)  # 会话24小时有效

# 配置上传文件夹
UPLOAD_FOLDER = 'scripts/tmp'
ALLOWED_EXTENSIONS = {'py'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 多实例管理
locust_instances = {}  # 存储所有Locust实例 {instance_id: instance_info}
instances_lock = threading.Lock()  # 保护实例字典的线程锁
BASE_PORT = 8089  # 基础端口，实例将使用8089, 8090, 8091...

class LocustInstance:
    """Locust实例类"""
    def __init__(self, instance_id, script_file, port, target_host=None, users=None, spawn_rate=None, run_time=None):
        self.instance_id = instance_id
        self.script_file = script_file
        self.port = port
        self.target_host = target_host
        self.users = users
        self.spawn_rate = spawn_rate
        self.run_time = run_time
        self.process = None
        self.created_at = datetime.now()
        self.status = 'stopped'
        
    def start(self):
        """启动Locust实例"""
        if self.process and self.process.poll() is None:
            return False, "实例已在运行"
        
        # 构建命令
        cmd = [
            'locust',
            '-f', self.script_file,
            '--web-host', '0.0.0.0',
            '--web-port', str(self.port)
        ]
        
        if self.target_host:
            cmd.extend(['--host', self.target_host])
        
        # 如果指定了用户数和生成速率，添加默认参数（但保持Web UI可用）
        if self.users and self.spawn_rate:
            cmd.extend([
                '-u', str(self.users),
                '-r', str(self.spawn_rate)
            ])
            
            if self.run_time:
                cmd.extend(['-t', self.run_time])
        
        try:
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.status = 'running'
            return True, f"实例已启动，端口: {self.port}, PID: {self.process.pid}"
        except Exception as e:
            self.status = 'error'
            return False, f"启动失败: {str(e)}"
    
    def stop(self):
        """停止Locust实例"""
        if not self.process:
            return False, "实例未运行"
        
        if self.process.poll() is not None:
            self.status = 'stopped'
            return False, "实例已停止"
        
        try:
            # 尝试优雅停止
            self.process.terminate()
            
            # 等待最多5秒
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # 强制杀死
                self.process.kill()
                self.process.wait()
            
            pid = self.process.pid
            self.status = 'stopped'
            return True, f"实例已停止，端口: {self.port}, PID: {pid}"
        except Exception as e:
            return False, f"停止失败: {str(e)}"
    
    def is_running(self):
        """检查实例是否运行中"""
        if not self.process:
            return False
        running = self.process.poll() is None
        if not running:
            self.status = 'stopped'
        return running
    
    def get_info(self):
        """获取实例信息"""
        return {
            'instance_id': self.instance_id,
            'script_file': self.script_file,
            'port': self.port,
            'target_host': self.target_host,
            'users': self.users,
            'spawn_rate': self.spawn_rate,
            'run_time': self.run_time,
            'status': self.status,
            'is_running': self.is_running(),
            'created_at': self.created_at.isoformat(),
            'pid': self.process.pid if self.process else None,
            'web_url': f'http://localhost:{self.port}'
        }

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_directory_tree():
    """获取scripts目录的完整树形结构"""
    def scan_directory(path, relative_path=""):
        """递归扫描目录"""
        items = []
        
        if not os.path.exists(path):
            return items
        
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                item_relative_path = os.path.join(relative_path, item) if relative_path else item
                
                if os.path.isdir(item_path):
                    # 递归扫描子目录
                    children = scan_directory(item_path, item_relative_path)
                    
                    # 特殊处理tmp目录
                    display_name = "临时文件" if item == "tmp" and relative_path == "" else item
                    
                    items.append({
                        'name': display_name,
                        'path': item_relative_path,
                        'type': 'directory',
                        'children': children,
                        'has_scripts': any(child['type'] == 'file' for child in children) or 
                                     any(child.get('has_scripts', False) for child in children if child['type'] == 'directory')
                    })
                elif item.endswith('.py'):
                    # Python脚本文件
                    items.append({
                        'name': item,
                        'path': item_relative_path,
                        'type': 'file'
                    })
        except PermissionError:
            pass
        
        return items
    
    scripts_dir = os.path.join(os.getcwd(), 'scripts')
    tree = scan_directory(scripts_dir)
    
    # 添加根目录的脚本文件
    root_scripts = []
    if os.path.exists(scripts_dir):
        for item in os.listdir(scripts_dir):
            item_path = os.path.join(scripts_dir, item)
            if os.path.isfile(item_path) and item.endswith('.py'):
                root_scripts.append({
                    'name': item,
                    'path': item,
                    'type': 'file'
                })
    
    # 如果根目录有脚本，添加到树的开头
    if root_scripts:
        tree.insert(0, {
            'name': '根目录',
            'path': '',
            'type': 'directory',
            'children': root_scripts,
            'has_scripts': True
        })
    
    return tree

def get_available_scripts():
    """获取可用的Locust脚本列表，按目录分组（保持向后兼容）"""
    scripts_by_dir = {}
    
    # 扫描scripts目录作为根目录
    scripts_dir = os.path.join(os.getcwd(), 'scripts')
    if os.path.exists(scripts_dir):
        # 扫描scripts根目录下的.py文件
        root_scripts = []
        for file in os.listdir(scripts_dir):
            file_path = os.path.join(scripts_dir, file)
            if os.path.isfile(file_path) and file.endswith('.py'):
                root_scripts.append(file)
        
        if root_scripts:
            scripts_by_dir['根目录'] = root_scripts
        
        # 扫描scripts目录下的子目录
        for subdir in os.listdir(scripts_dir):
            subdir_path = os.path.join(scripts_dir, subdir)
            if os.path.isdir(subdir_path):
                subdir_scripts = []
                for file in os.listdir(subdir_path):
                    if file.endswith('.py'):
                        subdir_scripts.append(file)
                
                # 对于tmp目录，使用"临时文件"作为显示名称
                if subdir == 'tmp':
                    scripts_by_dir['临时文件'] = subdir_scripts
                elif subdir_scripts:
                    scripts_by_dir[subdir] = subdir_scripts
    
    # 如果tmp目录不存在，仍然添加空的临时文件目录选项
    if '临时文件' not in scripts_by_dir:
        scripts_by_dir['临时文件'] = []
    
    return scripts_by_dir

def get_scripts_in_directory(directory):
    """获取指定目录下的脚本列表"""
    scripts = []
    
    if directory == '根目录':
        # 扫描scripts根目录
        scripts_dir = os.path.join(os.getcwd(), 'scripts')
        if os.path.exists(scripts_dir):
            for file in os.listdir(scripts_dir):
                file_path = os.path.join(scripts_dir, file)
                if os.path.isfile(file_path) and file.endswith('.py'):
                    scripts.append(file)
    elif directory == '临时文件':
        # 扫描scripts/tmp目录
        tmp_dir = os.path.join(os.getcwd(), 'scripts', 'tmp')
        if os.path.exists(tmp_dir):
            for file in os.listdir(tmp_dir):
                if file.endswith('.py'):
                    scripts.append(file)
    else:
        # 扫描scripts目录下的子目录
        scripts_dir = os.path.join(os.getcwd(), 'scripts', directory)
        if os.path.exists(scripts_dir):
            for file in os.listdir(scripts_dir):
                if file.endswith('.py'):
                    scripts.append(file)
    
    return scripts

def get_next_available_port():
    """获取下一个可用端口"""
    with instances_lock:
        used_ports = {instance.port for instance in locust_instances.values()}
        port = BASE_PORT
        while port in used_ports:
            port += 1
        return port

def create_instance(script_file, target_host=None, users=None, spawn_rate=None, run_time=None):
    """创建新的Locust实例"""
    instance_id = str(uuid.uuid4())[:8]  # 使用短UUID作为实例ID
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
        return [instance.get_info() for instance in locust_instances.values()]

def remove_instance(instance_id):
    """移除实例"""
    with instances_lock:
        instance = locust_instances.get(instance_id)
        if instance:
            # 确保实例已停止
            if instance.is_running():
                instance.stop()
            del locust_instances[instance_id]
            return True
        return False

def cleanup_stopped_instances():
    """清理已停止的实例"""
    with instances_lock:
        stopped_instances = []
        for instance_id, instance in locust_instances.items():
            if not instance.is_running() and instance.status == 'stopped':
                stopped_instances.append(instance_id)
        
        for instance_id in stopped_instances:
            del locust_instances[instance_id]
        
        return len(stopped_instances)

def start_locust_instance(script_file, target_host=None, users=None, spawn_rate=None, run_time=None):
    """启动新的Locust实例"""
    try:
        # 转换参数
        users = int(users) if users else None
        spawn_rate = int(spawn_rate) if spawn_rate else None
        
        # 创建实例
        instance = create_instance(script_file, target_host, users, spawn_rate, run_time)
        
        # 启动实例
        success, message = instance.start()
        
        if success:
            return True, message, instance.instance_id, instance.port
        else:
            # 启动失败，移除实例
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面和处理"""
    if request.method == 'GET':
        # 如果已经登录，重定向到主页
        if get_current_user():
            return redirect(url_for('index'))
        return render_template('login.html')
    
    # POST请求处理登录
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    success, message, user_info = authenticate_user(username, password)
    
    if success:
        create_session(user_info)
        return jsonify({
            'success': True,
            'message': message,
            'redirect': url_for('index')
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 401

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """登出"""
    clear_session()
    return jsonify({
        'success': True,
        'message': '已成功登出',
        'redirect': url_for('login')
    })

@app.route('/api/user')
@login_required
def get_user_info():
    """获取当前用户信息"""
    user = get_current_user()
    return jsonify({
        'success': True,
        'user': user
    })

@app.route('/')
@login_required
def index():
    """主页面"""
    scripts_by_dir = get_available_scripts()
    instances = get_all_instances()
    current_user = get_current_user()
    
    return render_template('index.html', 
                         scripts_by_dir=scripts_by_dir, 
                         instances=instances,
                         current_user=current_user)

@app.route('/api/scripts/<directory>')
@login_required
def get_directory_scripts(directory):
    """获取指定目录下的脚本列表"""
    scripts = get_scripts_in_directory(directory)
    return jsonify({'scripts': scripts})

@app.route('/api/directory-tree')
@login_required
def get_directory_tree_api():
    """获取完整的目录树结构"""
    try:
        tree = get_directory_tree()
        return jsonify({'tree': tree, 'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取目录树失败: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    """API接口：上传Python文件到临时目录"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # 确保上传目录存在
            upload_path = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'])
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            
            file_path = os.path.join(upload_path, filename)
            file.save(file_path)
            
            return jsonify({
                'success': True, 
                'message': f'文件 {filename} 上传成功',
                'filename': filename
            })
        else:
            return jsonify({'success': False, 'message': '只允许上传.py文件'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500

@app.route('/api/delete', methods=['POST'])
@login_required
def delete_file():
    """API接口：删除临时目录中的Python文件"""
    try:
        filename = request.json.get('filename')
        if not filename:
            return jsonify({'success': False, 'message': '未指定文件名'}), 400
        
        # 安全检查：只允许删除.py文件
        if not filename.endswith('.py'):
            return jsonify({'success': False, 'message': '只能删除.py文件'}), 400
        
        # 构建文件路径
        file_path = os.path.join(os.getcwd(), 'scripts', 'tmp', secure_filename(filename))
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        # 检查是否在正确的目录中
        if not file_path.startswith(os.path.join(os.getcwd(), 'scripts', 'tmp')):
            return jsonify({'success': False, 'message': '无效的文件路径'}), 400
        
        # 删除文件
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': f'文件 {filename} 删除成功'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

@app.route('/start', methods=['POST'])
@login_required
def start():
    """启动新的Locust实例"""
    script_directory = request.form.get('script_directory')
    script_file = request.form.get('script_file')
    target_host = request.form.get('target_host', '').strip()
    users = request.form.get('users', '').strip()
    spawn_rate = request.form.get('spawn_rate', '').strip()
    run_time = request.form.get('run_time', '').strip()
    
    if not script_directory or not script_file:
        return jsonify({'success': False, 'message': '请选择目录和脚本文件'})
    
    # 构建完整的脚本路径
    if script_directory == '根目录':
        full_script_path = f'scripts/{script_file}'
    elif script_directory == '临时文件':
        full_script_path = f'scripts/tmp/{script_file}'
    else:
        full_script_path = f'scripts/{script_directory}/{script_file}'
    
    target_host = target_host if target_host else None
    run_time = run_time if run_time else None
    
    success, message, instance_id, port = start_locust_instance(
        full_script_path, target_host, users, spawn_rate, run_time
    )
    
    response = {'success': success, 'message': message}
    if success:
        response.update({
            'instance_id': instance_id,
            'port': port,
            'web_url': f'http://localhost:{port}'
        })
    
    return jsonify(response)

@app.route('/stop/<instance_id>', methods=['POST'])
@login_required
def stop_instance(instance_id):
    """停止指定的Locust实例"""
    success, message = stop_locust_instance(instance_id)
    return jsonify({'success': success, 'message': message})

@app.route('/stop_all', methods=['POST'])
@login_required
def stop_all():
    """停止所有Locust实例"""
    results = stop_all_instances()
    return jsonify({
        'success': True, 
        'message': f'已停止 {len(results)} 个实例',
        'details': results
    })

@app.route('/instances')
@login_required
def get_instances():
    """获取所有实例状态"""
    instances = get_all_instances()
    return jsonify({
        'instances': instances,
        'count': len(instances),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/instance/<instance_id>')
@login_required
def get_instance_info(instance_id):
    """获取指定实例信息"""
    instance = get_instance(instance_id)
    if not instance:
        return jsonify({'success': False, 'message': '实例不存在'}), 404
    
    return jsonify({
        'success': True,
        'instance': instance.get_info()
    })

@app.route('/cleanup', methods=['POST'])
@login_required
def cleanup():
    """清理已停止的实例"""
    count = cleanup_stopped_instances()
    return jsonify({
        'success': True,
        'message': f'已清理 {count} 个停止的实例'
    })

@app.route('/proxy/<instance_id>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/proxy/<instance_id>/', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/proxy/<instance_id>/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy_to_instance(instance_id, path=''):
    """代理请求到指定的Locust实例"""
    instance = get_instance(instance_id)
    if not instance:
        return jsonify({'error': '实例不存在'}), 404
    
    if not instance.is_running():
        return jsonify({'error': '实例未运行'}), 503
    
    # 构建目标URL
    target_url = f'http://localhost:{instance.port}'
    if path:
        target_url += f'/{path}'
    
    # 添加查询参数
    if request.query_string:
        target_url += f'?{request.query_string.decode()}'
    
    try:
        # 准备请求头，移除Host头以避免冲突
        headers = dict(request.headers)
        headers.pop('Host', None)
        
        # 转发请求 - 统一处理所有HTTP方法
        resp = requests.request(
            method=request.method,
            url=target_url,
            data=request.get_data(),
            headers=headers,
            params=None,  # 查询参数已经包含在target_url中
            timeout=30,
            allow_redirects=False  # 不自动跟随重定向，让前端处理
        )
        
        # 处理响应内容
        content = resp.content
        content_type = resp.headers.get('Content-Type', '')
        
        # 如果是HTML内容，修改其中的相对路径
        if 'text/html' in content_type:
            content_str = content.decode('utf-8', errors='ignore')
            # 替换相对路径为代理路径，避免重复替换
            content_str = content_str.replace('href="./', f'href="/proxy/{instance_id}/')
            content_str = content_str.replace('src="./', f'src="/proxy/{instance_id}/')
            # 只替换不是已经代理的绝对路径
            import re
            content_str = re.sub(r'href="(/(?!proxy/))', f'href="/proxy/{instance_id}\\1', content_str)
            content_str = re.sub(r'src="(/(?!proxy/))', f'src="/proxy/{instance_id}\\1', content_str)
            # 处理JavaScript中的相对路径
            content_str = content_str.replace("fetch('./", f"fetch('/proxy/{instance_id}/")
            content_str = content_str.replace('fetch("./', f'fetch("/proxy/{instance_id}/')
            content_str = re.sub(r"fetch\('(/(?!proxy/))", f"fetch('/proxy/{instance_id}\\1", content_str)
            content_str = re.sub(r'fetch\("(/(?!proxy/))', f'fetch("/proxy/{instance_id}\\1', content_str)
            content = content_str.encode('utf-8')
        
        # 创建响应
        response = Response(
            content,
            status=resp.status_code,
            headers=dict(resp.headers)
        )
        
        # 移除可能导致问题的头部
        response.headers.pop('Content-Encoding', None)
        response.headers.pop('Transfer-Encoding', None)
        response.headers['Content-Length'] = str(len(content))
        
        return response
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'代理请求失败: {str(e)}'}), 502

@app.route('/open/<instance_id>')
def open_instance_ui(instance_id):
    """重定向到指定实例的Web UI"""
    instance = get_instance(instance_id)
    if not instance:
        return jsonify({'error': '实例不存在'}), 404
    
    if not instance.is_running():
        return jsonify({'error': '实例未运行'}), 503
    
    return redirect(f'http://localhost:{instance.port}')

@app.route('/api/directories')
def get_directories():
    """API接口：获取所有可用的脚本目录"""
    try:
        scripts_by_dir = get_available_scripts()
        directories = list(scripts_by_dir.keys())
        return jsonify({'directories': directories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/instances')
def get_instances_api():
    """API接口：获取所有实例信息"""
    try:
        instances = get_all_instances()
        return jsonify({'instances': instances})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_api():
    """API接口：启动新的Locust实例"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        script_directory = data.get('script_directory')
        script_file = data.get('script_file')
        target_host = data.get('target_host')
        users = data.get('users')
        spawn_rate = data.get('spawn_rate', 1)
        run_time = data.get('run_time')
        
        if not script_directory or not script_file:
            return jsonify({'success': False, 'message': '请选择脚本目录和文件'}), 400
        
        # 构建完整的脚本路径
        if script_directory == '根目录':
            full_script_path = os.path.join('scripts', script_file)
        elif script_directory == '临时文件':
            full_script_path = os.path.join('scripts', 'tmp', script_file)
        else:
            full_script_path = os.path.join('scripts', script_directory, script_file)
        
        # 检查脚本文件是否存在
        if not os.path.exists(full_script_path):
            return jsonify({'success': False, 'message': f'脚本文件不存在: {full_script_path}'}), 400
        
        # 启动实例
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

@app.route('/api/stop/<instance_id>', methods=['POST'])
def stop_instance_api(instance_id):
    """API接口：停止指定的Locust实例"""
    try:
        success, message = stop_locust_instance(instance_id)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止失败: {str(e)}'}), 500

@app.route('/api/remove/<instance_id>', methods=['DELETE'])
def remove_instance_api(instance_id):
    """API接口：删除指定的Locust实例"""
    try:
        instance = get_instance(instance_id)
        if not instance:
            return jsonify({'success': False, 'message': '实例不存在'}), 404
        
        # 如果实例正在运行，先停止它
        if instance.is_running():
            stop_locust_instance(instance_id)
        
        # 删除实例
        remove_instance(instance_id)
        return jsonify({'success': True, 'message': f'实例 {instance_id} 已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

@app.route('/api/stop_all', methods=['POST'])
def stop_all_api():
    """API接口：停止所有Locust实例"""
    try:
        stopped_count = stop_all_instances()
        return jsonify({
            'success': True,
            'message': f'已停止 {stopped_count} 个实例'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止失败: {str(e)}'}), 500

@app.route('/ok')
def health_check():
    """健康检测接口"""
    return 'ok'

def init_application():
    """初始化应用程序"""
    print("🚀 正在启动Locust多实例管理系统...")
    
    # 检查并创建必要的目录
    os.makedirs('scripts/tmp', exist_ok=True)
    
    # 初始化数据库
    print("📋 正在初始化数据库...")
    try:
        # 获取数据库配置信息
        from app.config import db_config
        config = db_config.get_database_config()
        db_type = config.get('type', 'sqlite')
        
        if db_type == 'mysql':
            print(f"🔗 使用MySQL数据库: {config['host']}:{config['port']}/{config['database']}")
            print("💡 确保MySQL服务已启动并且数据库可访问")
        else:
            print("🔗 使用SQLite本地数据库")
        
        # 执行数据库初始化
        db_manager.init_database()
        print("✅ 数据库初始化成功")
        
        
    except ImportError as e:
        if 'pymysql' in str(e):
            print("❌ MySQL支持需要安装pymysql")
            print("💡 请运行: pip install pymysql")
        else:
            print(f"❌ 数据库模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        print("\n🔧 故障排除建议:")
        if 'mysql' in str(e).lower() or 'connection' in str(e).lower():
            print("   1. 检查MySQL服务是否启动")
            print("   2. 检查数据库连接配置")
            print("   3. 确认数据库用户权限")
            print("   4. 检查防火墙设置")
        print("   5. 查看详细错误信息进行诊断")
        return False
    
    print("\n🌐 Web服务启动信息:")
    print("   管理界面: http://localhost:8088")
    print("   健康检查: http://localhost:8088/ok")
    print("\n" + "="*50)
    
    return True

if __name__ == '__main__':
    # 初始化应用程序
    if not init_application():
        print("\n❌ 应用程序初始化失败，退出...")
        exit(1)
    
    try:
        app.run(host='0.0.0.0', port=8088, debug=True)
    except KeyboardInterrupt:
        print("\n\n👋 正在关闭应用程序...")
        # 停止所有运行中的Locust实例
        try:
            stopped_count = stop_all_instances()
            if stopped_count > 0:
                print(f"✅ 已停止 {stopped_count} 个Locust实例")
        except:
            pass
        print("✅ 应用程序已安全关闭")
    except Exception as e:
        print(f"\n❌ 应用程序运行错误: {e}")
        exit(1)