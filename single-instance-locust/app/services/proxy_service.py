# -*- coding: utf-8 -*-
"""代理服务 - HTTP会话管理和缓存"""

import re
import hashlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_optimized_session():
    """创建优化的HTTP会话，包含连接池和重试机制"""
    s = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=20,
        pool_maxsize=20,
        pool_block=False
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


# 全局HTTP会话实例
http_session = create_optimized_session()


class SimpleCache:
    """简单的内存缓存"""

    def __init__(self, max_size=100):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []

    def get(self, key):
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None

    def set(self, key, value):
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        self.cache[key] = value
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    def clear(self):
        self.cache.clear()
        self.access_order.clear()


# 全局缓存实例
response_cache = SimpleCache(max_size=50)


def should_cache_response(content_type, path):
    """判断响应是否应该被缓存"""
    static_types = ['text/css', 'application/javascript', 'text/javascript',
                    'image/', 'font/', 'application/font']
    static_paths = ['/static/', '/css/', '/js/', '/images/', '/fonts/']
    return (any(ct in content_type for ct in static_types) or
            any(sp in path for sp in static_paths))


def get_cache_key(instance_id, path, method):
    """生成缓存键"""
    key_str = f"{instance_id}:{method}:{path}"
    return hashlib.md5(key_str.encode()).hexdigest()


def optimize_html_content(content_str, instance_id):
    """优化HTML内容处理"""
    patterns = [
        (r'href="\./', f'href="/proxy/{instance_id}/'),
        (r'src="\./', f'src="/proxy/{instance_id}/'),
        (r'href="(/(?!proxy/))', f'href="/proxy/{instance_id}\\1'),
        (r'src="(/(?!proxy/))', f'src="/proxy/{instance_id}\\1'),
        (r"fetch\('\.\/", f"fetch('/proxy/{instance_id}/"),
        (r'fetch\("\./', f'fetch("/proxy/{instance_id}/'),
        (r"fetch\('(/(?!proxy/))", f"fetch('/proxy/{instance_id}\\1"),
        (r'fetch\("(/(?!proxy/))', f'fetch("/proxy/{instance_id}\\1'),
    ]
    for pattern, replacement in patterns:
        content_str = re.sub(pattern, replacement, content_str)
    return content_str
