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
                 users=None, spawn_rate=None, run_time=None, mode='standalone',
                 master_host=None, master_port=None, master_bind_port=None,
                 expect_workers=0, worker_processes=1):
        """
        初始化 Locust 实例
        
        Args:
            instance_id: 实例 ID
            script_file: 脚本文件路径
            port: Web UI 端口
            target_host: 目标主机
            users: 用户数
            spawn_rate: 生成速率
            run_time: 运行时间
            mode: 运行模式 ('standalone' | 'master' | 'worker')
            master_host: Master 主机地址（Worker 模式时使用）
            master_port: Master 端口（Worker 模式时使用）
            master_bind_port: Master 绑定端口（Master 模式时使用）
            expect_workers: 期望的 Worker 数量
            worker_processes: Worker 模式下在本地启动的进程数（利用多核）
        """
        self.instance_id = instance_id
        self.script_file = script_file
        self.port = port
        self.target_host = target_host
        self.users = users
        self.spawn_rate = spawn_rate
        self.run_time = run_time
        self.mode = mode
        self.master_host = master_host
        self.master_port = master_port
        self.master_bind_port = master_bind_port
        self.expect_workers = expect_workers
        self.worker_processes = max(1, worker_processes)
        self.process = None
        self.processes = []  # 多进程列表（Worker 多进程模式）
        self.created_at = datetime.now()
        self.status = 'stopped'

    def start(self):
        """启动Locust实例"""
        if self.process and self.process.poll() is None:
            return False, "实例已在运行"
        if self.processes and any(p.poll() is None for p in self.processes):
            return False, "实例已在运行"

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), '..', 'locust_runner.py'),
            '-f', self.script_file,
        ]
        
        # 根据模式设置不同的启动参数
        if self.mode == 'master':
            # Master 模式
            cmd.extend([
                '--master',
                '--master-bind-port', str(self.master_bind_port),
                '--web-host', '0.0.0.0',
                '--web-port', str(self.port)
            ])
            if self.expect_workers > 0:
                cmd.extend(['--expect-workers', str(self.expect_workers)])
                
        elif self.mode == 'worker':
            # Worker 模式 - 无 Web UI
            cmd.extend([
                '--worker',
                '--master-host', self.master_host,
                '--master-port', str(self.master_port)
            ])
            
        else:
            # Standalone 模式
            cmd.extend([
                '--web-host', '0.0.0.0',
                '--web-port', str(self.port)
            ])

        if self.target_host:
            cmd.extend(['--host', self.target_host])

        # 用户数和生成速率（仅 standalone 和 master 模式有效）
        if self.mode != 'worker' and self.users and self.spawn_rate:
            cmd.extend(['-u', str(self.users), '-r', str(self.spawn_rate)])
            if self.run_time:
                cmd.extend(['-t', self.run_time])

        try:
            # 构建环境变量，确保子进程能找到所有 Python 包
            env = os.environ.copy()
            import site
            user_site = site.getusersitepackages()
            if user_site and os.path.isdir(user_site):
                paths = [user_site]
                existing = env.get('PYTHONPATH', '')
                if existing:
                    paths.append(existing)
                env['PYTHONPATH'] = os.pathsep.join(paths)

            env['PYTHONUSERBASE'] = env.get('PYTHONUSERBASE', os.path.dirname(os.path.dirname(user_site)) if user_site else '')

            # 日志目录
            log_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(log_dir, exist_ok=True)

            # Worker 多进程模式：启动 N 个 Worker 子进程
            num_processes = self.worker_processes if self.mode == 'worker' else 1

            if num_processes > 1 and self.mode == 'worker':
                self.processes = []
                for i in range(num_processes):
                    log_file = os.path.join(log_dir, f'{self.instance_id}-p{i}.log')
                    log_fh = open(log_file, 'w', encoding='utf-8', buffering=1)
                    proc = subprocess.Popen(
                        cmd,
                        stdout=log_fh,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True,
                        env=env
                    )
                    self.processes.append((proc, log_fh, log_file))

                # 等待检查是否有进程立即退出
                time.sleep(1.5)
                failed = [p for p, _, _ in self.processes if p.poll() is not None]
                if len(failed) == num_processes:
                    # 全部失败
                    _, _, last_log = self.processes[-1]
                    with open(last_log, 'r', encoding='utf-8') as lf:
                        error_msg = lf.read() or '未知错误'
                    error_lines = [l for l in error_msg.strip().split('\n') if l.strip()]
                    brief_error = error_lines[-1] if error_lines else '进程启动后立即退出'
                    self.status = 'error'
                    return False, f"Locust Worker启动失败: {brief_error}"

                # 将第一个存活进程赋给 self.process（兼容现有状态检查）
                for proc, _, _ in self.processes:
                    if proc.poll() is None:
                        self.process = proc
                        break

                self.log_file = os.path.join(log_dir, f'{self.instance_id}-p0.log')
                self.status = 'running'
                alive_count = sum(1 for p, _, _ in self.processes if p.poll() is None)
                return True, f"Worker已启动 {alive_count}/{num_processes} 个进程，PID: {[p.pid for p, _, _ in self.processes]}"

            else:
                # 单进程模式（原逻辑）
                self.log_file = os.path.join(log_dir, f'{self.instance_id}.log')
                self._log_fh = open(self.log_file, 'w', encoding='utf-8', buffering=1)

                self.process = subprocess.Popen(
                    cmd,
                    stdout=self._log_fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env
                )
                # 等待短暂时间检查进程是否立即退出
                time.sleep(1.5)
                if self.process.poll() is not None:
                    self._log_fh.flush()
                    with open(self.log_file, 'r', encoding='utf-8') as lf:
                        error_msg = lf.read() or '未知错误'
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
        # 多进程模式
        if self.processes:
            pids = []
            for proc, log_fh, _ in self.processes:
                if proc.poll() is None:
                    try:
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait()
                        pids.append(proc.pid)
                    except Exception:
                        pass
                if log_fh:
                    try:
                        log_fh.close()
                    except Exception:
                        pass
            self.processes = []
            self.process = None
            self.status = 'stopped'
            return True, f"已停止 {len(pids)} 个Worker进程，PIDs: {pids}"

        # 单进程模式
        if not self.process:
            return False, "实例未运行"

        if self.process.poll() is not None:
            self.status = 'stopped'
            if hasattr(self, '_log_fh') and self._log_fh:
                self._log_fh.close()
            return False, "实例已停止"

        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

            if hasattr(self, '_log_fh') and self._log_fh:
                self._log_fh.close()

            pid = self.process.pid
            self.status = 'stopped'
            return True, f"实例已停止，端口: {self.port}, PID: {pid}"
        except Exception as e:
            return False, f"停止失败: {str(e)}"

    def is_running(self):
        """检查实例是否运行中"""
        # 多进程模式：任一进程存活即为运行中
        if self.processes:
            running = any(p.poll() is None for p, _, _ in self.processes)
            if not running:
                self.status = 'stopped'
            return running

        # 单进程模式
        if not self.process:
            return False
        running = self.process.poll() is None
        if not running:
            self.status = 'stopped'
        return running

    def get_info(self):
        """获取实例信息"""
        info = {
            'instance_id': self.instance_id,
            'script_file': self.script_file,
            'port': self.port,
            'target_host': self.target_host,
            'users': self.users,
            'spawn_rate': self.spawn_rate,
            'run_time': self.run_time,
            'mode': self.mode,
            'status': self.status,
            'is_running': self.is_running(),
            'created_at': self.created_at.isoformat(),
            'pid': self.process.pid if self.process else None,
            'log_file': getattr(self, 'log_file', None)
        }
        
        # 根据模式添加额外信息
        if self.mode == 'master':
            info['master_bind_port'] = self.master_bind_port
            info['expect_workers'] = self.expect_workers
            info['web_url'] = f'http://localhost:{self.port}'
        elif self.mode == 'worker':
            info['master_host'] = self.master_host
            info['master_port'] = self.master_port
            info['web_url'] = None  # Worker 没有 Web UI
        else:
            info['web_url'] = f'http://localhost:{self.port}'
            
        return info
