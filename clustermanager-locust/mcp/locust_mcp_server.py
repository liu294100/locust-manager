# -*- coding: utf-8 -*-
"""
Locust 压测平台 MCP Server

提供以下功能:
1. 脚本管理 - 上传、列表、预览、删除脚本
2. 实例管理 - 启动、停止、查看压测实例
3. 结果分析 - 获取压测统计数据和结果分析
"""

import os
import json
import httpx
from typing import Optional
from datetime import datetime
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ============== 配置 ==============
DEFAULT_BASE_URL = "http://localhost:8088"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"

# 从环境变量读取配置
BASE_URL = os.getenv("LOCUST_BASE_URL", DEFAULT_BASE_URL)
USERNAME = os.getenv("LOCUST_USERNAME", DEFAULT_USERNAME)
PASSWORD = os.getenv("LOCUST_PASSWORD", DEFAULT_PASSWORD)


class LocustMCPServer:
    """Locust MCP Server 实现"""
    
    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.username = USERNAME
        self.password = PASSWORD
        self.session_cookies = None
        self.client = httpx.Client(timeout=30.0)
    
    def _ensure_login(self) -> bool:
        """确保已登录"""
        if self.session_cookies:
            return True
        return self._login()
    
    def _login(self) -> bool:
        """登录获取会话"""
        try:
            resp = self.client.post(
                f"{self.base_url}/api/login",
                json={"username": self.username, "password": self.password}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    self.session_cookies = resp.cookies
                    return True
        except Exception as e:
            print(f"登录失败: {e}")
        return False
    
    def _request(self, method: str, path: str, **kwargs) -> dict:
        """发送请求"""
        self._ensure_login()
        url = f"{self.base_url}{path}"
        
        if self.session_cookies:
            kwargs["cookies"] = self.session_cookies
        
        try:
            resp = self.client.request(method, url, **kwargs)
            if resp.status_code == 401:
                # 重新登录
                self._login()
                kwargs["cookies"] = self.session_cookies
                resp = self.client.request(method, url, **kwargs)
            
            return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"text": resp.text}
        except Exception as e:
            return {"error": str(e)}
    
    # ============== 脚本管理 ==============
    
    def list_scripts(self) -> dict:
        """获取所有脚本列表"""
        tree = self._request("GET", "/api/directory-tree")
        return tree
    
    def get_directories(self) -> dict:
        """获取脚本目录列表"""
        return self._request("GET", "/api/directories")
    
    def preview_script(self, script_path: str) -> dict:
        """预览脚本内容"""
        return self._request("GET", f"/api/preview/{script_path}")
    
    def upload_script(self, filename: str, content: str) -> dict:
        """创建/上传脚本到临时目录"""
        return self._request("POST", "/api/create-temp-script", json={
            "filename": filename,
            "content": content
        })
    
    def delete_script(self, filename: str) -> dict:
        """删除临时目录中的脚本"""
        return self._request("POST", "/api/delete", json={"filename": filename})
    
    def curl_to_script(self, curl_cmd: str, filename: str = "", save: bool = False) -> dict:
        """将 cURL 命令转换为 Locust 脚本"""
        return self._request("POST", "/api/curl-to-script", json={
            "curl": curl_cmd,
            "filename": filename,
            "save": save
        })
    
    # ============== 实例管理 ==============
    
    def list_instances(self) -> dict:
        """获取所有压测实例"""
        return self._request("GET", "/api/instances")
    
    def start_instance(
        self,
        script_path: str,
        target_host: str,
        users: int = 10,
        spawn_rate: int = 1,
        run_time: str = None,
        load_mode: str = "fixed",
        step_users: int = None,
        step_increment: int = None,
        step_interval: int = None
    ) -> dict:
        """启动压测实例"""
        data = {
            "script_full_path": script_path,
            "target_host": target_host,
            "users": users,
            "spawn_rate": spawn_rate,
            "load_mode": load_mode
        }
        if run_time:
            data["run_time"] = run_time
        if load_mode == "step":
            data["step_users"] = step_users or 100
            data["step_increment"] = step_increment or 10
            data["step_interval_seconds"] = step_interval or 60
        
        return self._request("POST", "/api/start", json=data)
    
    def stop_instance(self, instance_id: str) -> dict:
        """停止压测实例"""
        return self._request("POST", f"/api/stop/{instance_id}")
    
    def stop_all_instances(self) -> dict:
        """停止所有压测实例"""
        return self._request("POST", "/api/stop_all")
    
    def remove_instance(self, instance_id: str) -> dict:
        """删除压测实例"""
        return self._request("DELETE", f"/api/remove/{instance_id}")
    
    # ============== 结果分析 ==============
    
    def get_instance_stats(self, instance_id: str) -> dict:
        """获取实例统计数据（通过代理）"""
        return self._request("GET", f"/proxy/{instance_id}/stats/requests")
    
    def get_instance_failures(self, instance_id: str) -> dict:
        """获取实例失败请求"""
        return self._request("GET", f"/proxy/{instance_id}/stats/failures")
    
    def get_instance_exceptions(self, instance_id: str) -> dict:
        """获取实例异常"""
        return self._request("GET", f"/proxy/{instance_id}/exceptions")
    
    def analyze_results(self, instance_id: str) -> dict:
        """分析压测结果"""
        stats = self.get_instance_stats(instance_id)
        failures = self.get_instance_failures(instance_id)
        
        if "error" in stats:
            return stats
        
        # 分析统计数据
        analysis = {
            "instance_id": instance_id,
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "endpoints": [],
            "recommendations": []
        }
        
        total_requests = 0
        total_failures = 0
        total_response_time = 0
        max_response_time = 0
        
        for endpoint in stats.get("stats", []):
            name = endpoint.get("name", "")
            num_requests = endpoint.get("num_requests", 0)
            num_failures = endpoint.get("num_failures", 0)
            avg_response = endpoint.get("avg_response_time", 0)
            max_response = endpoint.get("max_response_time", 0)
            
            total_requests += num_requests
            total_failures += num_failures
            total_response_time += avg_response * num_requests
            max_response_time = max(max_response_time, max_response)
            
            # 计算错误率
            error_rate = (num_failures / num_requests * 100) if num_requests > 0 else 0
            
            analysis["endpoints"].append({
                "name": name,
                "requests": num_requests,
                "failures": num_failures,
                "error_rate": f"{error_rate:.2f}%",
                "avg_response_time": f"{avg_response:.2f}ms",
                "max_response_time": f"{max_response:.2f}ms",
                "rps": endpoint.get("current_rps", 0)
            })
        
        # 汇总
        overall_error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
        avg_response = (total_response_time / total_requests) if total_requests > 0 else 0
        
        analysis["summary"] = {
            "total_requests": total_requests,
            "total_failures": total_failures,
            "overall_error_rate": f"{overall_error_rate:.2f}%",
            "avg_response_time": f"{avg_response:.2f}ms",
            "max_response_time": f"{max_response_time:.2f}ms",
            "current_users": stats.get("user_count", 0),
            "total_rps": stats.get("total_rps", 0)
        }
        
        # 生成建议
        if overall_error_rate > 5:
            analysis["recommendations"].append(
                f"⚠️ 错误率较高 ({overall_error_rate:.2f}%)，建议检查目标服务状态或降低并发"
            )
        if avg_response > 1000:
            analysis["recommendations"].append(
                f"⚠️ 平均响应时间较长 ({avg_response:.0f}ms)，建议优化接口性能"
            )
        if max_response_time > 5000:
            analysis["recommendations"].append(
                f"⚠️ 最大响应时间过长 ({max_response_time:.0f}ms)，存在慢请求"
            )
        if not analysis["recommendations"]:
            analysis["recommendations"].append("✅ 压测指标正常，系统表现良好")
        
        # 添加失败详情
        if failures.get("failures"):
            analysis["failure_details"] = failures["failures"]
        
        return analysis


