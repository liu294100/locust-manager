# -*- coding: utf-8 -*-
"""脚本管理API路由"""

import os
import re
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.auth import login_required
from app.services.script_manager import (
    get_available_scripts, get_scripts_in_directory,
    get_directory_tree, allowed_file
)

script_bp = Blueprint('script', __name__)


@script_bp.route('/api/directories')
def get_directories():
    """获取所有可用的脚本目录"""
    try:
        scripts_by_dir = get_available_scripts()
        directories = list(scripts_by_dir.keys())
        return jsonify({'directories': directories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@script_bp.route('/api/scripts/<directory>')
@login_required
def get_directory_scripts(directory):
    """获取指定目录下的脚本列表"""
    scripts = get_scripts_in_directory(directory)
    return jsonify({'scripts': scripts})


@script_bp.route('/api/directory-tree')
@login_required
def get_directory_tree_api():
    """获取完整的目录树结构"""
    try:
        tree = get_directory_tree()
        return jsonify({'tree': tree, 'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取目录树失败: {str(e)}'}), 500


@script_bp.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    """上传Python文件到临时目录"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(os.getcwd(), 'scripts', 'tmp')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            return jsonify({
                'success': True,
                'message': f'文件 {filename} 上传成功',
                'filename': filename
            })
        else:
            return jsonify({'success': False, 'message': '只允许上传.py文件'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500


@script_bp.route('/api/delete', methods=['POST'])
@login_required
def delete_file():
    """删除临时目录中的Python文件"""
    try:
        filename = request.json.get('filename')
        if not filename:
            return jsonify({'success': False, 'message': '未指定文件名'}), 400

        if not filename.endswith('.py'):
            return jsonify({'success': False, 'message': '只能删除.py文件'}), 400

        file_path = os.path.join(os.getcwd(), 'scripts', 'tmp', secure_filename(filename))

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': '文件不存在'}), 404

        if not file_path.startswith(os.path.join(os.getcwd(), 'scripts', 'tmp')):
            return jsonify({'success': False, 'message': '无效的文件路径'}), 400

        os.remove(file_path)
        return jsonify({'success': True, 'message': f'文件 {filename} 删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


@script_bp.route('/api/preview/<path:script_path>')
def preview_script(script_path):
    """获取脚本文件内容预览"""
    try:
        safe_path = os.path.normpath(script_path)
        if '..' in safe_path or safe_path.startswith('/'):
            return jsonify({'error': '无效的文件路径'}), 400

        full_path = os.path.join('scripts', safe_path)
        if not os.path.exists(full_path):
            return jsonify({'error': '文件不存在'}), 404

        if not full_path.endswith('.py'):
            return jsonify({'error': '只支持预览Python文件'}), 400

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(full_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except UnicodeDecodeError:
                return jsonify({'error': '文件编码不支持'}), 400

        return jsonify({
            'success': True, 'content': content,
            'filename': os.path.basename(full_path), 'path': script_path
        })
    except Exception as e:
        return jsonify({'error': f'读取文件失败: {str(e)}'}), 500


@script_bp.route('/api/create-temp-script', methods=['POST'])
def create_temp_script():
    """创建临时脚本文件"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        filename = data.get('filename', '').strip()
        content = data.get('content', '')

        if not filename:
            return jsonify({'error': '文件名不能为空'}), 400

        if not filename.endswith('.py'):
            filename += '.py'

        if not re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fff]+\.py$', filename):
            return jsonify({'error': '文件名只能包含字母、数字、下划线、中划线和中文字符'}), 400

        temp_dir = os.path.join('scripts', 'tmp')
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, filename)

        if os.path.exists(file_path):
            return jsonify({'error': '文件已存在，请使用不同的文件名'}), 400

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return jsonify({
            'success': True,
            'message': f'临时脚本 {filename} 创建成功',
            'filename': filename,
            'path': f'tmp/{filename}'
        })
    except Exception as e:
        return jsonify({'error': f'创建文件失败: {str(e)}'}), 500


