# -*- coding: utf-8 -*-
"""
数据库管理模块
支持MySQL数据库连接、用户认证和数据操作
"""

import hashlib
import pymysql
import logging
from datetime import datetime
from typing import Optional, Dict, List
from .config import config

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self):
        self.config = config.get_mysql_config()
        self.connection = None
        self.logger = logging.getLogger(__name__)
        
    def get_connection(self):
        """获取数据库连接"""
        try:
            if self.connection is None or not self.connection.open:
                self.connection = pymysql.connect(**self.config)
            return self.connection
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            raise
    
    def connect(self):
        """连接数据库"""
        try:
            self.get_connection()
            self.logger.info("数据库连接成功")
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            raise
    
    def close_connection(self):
        """关闭数据库连接"""
        if self.connection and self.connection.open:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = True):
        """执行SQL查询"""
        try:
            conn = self.get_connection()
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query, params)
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            self.logger.error(f"SQL执行失败: {e}, Query: {query}")
            if self.connection:
                self.connection.rollback()
            raise
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = "locust-manager-salt"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """验证用户登录"""
        try:
            password_hash = self._hash_password(password)
            query = """
                SELECT id, username, email, role, is_active 
                FROM users 
                WHERE username = %s AND password_hash = %s AND is_active = TRUE
            """
            user = self.execute_query(query, (username, password_hash), fetch_one=True)
            return user
        except Exception as e:
            self.logger.error(f"用户验证失败: {e}")
            return None
    
    def create_user(self, username: str, password: str, email: str = None, role: str = 'user') -> bool:
        """创建用户"""
        try:
            password_hash = self._hash_password(password)
            query = """
                INSERT INTO users (username, password_hash, email, role) 
                VALUES (%s, %s, %s, %s)
            """
            self.execute_query(query, (username, password_hash, email, role), fetch_all=False)
            return True
        except Exception as e:
            self.logger.error(f"创建用户失败: {e}")
            return False
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """根据ID获取用户信息"""
        try:
            query = "SELECT id, username, email, role, created_at FROM users WHERE id = %s AND is_active = TRUE"
            return self.execute_query(query, (user_id,), fetch_one=True)
        except Exception as e:
            self.logger.error(f"获取用户信息失败: {e}")
            return None
    
    def create_test_task(self, task_data: Dict) -> Optional[int]:
        """创建压测任务"""
        try:
            query = """
                INSERT INTO test_tasks (task_name, script_file, target_host, users, spawn_rate, 
                                      run_time, created_by, cluster_mode, node_count, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                task_data.get('task_name'),
                task_data.get('script_file'),
                task_data.get('target_host'),
                task_data.get('users', 1),
                task_data.get('spawn_rate', 1.0),
                task_data.get('run_time'),
                task_data.get('created_by'),
                task_data.get('cluster_mode', False),
                task_data.get('node_count', 1),
                task_data.get('description')
            )
            self.execute_query(query, params, fetch_all=False)
            
            # 获取插入的任务ID
            conn = self.get_connection()
            return conn.insert_id()
        except Exception as e:
            self.logger.error(f"创建压测任务失败: {e}")
            return None
    
    def update_task_status(self, task_id: int, status: str, started_at: datetime = None, completed_at: datetime = None) -> bool:
        """更新任务状态"""
        try:
            if started_at and completed_at:
                query = "UPDATE test_tasks SET status = %s, started_at = %s, completed_at = %s WHERE id = %s"
                params = (status, started_at, completed_at, task_id)
            elif started_at:
                query = "UPDATE test_tasks SET status = %s, started_at = %s WHERE id = %s"
                params = (status, started_at, task_id)
            elif completed_at:
                query = "UPDATE test_tasks SET status = %s, completed_at = %s WHERE id = %s"
                params = (status, completed_at, task_id)
            else:
                query = "UPDATE test_tasks SET status = %s WHERE id = %s"
                params = (status, task_id)
            
            self.execute_query(query, params, fetch_all=False)
            return True
        except Exception as e:
            self.logger.error(f"更新任务状态失败: {e}")
            return False
    
    def get_test_tasks(self, user_id: int = None, status: str = None, limit: int = 50) -> List[Dict]:
        """获取压测任务列表"""
        try:
            query = """
                SELECT t.*, u.username as created_by_name 
                FROM test_tasks t 
                LEFT JOIN users u ON t.created_by = u.id 
                WHERE 1=1
            """
            params = []
            
            if user_id:
                query += " AND t.created_by = %s"
                params.append(user_id)
            
            if status:
                query += " AND t.status = %s"
                params.append(status)
            
            query += " ORDER BY t.created_at DESC LIMIT %s"
            params.append(limit)
            
            return self.execute_query(query, tuple(params))
        except Exception as e:
            self.logger.error(f"获取任务列表失败: {e}")
            return []
    
    def get_tasks_paginated(self, page: int = 1, per_page: int = 20, user_id: int = None, status: str = None) -> List[Dict]:
        """获取分页的压测任务列表"""
        try:
            offset = (page - 1) * per_page
            query = """
                SELECT t.*, u.username as created_by_name 
                FROM test_tasks t 
                LEFT JOIN users u ON t.created_by = u.id 
                WHERE 1=1
            """
            params = []
            
            if user_id:
                query += " AND t.created_by = %s"
                params.append(user_id)
            
            if status:
                query += " AND t.status = %s"
                params.append(status)
            
            query += " ORDER BY t.created_at DESC LIMIT %s OFFSET %s"
            params.extend([per_page, offset])
            
            return self.execute_query(query, tuple(params))
        except Exception as e:
            self.logger.error(f"获取分页任务列表失败: {e}")
            return []
    
    def get_test_task(self, task_id: int) -> Optional[Dict]:
        """获取单个压测任务"""
        try:
            query = """
                SELECT t.*, u.username as created_by_name 
                FROM test_tasks t 
                LEFT JOIN users u ON t.created_by = u.id 
                WHERE t.id = %s
            """
            return self.execute_query(query, (task_id,), fetch_one=True)
        except Exception as e:
            self.logger.error(f"获取任务详情失败: {e}")
            return None
    
    def get_recent_tasks(self, limit: int = 10) -> List[Dict]:
        """获取最近的压测任务"""
        try:
            query = """
                SELECT t.*, u.username as created_by_name 
                FROM test_tasks t 
                LEFT JOIN users u ON t.created_by = u.id 
                ORDER BY t.created_at DESC 
                LIMIT %s
            """
            return self.execute_query(query, (limit,))
        except Exception as e:
            self.logger.error(f"获取最近任务失败: {e}")
            return []
    
    def create_test_instance(self, instance_data: Dict) -> bool:
        """创建压测实例记录"""
        try:
            query = """
                INSERT INTO test_instances (instance_id, task_id, node_id, port, pid, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                instance_data.get('instance_id'),
                instance_data.get('task_id'),
                instance_data.get('node_id'),
                instance_data.get('port'),
                instance_data.get('pid'),
                instance_data.get('status', 'starting')
            )
            self.execute_query(query, params, fetch_all=False)
            return True
        except Exception as e:
            self.logger.error(f"创建实例记录失败: {e}")
            return False
    
    def update_instance_status(self, instance_id: str, status: str, pid: int = None) -> bool:
        """更新实例状态"""
        try:
            if pid:
                query = "UPDATE test_instances SET status = %s, pid = %s, last_heartbeat = NOW() WHERE instance_id = %s"
                params = (status, pid, instance_id)
            else:
                query = "UPDATE test_instances SET status = %s, last_heartbeat = NOW() WHERE instance_id = %s"
                params = (status, instance_id)
            
            self.execute_query(query, params, fetch_all=False)
            return True
        except Exception as e:
            self.logger.error(f"更新实例状态失败: {e}")
            return False
    
    def get_test_instances(self, task_id: int = None) -> List[Dict]:
        """获取压测实例列表"""
        try:
            if task_id:
                query = "SELECT * FROM test_instances WHERE task_id = %s ORDER BY created_at DESC"
                params = (task_id,)
            else:
                query = "SELECT * FROM test_instances ORDER BY created_at DESC LIMIT 100"
                params = ()
            
            return self.execute_query(query, params)
        except Exception as e:
            self.logger.error(f"获取实例列表失败: {e}")
            return []
    
    def save_test_result(self, result_data: Dict) -> bool:
        """保存压测结果"""
        try:
            query = """
                INSERT INTO test_results (task_id, instance_id, request_method, request_name,
                                        num_requests, num_failures, median_response_time,
                                        average_response_time, min_response_time, max_response_time,
                                        average_content_size, requests_per_second, failures_per_second)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                result_data.get('task_id'),
                result_data.get('instance_id'),
                result_data.get('request_method'),
                result_data.get('request_name'),
                result_data.get('num_requests', 0),
                result_data.get('num_failures', 0),
                result_data.get('median_response_time', 0),
                result_data.get('average_response_time', 0),
                result_data.get('min_response_time', 0),
                result_data.get('max_response_time', 0),
                result_data.get('average_content_size', 0),
                result_data.get('requests_per_second', 0),
                result_data.get('failures_per_second', 0)
            )
            self.execute_query(query, params, fetch_all=False)
            return True
        except Exception as e:
            self.logger.error(f"保存压测结果失败: {e}")
            return False
    
    def get_test_results(self, task_id: int) -> List[Dict]:
        """获取压测结果"""
        try:
            query = """
                SELECT * FROM test_results 
                WHERE task_id = %s 
                ORDER BY recorded_at DESC
            """
            return self.execute_query(query, (task_id,))
        except Exception as e:
            self.logger.error(f"获取压测结果失败: {e}")
            return []
    
    def log_system_event(self, level: str, message: str, **kwargs) -> bool:
        """记录系统日志"""
        try:
            query = """
                INSERT INTO system_logs (level, message, module, function_name, line_number,
                                       user_id, task_id, instance_id, node_id, extra_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                level,
                message,
                kwargs.get('module'),
                kwargs.get('function_name'),
                kwargs.get('line_number'),
                kwargs.get('user_id'),
                kwargs.get('task_id'),
                kwargs.get('instance_id'),
                kwargs.get('node_id'),
                kwargs.get('extra_data')
            )
            self.execute_query(query, params, fetch_all=False)
            return True
        except Exception as e:
            self.logger.error(f"记录系统日志失败: {e}")
            return False
    
    def get_all_script_files(self, user_id: int = None) -> List[Dict]:
        """获取所有脚本文件列表"""
        try:
            query = """
                SELECT s.*, u.username as uploaded_by_name 
                FROM script_files s 
                LEFT JOIN users u ON s.uploaded_by = u.id 
                WHERE s.is_active = TRUE
            """
            params = []
            
            if user_id:
                query += " AND s.uploaded_by = %s"
                params.append(user_id)
            
            query += " ORDER BY s.uploaded_at DESC"
            
            return self.execute_query(query, tuple(params) if params else ())
        except Exception as e:
            self.logger.error(f"获取脚本文件列表失败: {e}")
            return []
    
    def get_script_file(self, script_id: int) -> Optional[Dict]:
        """获取单个脚本文件信息"""
        try:
            query = """
                SELECT s.*, u.username as uploaded_by_name 
                FROM script_files s 
                LEFT JOIN users u ON s.uploaded_by = u.id 
                WHERE s.id = %s
            """
            return self.execute_query(query, (script_id,), fetch_one=True)
        except Exception as e:
            self.logger.error(f"获取脚本文件失败: {e}")
            return None

    def get_script_file_by_filename(self, filename: str) -> Optional[Dict]:
        """通过文件名获取脚本文件信息"""
        try:
            query = """
                SELECT s.*, u.username as uploaded_by_name 
                FROM script_files s 
                LEFT JOIN users u ON s.uploaded_by = u.id 
                WHERE s.filename = %s AND s.is_active = TRUE
            """
            return self.execute_query(query, (filename,), fetch_one=True)
        except Exception as e:
            self.logger.error(f"通过文件名获取脚本文件失败: {e}")
            return None

    def create_script_file(self, script_data: Dict) -> Optional[int]:
        """创建脚本文件记录"""
        try:
            query = """
                INSERT INTO script_files (
                    filename, file_path, file_size, file_hash, 
                    uploaded_by, description, uploaded_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                script_data.get('filename'),
                script_data.get('file_path'),
                script_data.get('file_size', 0),
                script_data.get('file_hash'),
                script_data.get('uploaded_by'),
                script_data.get('description', ''),
                script_data.get('upload_time', datetime.now())
            )
            
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            self.logger.error(f"创建脚本文件记录失败: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def delete_script_file(self, script_id: int) -> bool:
        """删除脚本文件记录"""
        try:
            query = "UPDATE script_files SET is_active = FALSE WHERE id = %s"
            self.execute_query(query, (script_id,), fetch_all=False)
            return True
        except Exception as e:
            self.logger.error(f"删除脚本文件记录失败: {e}")
            return False

    def get_dashboard_stats(self) -> Dict:
        """获取仪表板统计数据"""
        try:
            # 获取任务统计
            task_stats = self.execute_query("SELECT * FROM active_tasks_summary", fetch_one=True)
            
            # 获取集群统计
            cluster_stats = self.execute_query("SELECT * FROM cluster_status_summary", fetch_one=True)
            
            # 获取最近的系统日志
            recent_logs = self.execute_query("""
                SELECT level, message, created_at 
                FROM system_logs 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            
            return {
                'tasks': task_stats or {},
                'cluster': cluster_stats or {},
                'recent_logs': recent_logs or []
            }
        except Exception as e:
            self.logger.error(f"获取仪表板统计失败: {e}")
            return {'tasks': {}, 'cluster': {}, 'recent_logs': []}

# 创建数据库管理器实例
db_manager = DatabaseManager()