# ============== MCP Server 定义 ==============

server = Server("locust-stress-test")
locust_server = LocustMCPServer()


@server.list_tools()
async def list_tools():
    """列出所有可用工具"""
    return [
        # 脚本管理
        Tool(
            name="list_scripts",
            description="获取所有可用的压测脚本列表，包括目录结构",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="preview_script",
            description="预览脚本文件内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {
                        "type": "string",
                        "description": "脚本相对路径，如 tmp/demo.py 或 Trader/trader_locust.py"
                    }
                },
                "required": ["script_path"]
            }
        ),
        Tool(
            name="upload_script",
            description="上传/创建压测脚本到临时目录",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "脚本文件名（不需要完整路径），如 my_test.py"
                    },
                    "content": {
                        "type": "string",
                        "description": "脚本内容（Python代码）"
                    }
                },
                "required": ["filename", "content"]
            }
        ),
        Tool(
            name="delete_script",
            description="删除临时目录中的脚本文件",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "要删除的脚本文件名"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="curl_to_script",
            description="将 cURL 命令转换为 Locust 压测脚本",
            inputSchema={
                "type": "object",
                "properties": {
                    "curl_cmd": {
                        "type": "string",
                        "description": "cURL 命令字符串"
                    },
                    "filename": {
                        "type": "string",
                        "description": "保存的脚本文件名（可选）"
                    },
                    "save": {
                        "type": "boolean",
                        "description": "是否保存到临时目录，默认 false"
                    }
                },
                "required": ["curl_cmd"]
            }
        ),
        
        # 实例管理
        Tool(
            name="list_instances",
            description="获取所有压测实例的状态信息",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="start_instance",
            description="启动一个新的压测实例",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {
                        "type": "string",
                        "description": "脚本相对路径（相对于 scripts 目录），如 tmp/demo.py"
                    },
                    "target_host": {
                        "type": "string",
                        "description": "目标主机地址，如 https://api.example.com"
                    },
                    "users": {
                        "type": "integer",
                        "description": "并发用户数，默认 10"
                    },
                    "spawn_rate": {
                        "type": "integer",
                        "description": "每秒启动用户数，默认 1"
                    },
                    "run_time": {
                        "type": "string",
                        "description": "运行时长，如 1m, 5m, 1h（可选）"
                    },
                    "load_mode": {
                        "type": "string",
                        "description": "负载模式: fixed(固定) 或 step(递增)，默认 fixed",
                        "enum": ["fixed", "step"]
                    },
                    "step_users": {
                        "type": "integer",
                        "description": "递增模式：最大用户数"
                    },
                    "step_increment": {
                        "type": "integer",
                        "description": "递增模式：每次递增用户数"
                    },
                    "step_interval": {
                        "type": "integer",
                        "description": "递增模式：递增间隔（秒）"
                    }
                },
                "required": ["script_path", "target_host"]
            }
        ),
        Tool(
            name="stop_instance",
            description="停止指定的压测实例",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "实例 ID"
                    }
                },
                "required": ["instance_id"]
            }
        ),
        Tool(
            name="stop_all_instances",
            description="停止所有运行中的压测实例",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="remove_instance",
            description="删除指定的压测实例记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "实例 ID"
                    }
                },
                "required": ["instance_id"]
            }
        ),
        
        # 结果分析
        Tool(
            name="get_instance_stats",
            description="获取压测实例的原始统计数据",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "实例 ID"
                    }
                },
                "required": ["instance_id"]
            }
        ),
        Tool(
            name="analyze_results",
            description="分析压测结果，包括汇总统计、各端点性能和优化建议",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "实例 ID"
                    }
                },
                "required": ["instance_id"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """调用工具"""
    try:
        result = None
        
        # 脚本管理
        if name == "list_scripts":
            result = locust_server.list_scripts()
        elif name == "preview_script":
            result = locust_server.preview_script(arguments["script_path"])
        elif name == "upload_script":
            result = locust_server.upload_script(
                arguments["filename"],
                arguments["content"]
            )
        elif name == "delete_script":
            result = locust_server.delete_script(arguments["filename"])
        elif name == "curl_to_script":
            result = locust_server.curl_to_script(
                arguments["curl_cmd"],
                arguments.get("filename", ""),
                arguments.get("save", False)
            )
        
        # 实例管理
        elif name == "list_instances":
            result = locust_server.list_instances()
        elif name == "start_instance":
            result = locust_server.start_instance(
                script_path=arguments["script_path"],
                target_host=arguments["target_host"],
                users=arguments.get("users", 10),
                spawn_rate=arguments.get("spawn_rate", 1),
                run_time=arguments.get("run_time"),
                load_mode=arguments.get("load_mode", "fixed"),
                step_users=arguments.get("step_users"),
                step_increment=arguments.get("step_increment"),
                step_interval=arguments.get("step_interval")
            )
        elif name == "stop_instance":
            result = locust_server.stop_instance(arguments["instance_id"])
        elif name == "stop_all_instances":
            result = locust_server.stop_all_instances()
        elif name == "remove_instance":
            result = locust_server.remove_instance(arguments["instance_id"])
        
        # 结果分析
        elif name == "get_instance_stats":
            result = locust_server.get_instance_stats(arguments["instance_id"])
        elif name == "analyze_results":
            result = locust_server.analyze_results(arguments["instance_id"])
        
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]
        
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, ensure_ascii=False)
        )]


async def main():
    """启动 MCP Server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