@script_bp.route('/api/curl-to-script', methods=['POST'])
@login_required
def curl_to_script():
    """将 cURL 命令转换为 Locust 压测脚本"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400

        curl_cmd = data.get('curl', '').strip()
        filename = data.get('filename', '').strip()
        save = data.get('save', False)

        if not curl_cmd:
            return jsonify({'success': False, 'message': '请输入 cURL 命令'}), 400

        from app.services.curl_parser import parse_curl, generate_locust_script

        # 解析 curl 命令
        parsed = parse_curl(curl_cmd)

        if not parsed['url']:
            return jsonify({'success': False, 'message': '无法从 cURL 命令中解析出 URL'}), 400

        # 根据文件名生成类名
        if filename:
            class_name = re.sub(r'[^a-zA-Z0-9]', '_', filename).strip('_')
            class_name = class_name.title().replace('_', '') or 'CurlTask'
        else:
            # 从 URL path 生成类名
            from urllib.parse import urlparse
            url_path = urlparse(parsed['url']).path.rstrip('/')
            path_part = url_path.split('/')[-1] if url_path else 'api'
            class_name = re.sub(r'[^a-zA-Z0-9]', '_', path_part).strip('_')
            class_name = class_name.title().replace('_', '') or 'CurlTask'

        # 生成脚本
        script_content = generate_locust_script(parsed, script_name=class_name)

        result = {
            'success': True,
            'content': script_content,
            'parsed': {
                'method': parsed['method'],
                'url': parsed['url'],
                'headers_count': len(parsed['headers']),
                'has_body': parsed['data'] is not None,
                'data_type': parsed['data_type'],
            }
        }

        # 如果需要保存到临时目录
        if save and filename:
            if not filename.endswith('.py'):
                filename += '.py'

            if not re.match(r'^[a-zA-Z0-9_\-]+\.py$', filename):
                return jsonify({'success': False, 'message': '文件名只能包含字母、数字、下划线和连字符'}), 400

            temp_dir = os.path.join('scripts', 'tmp')
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, filename)

            if os.path.exists(file_path):
                return jsonify({'success': False, 'message': f'文件 {filename} 已存在'}), 400

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            result['saved'] = True
            result['filename'] = filename
            result['message'] = f'脚本 {filename} 已生成并保存'
        else:
            result['saved'] = False
            result['message'] = '脚本已生成，可预览或保存'

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'message': f'转换失败: {str(e)}'}), 500


@script_bp.route('/api/curl-to-signed-script', methods=['POST'])
@login_required
def curl_to_signed_script():
    """将 cURL 命令转换为带签名的 Locust 压测脚本"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400

        curl_cmd = data.get('curl', '').strip()
        filename = data.get('filename', '').strip()
        secret_path = data.get('secret_path', '').strip()
        save = data.get('save', False)

        if not curl_cmd:
            return jsonify({'success': False, 'message': '请输入 cURL 命令'}), 400

        if not secret_path:
            return jsonify({'success': False, 'message': '请输入签名URI（如 /api/secret/fetch）'}), 400

        from app.services.curl_parser import parse_curl, generate_signed_locust_script

        parsed = parse_curl(curl_cmd)

        if not parsed['url']:
            return jsonify({'success': False, 'message': '无法从 cURL 命令中解析出 URL'}), 400

        # 生成类名
        if filename:
            class_name = re.sub(r'[^a-zA-Z0-9]', '_', filename).strip('_')
            class_name = class_name.title().replace('_', '') or 'SignedCurlTask'
        else:
            from urllib.parse import urlparse
            url_path = urlparse(parsed['url']).path.rstrip('/')
            path_part = url_path.split('/')[-1] if url_path else 'api'
            class_name = re.sub(r'[^a-zA-Z0-9]', '_', path_part).strip('_')
            class_name = class_name.title().replace('_', '') or 'SignedCurlTask'

        script_content = generate_signed_locust_script(
            parsed, script_name=class_name, secret_path=secret_path
        )

        result = {
            'success': True,
            'content': script_content,
            'parsed': {
                'method': parsed['method'],
                'url': parsed['url'],
                'headers_count': len(parsed['headers']),
                'has_body': parsed['data'] is not None,
                'data_type': parsed['data_type'],
                'secret_path': secret_path,
            }
        }

        if save and filename:
            if not filename.endswith('.py'):
                filename += '.py'

            if not re.match(r'^[a-zA-Z0-9_\-]+\.py$', filename):
                return jsonify({'success': False, 'message': '文件名只能包含字母、数字、下划线和连字符'}), 400

            temp_dir = os.path.join('scripts', 'tmp')
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, filename)

            if os.path.exists(file_path):
                return jsonify({'success': False, 'message': f'文件 {filename} 已存在'}), 400

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            result['saved'] = True
            result['filename'] = filename
            result['message'] = f'签名脚本 {filename} 已生成并保存'
        else:
            result['saved'] = False
            result['message'] = '签名脚本已生成，可预览或保存'

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'message': f'转换失败: {str(e)}'}), 500


