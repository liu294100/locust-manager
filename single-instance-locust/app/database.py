# -*- coding: utf-8 -*-
"""
数据库管理模块
支持MySQL和SQLite数据库，用户认证和数据库操作
"""

import hashlib
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional, Dict
from .config import db_config, DatabaseConfig

# 动态导入数据库驱动
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pymysql = None

try:
    import sqlite3
except ImportError:
    sqlite3 = None

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self):
        self.config = db_config.get_database_config()
        self.db_type = self.config.get('type', 'sqlite')
        self.connection = None
        
        # 如果配置为MySQL，先测试连接，失败则回退到SQLite
        if self.db_type == 'mysql':
            try:
                test_conn = self.get_connection()
                test_conn.close()
                print("✅ MySQL连接成功")
            except Exception as e:
                print(f"❌ MySQL连接失败: {e}")
                print("🔄 自动切换到SQLite数据库")
                self.db_type = 'sqlite'
                self.config = {'type': 'sqlite', 'database': 'locust_auth.db'}
        
        self.init_database()
    
    def connect(self):
        """连接数据库"""
        try:
            # 使用SQLite作为本地数据库
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locust_auth.db')
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        except Exception as e:
            print(f"数据库连接失败: {e}")
            self.connection = None
    
    def init_database(self):
        """初始化数据库"""
        try:
            # 测试数据库连接
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == 'mysql':
                    # 检查用户表是否存在
                    cursor.execute("SHOW TABLES LIKE 'users'")
                    table_exists = cursor.fetchone() is not None
                else:
                    # SQLite
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                    table_exists = cursor.fetchone() is not None
                
                if not table_exists:
                    print("📋 用户表不存在，开始初始化数据库...")
                    self.execute_init_sql()
                else:
                    print("✅ 数据库已存在，跳过初始化")
                    
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
            print("🔧 尝试执行初始化SQL...")
            self.execute_init_sql()
    
    def get_connection(self):
        """获取数据库连接"""
        if self.db_type == 'mysql':
            if pymysql is None:
                raise ImportError("pymysql is required for MySQL support. Install it with: pip install pymysql")
            
            return pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config['charset'],
                autocommit=self.config.get('autocommit', True),
                connect_timeout=self.config.get('connect_timeout', 10)
            )
        else:
            # SQLite
            if sqlite3 is None:
                raise ImportError("sqlite3 is required for SQLite support")
            if self.connection is None:
                try:
                    # 使用SQLite作为本地数据库
                    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locust_auth.db')
                    self.connection = sqlite3.connect(db_path, check_same_thread=False)
                    self.connection.row_factory = sqlite3.Row  # 使结果可以像字典一样访问
                except Exception as e:
                    print(f"数据库连接失败: {e}")
                    raise
            return self.connection
    
    def close_connection(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_init_sql(self):
        """执行初始化SQL脚本"""
        init_sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), f'init_{self.db_type}.sql')
        
        if not os.path.exists(init_sql_path):
            print(f"⚠️  初始化SQL文件不存在: {init_sql_path}")
            print("🔧 正在生成初始化SQL文件...")
            
            # 运行生成脚本
            generate_script = os.path.join(os.path.dirname(__file__), 'generate_init_sql.py')
            if os.path.exists(generate_script):
                try:
                    subprocess.run([sys.executable, generate_script, '--type', self.db_type], check=True, cwd=os.path.dirname(os.path.dirname(__file__)))
                    print("✅ 初始化SQL文件生成成功")
                except subprocess.CalledProcessError as e:
                    print(f"❌ 生成初始化SQL文件失败: {e}")
                    return False
            else:
                print(f"❌ 生成脚本不存在: {generate_script}")
                return False
        
        if self.db_type == 'mysql':
            return self._execute_mysql_init_sql(init_sql_path)
        else:
            return self._execute_sqlite_init_sql(init_sql_path)
    
    def _execute_mysql_init_sql(self, sql_file_path: str) -> bool:
        """执行MySQL初始化SQL"""
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割SQL语句
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for statement in statements:
                    if statement:
                        try:
                            cursor.execute(statement)
                        except Exception as e:
                            # 忽略一些常见的警告（如数据库已存在等）
                            if 'already exists' not in str(e).lower():
                                print(f"⚠️  SQL执行警告: {e}")
                
                conn.commit()
                print("✅ MySQL数据库初始化完成")
                return True
                
        except Exception as e:
            print(f"❌ MySQL初始化失败: {e}")
            return False
    
    def _execute_sqlite_init_sql(self, sql_file_path: str) -> bool:
        """执行SQLite初始化SQL（转换MySQL语法）"""
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 转换MySQL语法到SQLite
            sqlite_sql = self._convert_mysql_to_sqlite(sql_content)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executescript(sqlite_sql)
                conn.commit()
                print("✅ SQLite数据库初始化完成")
                return True
                
        except Exception as e:
            print(f"❌ SQLite初始化失败: {e}")
            return False
    
    def _convert_mysql_to_sqlite(self, mysql_sql: str) -> str:
        """将MySQL SQL转换为SQLite兼容的SQL"""
        # 基本的MySQL到SQLite转换
        sqlite_sql = mysql_sql
        
        # 移除MySQL特定的语句
        sqlite_sql = sqlite_sql.replace('CREATE DATABASE IF NOT EXISTS locust_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;', '')
        sqlite_sql = sqlite_sql.replace('USE locust_auth;', '')
        
        # 转换数据类型
        sqlite_sql = sqlite_sql.replace('INT AUTO_INCREMENT PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        sqlite_sql = sqlite_sql.replace('VARCHAR(50)', 'TEXT')
        sqlite_sql = sqlite_sql.replace('VARCHAR(100)', 'TEXT')
        sqlite_sql = sqlite_sql.replace('VARCHAR(64)', 'TEXT')
        sqlite_sql = sqlite_sql.replace('BOOLEAN', 'INTEGER')
        sqlite_sql = sqlite_sql.replace('TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        sqlite_sql = sqlite_sql.replace('ON UPDATE CURRENT_TIMESTAMP', '')
        
        # 移除MySQL特定的表选项
        sqlite_sql = sqlite_sql.replace('ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci', '')
        sqlite_sql = sqlite_sql.replace('COMMENT=\'用户表\'', '')
        
        # 移除注释
        lines = sqlite_sql.split('\n')
        filtered_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('--') and 'COMMENT' not in line:
                # 移除行内注释
                if 'COMMENT' in line:
                    line = line.split('COMMENT')[0].strip().rstrip(',')
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def init_tables(self):
        """初始化用户表"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 创建用户表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
            """
            
            cursor.execute(create_table_sql)
            
            # 检查是否有默认管理员用户，如果没有则创建
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            if cursor.fetchone()[0] == 0:
                admin_password_hash = hashlib.sha256('xxxxxx'.encode()).hexdigest()
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    ('admin', admin_password_hash)
                )
                conn.commit()
            
            
            cursor.close()
            return True
            
        except Exception as e:
            print(f"初始化数据库表失败: {e}")
            return False
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """验证用户登录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 计算密码哈希
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # 查询用户
            if self.db_type == 'mysql':
                cursor.execute(
                    "SELECT id, username, created_at FROM users WHERE username = %s AND password_hash = %s AND is_active = 1",
                    (username, password_hash)
                )
            else:
                cursor.execute(
                    "SELECT id, username, created_at FROM users WHERE username = ? AND password_hash = ? AND is_active = 1",
                    (username, password_hash)
                )
            
            row = cursor.fetchone()
            
            if row:
                # 更新最后登录时间
                if self.db_type == 'mysql':
                    cursor.execute(
                        "UPDATE users SET updated_at = NOW() WHERE id = %s",
                        (row[0],)
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (row[0],)
                    )
                
                if not self.config.get('autocommit', False):
                    conn.commit()
                
                cursor.close()
                return dict(row) if hasattr(row, 'keys') else {'id': row[0], 'username': row[1], 'created_at': row[2]}
            
            cursor.close()
            return None
            
        except Exception as e:
            print(f"用户验证失败: {e}")
            return None
    
    def create_user(self, username: str, password: str) -> bool:
        """创建新用户"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 计算密码哈希
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # 插入用户
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            
            conn.commit()
            cursor.close()
            return True
            
        except sqlite3.IntegrityError:
            print(f"用户名 {username} 已存在")
            return False
        except Exception as e:
            print(f"创建用户失败: {e}")
            return False
    
    def change_password(self, username: str, new_password: str) -> bool:
        """修改用户密码"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 计算新密码哈希
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            
            # 更新密码
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (password_hash, username)
            )
            
            conn.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows > 0
            
        except Exception as e:
            print(f"修改密码失败: {e}")
            return False
    
    def get_all_users(self):
        """获取所有用户信息（用于调试）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, username, created_at, is_active FROM users")
            rows = cursor.fetchall()
            cursor.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return []

# 全局数据库管理实例
db_manager = DatabaseManager()