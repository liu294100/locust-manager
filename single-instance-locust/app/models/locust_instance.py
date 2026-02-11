# -*- coding: utf-8 -*-
"""Locust实例模型"""

import os
import subprocess
import sys
import time
from datetime import datetime


class LocustInstance:
    """Locust实例类"""

    def __init__(self, instance_id, script_file, port, target_host=None,
                 users=None, spawn_rate=None, run_time=None):
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

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), '..', 'locust_runner.py'),
            '-f', self.script_file,
            '--web-host', '0.0.0.0',
            '--web-port', str(self.port)
        ]

        if self.target_host:
            cmd.extend(['--host', self.target_host])

        if self.users and self.spawn_rate:
            cmd.extend(['-u', str(self.users), '-r', str(self.spawn_rate)])
            if self.run_time:
                cmd.extend(['-t', self.run_time])

        try:
            # 构建环境变量，确保子进程能找到所有 Python 包
            env = os.environ.copy()
            import site
            user_site = site.getusersitepackages()
            if user_site and os.path.isdir(user_site):
                # 将 user site-packages 加入 PYTHONPATH，解决 Anaconda 环境下
                # zope namespace package 分散在不同目录导致的 import 失败问题
                paths = [user_site]
                existing = env.get('PYTHONPATH', '')
                if existing:
                    paths.append(existing)
                env['PYTHONPATH'] = os.pathsep.join(paths)

            # 同时注入一段修复 zope namespace 的启动代码
            env['PYTHONUSERBASE'] = env.get('PYTHONUSERBASE', os.path.dirname(os.path.dirname(user_site)) if user_site else '')

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            # 等待短暂时间检查进程是否立即退出
            time.sleep(1.5)
            if self.process.poll() is not None:
                # 进程已退出，读取错误信息
                stderr_output = self.process.stderr.read() if self.process.stderr else ''
                stdout_output = self.process.stdout.read() if self.process.stdout else ''
                error_msg = stderr_output or stdout_output or '未知错误'
                # 截取关键错误信息
                error_lines = [l for l in error_msg.strip().split('\n') if l.strip()]
                brief_error = error_lines[-1] if error_lines else '进程启动后立即退出'
                self.status = 'error'
                return False, f"Locust启动失败: {brief_error}"

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
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
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
