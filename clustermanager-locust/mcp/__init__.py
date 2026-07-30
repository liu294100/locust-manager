# -*- coding: utf-8 -*-
"""
Locust 压测平台 MCP Server

提供压测脚本管理、实例管理、结果分析功能
"""

__version__ = "1.0.0"
__author__ = "Chief Team"

from .locust_mcp_server import LocustMCPServer, main

__all__ = ["LocustMCPServer", "main"]
