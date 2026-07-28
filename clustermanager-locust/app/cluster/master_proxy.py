# -*- coding: utf-8 -*-
"""
主节点代理中间件
从节点自动将 HTTP 请求转发到主节点
"""

import requests
from functools import wraps
from flask import request, Response, jsonify
from typing import Optional, Tuple


class MasterProxy:
    """主节点代理"""
    
    # 不需要转发的路径（只保留健康检查和集群内部通信）
    BYPASS_PATHS = {
        '/ok',                              # 健康检查（K8s 探针）
        '/api/cluster/test-connectivity',   # 网络连通性测试（诊断用，需要在本地执行）
        '/api/script/sync',                 # 脚本同步（Worker 需要本地保存脚本）
    }
    
    # 静态资源路径前缀
    STATIC_PREFIXES = ('/static/', '/favicon.ico')
    
    def __init__(self):
        self._enabled = False
        
    def init_app(self, app):
        """初始化 Flask 应用"""
        self._enabled = True
        self_proxy = self  # 保存引用供闭包使用
        
        @app.before_request
        def check_and_proxy_to_master():
            """请求前检查是否需要转发到主节点"""
            # 检查是否需要代理
            should_proxy, master_url = self_proxy._should_proxy_request()
            if should_proxy and master_url:
                # 直接转发并返回响应
                response = self_proxy._forward_request(master_url)
                if response:
                    return response
                else:
                    print(f"⚠️ 转发失败，降级为本地处理: {request.path}")
            # 不需要转发，继续正常处理
            return None
            
    def _should_proxy_request(self) -> Tuple[bool, Optional[str]]:
        """
        判断是否需要将请求转发到主节点
        
        Returns:
            (是否需要转发, 主节点URL)
        """
        from app.config import is_cluster_enabled
        
        path = request.path
        
        # 集群模式未启用，不转发
        if not is_cluster_enabled():
            return False, None
        
        # 已经是转发过来的请求，不再转发（防止循环）
        if request.headers.get('X-Proxy-By') == 'locust-worker':
            return False, None
            
        # 静态资源不转发
        if path.startswith(self.STATIC_PREFIXES):
            return False, None
            
        # 白名单路径不转发
        if path in self.BYPASS_PATHS:
            return False, None
            
        # 检查当前节点是否是主节点
        try:
            from app.cluster import node_registry
            
            # 当前节点是主节点，不需要转发
            if node_registry.is_current_node_leader():
                return False, None
                
            # 获取主节点信息
            master_node = node_registry.get_master_node()
            if not master_node:
                # 没有主节点，不转发（可能正在选举中）
                return False, None
                
            # 构建主节点 URL
            master_url = f"http://{master_node.ip_address}:{master_node.port}"
            return True, master_url
            
        except Exception as e:
            print(f"检查主节点状态失败: {e}")
            return False, None
            
    def _forward_request(self, master_url: str) -> Optional[Response]:
        """
        将请求转发到主节点
        
        Args:
            master_url: 主节点基础URL
            
        Returns:
            转发后的响应
        """
        # 构建目标 URL
        target_url = f"{master_url}{request.full_path}"
        
        # 准备请求头（过滤掉一些不需要的头）
        headers = {
            key: value for key, value in request.headers
            if key.lower() not in ('host', 'content-length')
        }
        # 添加转发标记，防止循环转发
        headers['X-Forwarded-From'] = request.host
        headers['X-Proxy-By'] = 'locust-worker'
        
        try:
            # 转发请求
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.get_data(),
                cookies=request.cookies,
                timeout=30,
                allow_redirects=False
            )
            
            # 构建响应
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            response_headers = [
                (name, value) for name, value in resp.raw.headers.items()
                if name.lower() not in excluded_headers
            ]
            
            return Response(
                resp.content,
                status=resp.status_code,
                headers=response_headers
            )
            
        except requests.Timeout:
            print(f"❌ 转发超时: {target_url}")
            return Response(
                '{"success": false, "message": "转发请求到主节点超时"}',
                status=504,
                content_type='application/json'
            )
        except requests.ConnectionError as e:
            print(f"❌ 无法连接主节点: {target_url}, 错误: {e}")
            return Response(
                '{"success": false, "message": "无法连接到主节点"}',
                status=502,
                content_type='application/json'
            )
        except Exception as e:
            print(f"❌ 转发请求失败: {e}")
            return None


# 全局代理实例
master_proxy = MasterProxy()


def forward_to_master_if_worker(f):
    """
    装饰器：如果当前是从节点，则转发请求到主节点
    用于需要在主节点执行的特定路由
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.config import is_cluster_enabled
        
        if not is_cluster_enabled():
            return f(*args, **kwargs)
            
        try:
            from app.cluster import node_registry
            
            # 已经是转发过来的请求，直接执行
            if request.headers.get('X-Proxy-By') == 'locust-worker':
                return f(*args, **kwargs)
            
            # 当前是主节点，直接执行
            if node_registry.is_current_node_leader():
                return f(*args, **kwargs)
                
            # 获取主节点并转发
            master_node = node_registry.get_master_node()
            if not master_node:
                return jsonify({
                    'success': False,
                    'message': '集群无主节点，请稍后重试'
                }), 503
                
            master_url = f"http://{master_node.ip_address}:{master_node.port}"
            proxy = MasterProxy()
            response = proxy._forward_request(master_url)
            
            if response:
                return response
            else:
                return jsonify({
                    'success': False,
                    'message': '转发请求到主节点失败'
                }), 502
                
        except Exception as e:
            print(f"转发检查失败: {e}")
            # 出错时降级为本地执行
            return f(*args, **kwargs)
            
    return decorated_function
