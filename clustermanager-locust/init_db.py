#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
"""

import pymysql
import hashlib
from app.config import config

def hash_password(password: str) -> str:
    """密码哈希"""
    salt = "locust-manager-salt"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def init_database():
    """初始化数据库"""
    # 连接MySQL服务器（不指定数据库）
    connection = pymysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # 读取并执行SQL文件
            with open('init_database.sql', 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割SQL语句并执行
            sql_statements = sql_content.split(';')
            for statement in sql_statements:
                statement = statement.strip()
                if statement:
                    print(f"执行SQL: {statement[:50]}...")
                    cursor.execute(statement)
            
            connection.commit()
            print("数据库初始化完成")
            
            # 创建默认管理员用户
            connection.select_db('locust_manager')
            
            # 检查是否已存在管理员用户
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = 'admin'")
            result = cursor.fetchone()
            
            if result['count'] == 0:
                admin_password_hash = hash_password('admin123')
                cursor.execute("""
                    INSERT INTO users (username, password_hash, email, role) 
                    VALUES ('admin', %s, 'admin@locust-manager.com', 'admin')
                """, (admin_password_hash,))
                connection.commit()
                print("默认管理员用户创建完成")
                print("用户名: admin")
                print("密码: admin123")
            else:
                print("管理员用户已存在")
                
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        connection.rollback()
    finally:
        connection.close()

if __name__ == '__main__':
    init_database()