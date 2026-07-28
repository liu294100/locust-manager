# -*- coding: utf-8 -*-
"""
Locust管理系统
"""
import sys
import os

# Windows 控制台 UTF-8 编码修复（确保 emoji 和中文能正常输出）
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