# ============ 集群脚本同步 API ============

@script_bp.route('/api/script/sync', methods=['POST'])
def sync_script():
    """
    接收并保存脚本文件（供集群 Master 同步脚本到 Worker 使用）
    
    Request body:
    {
        "path": "tmp/demo11.py",   # 相对于 scripts/ 的路径
        "content": "# script content...",
        "source_node": "master-node-id"
    }
    """
    try:
        # 验证请求来源（只允许集群内部调用）
        proxy_by = request.headers.get('X-Cluster-Sync')
        if proxy_by != 'locust-cluster':
            return jsonify({'success': False, 'message': '未授权的请求'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        rel_path = data.get('path', '').strip()
        content = data.get('content', '')
        source_node = data.get('source_node', 'unknown')
        
        if not rel_path:
            return jsonify({'success': False, 'message': '缺少脚本路径'}), 400
        
        # 安全检查：防止路径穿越
        safe_path = os.path.normpath(rel_path)
        if '..' in safe_path or safe_path.startswith('/') or safe_path.startswith('\\'):
            return jsonify({'success': False, 'message': '无效的文件路径'}), 400
        
        # 只允许 .py 文件
        if not safe_path.endswith('.py'):
            return jsonify({'success': False, 'message': '只能同步 Python 脚本文件'}), 400
        
        # 构建完整路径
        full_path = os.path.join('scripts', safe_path)
        
        # 确保目录存在
        dir_path = os.path.dirname(full_path)
        os.makedirs(dir_path, exist_ok=True)
        
        # 写入文件
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"📥 脚本同步成功: {full_path} (来自 {source_node})")
        
        return jsonify({
            'success': True,
            'message': f'脚本 {rel_path} 同步成功',
            'path': full_path
        })
        
    except Exception as e:
        print(f"❌ 脚本同步失败: {e}")
        return jsonify({'success': False, 'message': f'同步失败: {str(e)}'}), 500


@script_bp.route('/api/script/content/<path:script_path>')
def get_script_content(script_path):
    """
    获取脚本文件内容（供集群同步使用）
    
    Args:
        script_path: 相对于 scripts/ 的路径，如 tmp/demo11.py
    """
    try:
        # 验证请求来源
        proxy_by = request.headers.get('X-Cluster-Sync')
        if proxy_by != 'locust-cluster':
            return jsonify({'success': False, 'message': '未授权的请求'}), 403
        
        # 安全检查
        safe_path = os.path.normpath(script_path)
        if '..' in safe_path or safe_path.startswith('/') or safe_path.startswith('\\'):
            return jsonify({'success': False, 'message': '无效的文件路径'}), 400
        
        full_path = os.path.join('scripts', safe_path)
        
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        if not full_path.endswith('.py'):
            return jsonify({'success': False, 'message': '只支持 Python 脚本'}), 400
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'path': script_path,
            'content': content
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'读取失败: {str(e)}'}), 500
