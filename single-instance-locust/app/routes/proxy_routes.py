# -*- coding: utf-8 -*-
"""代理路由"""

from flask import Blueprint, request, jsonify, Response, current_app
from app.services.instance_manager import get_instance
from app.services.proxy_service import (
    http_session, response_cache, should_cache_response,
    get_cache_key, optimize_html_content
)

proxy_bp = Blueprint('proxy', __name__)


@proxy_bp.route('/proxy/<instance_id>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@proxy_bp.route('/proxy/<instance_id>/', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@proxy_bp.route('/proxy/<instance_id>/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy_to_instance(instance_id, path=''):
    """代理请求到指定的Locust实例"""
    instance = get_instance(instance_id)
    if not instance:
        return jsonify({'error': '实例不存在'}), 404

    if not instance.is_running():
        return jsonify({'error': '实例未运行'}), 503

    target_url = f'http://localhost:{instance.port}'
    if path:
        target_url += f'/{path}'
    if request.query_string:
        target_url += f'?{request.query_string.decode()}'

    # 检查缓存
    if request.method == 'GET':
        cache_key = get_cache_key(instance_id, path, request.method)
        cached = response_cache.get(cache_key)
        if cached:
            return Response(cached['content'], status=cached['status'], headers=cached['headers'])

    try:
        headers = dict(request.headers)
        for h in ['Host', 'Content-Length', 'Content-Encoding', 'Transfer-Encoding']:
            headers.pop(h, None)

        timeout = (10, 60) if request.method in ['GET', 'HEAD', 'OPTIONS'] else (15, 120)

        resp = http_session.request(
            method=request.method, url=target_url,
            data=request.get_data(), headers=headers,
            params=None, timeout=timeout,
            allow_redirects=False, stream=True
        )

        content_type = resp.headers.get('Content-Type', '')

        # 非文本内容流式传输
        if not any(ct in content_type for ct in ['text/html', 'application/json', 'text/css', 'application/javascript']):
            def generate():
                for chunk in resp.iter_content(chunk_size=8192):
                    yield chunk
            response = Response(generate(), status=resp.status_code, headers=dict(resp.headers))
            response.headers.pop('Content-Encoding', None)
            response.headers.pop('Transfer-Encoding', None)
            return response

        content = resp.content

        if 'text/html' in content_type:
            try:
                content_str = content.decode('utf-8', errors='ignore')
                content_str = optimize_html_content(content_str, instance_id)
                content = content_str.encode('utf-8')
            except Exception as e:
                current_app.logger.warning(f"HTML内容处理失败: {e}")

        response = Response(content, status=resp.status_code, headers=dict(resp.headers))
        response.headers.pop('Content-Encoding', None)
        response.headers.pop('Transfer-Encoding', None)
        response.headers['Content-Length'] = str(len(content))

        # 缓存静态资源
        if (request.method == 'GET' and resp.status_code == 200 and
                should_cache_response(content_type, path) and len(content) < 1024 * 1024):
            cache_key = get_cache_key(instance_id, path, request.method)
            response_cache.set(cache_key, {
                'content': content, 'status': resp.status_code,
                'headers': dict(response.headers)
            })

        return response

    except Exception as e:
        current_app.logger.error(f"代理请求失败: {target_url}, 错误: {e}")
        return jsonify({'error': f'代理请求失败: {str(e)}'}), 502
