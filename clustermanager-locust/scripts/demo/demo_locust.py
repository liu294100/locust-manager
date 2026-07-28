#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Locust 示例压测脚本
演示基本的 HTTP 接口压力测试，包含 GET/POST 请求、权重配置和错误处理。

使用方式:
  1. 通过 Web UI 上传此脚本并选择执行
  2. 或命令行: locust -f scripts/demo_locust.py --host https://api.example.com
"""

from locust import HttpUser, task, between, events
import json
import random
import time


class DemoUser(HttpUser):
    """示例测试用户"""
    
    # 请求间隔 1-3 秒，模拟真实用户行为
    wait_time = between(1, 3)
    
    def on_start(self):
        """用户启动时执行（如登录等初始化操作）"""
        self.token = None
        self.user_id = f"test_user_{random.randint(1000, 9999)}"
        # 如需登录，取消下面的注释
        # self.login()
    
    def login(self):
        """登录获取 token（示例）"""
        payload = {
            "username": self.user_id,
            "password": "test123456"
        }
        with self.client.post("/api/auth/login", json=payload, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("token", "")
                resp.success()
            else:
                resp.failure(f"登录失败: {resp.status_code}")
    
    def get_headers(self):
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    @task(5)
    def health_check(self):
        """健康检查接口（权重最高，模拟高频请求）"""
        with self.client.get("/health", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"健康检查失败: {resp.status_code}")
    
    @task(3)
    def get_items(self):
        """查询列表接口"""
        params = {
            "page": random.randint(1, 10),
            "size": 20
        }
        with self.client.get("/api/items", params=params, 
                            headers=self.get_headers(),
                            catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 401:
                resp.failure("未授权")
            else:
                resp.failure(f"查询失败: {resp.status_code}")
    
    @task(2)
    def get_item_detail(self):
        """查询详情接口"""
        item_id = random.randint(1, 100)
        with self.client.get(f"/api/items/{item_id}", 
                            headers=self.get_headers(),
                            catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 404:
                # 404 是预期的，不算失败
                resp.success()
            else:
                resp.failure(f"查询详情失败: {resp.status_code}")
    
    @task(1)
    def create_item(self):
        """创建资源接口（权重低，模拟写操作）"""
        payload = {
            "name": f"test_item_{random.randint(1, 10000)}",
            "description": "Locust 压测创建的测试数据",
            "price": round(random.uniform(10.0, 999.99), 2)
        }
        with self.client.post("/api/items", 
                             json=payload,
                             headers=self.get_headers(),
                             catch_response=True) as resp:
            if resp.status_code in [200, 201]:
                resp.success()
            elif resp.status_code == 401:
                resp.failure("未授权，请检查 token")
            else:
                resp.failure(f"创建失败: {resp.status_code}")


# ============ 事件钩子（可选） ============

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时执行"""
    print("🚀 压力测试开始")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时执行"""
    print("✅ 压力测试结束")
