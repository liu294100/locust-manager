#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化SQL脚本生成器
支持 MySQL 和 SQLite 数据库
生成包含用户表结构和默认用户数据的init.sql文件
python app/generate_init_sql.py --type sqlite
python app/generate_init_sql.py --type mysql
"""

import hashlib
import os
import argparse
from datetime import datetime

def generate_password_hash(password: str) -> str:
    """生成密码的SHA256哈希值"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_mysql_sql():
    """生成MySQL初始化SQL脚本"""
    
    # 默认管理员密码
    admin_password = "123456"
    admin_password_hash = generate_password_hash(admin_password)
    
    # 当前时间戳
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    sql_content = f"""-- Locust认证系统MySQL数据库初始化脚本
-- 生成时间: {current_time}
-- 注意: 此脚本会删除现有的用户表并重新创建

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS locust_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE locust_auth;

-- 删除现有用户表（如果存在）
DROP TABLE IF EXISTS users;

-- 创建用户表
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(64) NOT NULL COMMENT '密码哈希值(SHA256)',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱地址',
    full_name VARCHAR(100) DEFAULT NULL COMMENT '全名',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    is_admin BOOLEAN DEFAULT FALSE COMMENT '是否管理员',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    last_login TIMESTAMP NULL DEFAULT NULL COMMENT '最后登录时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 创建索引
CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_is_active ON users(is_active);

-- 插入默认管理员用户
INSERT INTO users (
    username, 
    password_hash, 
    email, 
    full_name, 
    is_active, 
    is_admin
) VALUES (
    'admin',
    '{admin_password_hash}',
    'admin@locust.local',
    '管理员',
    TRUE,
    TRUE
);

-- 显示创建结果
SELECT 'Database initialization completed successfully!' as status;
SELECT COUNT(*) as user_count FROM users;
SELECT username, email, full_name, is_admin, is_active, created_at FROM users;
"""
    
    return sql_content

def generate_sqlite_sql():
    """生成SQLite初始化SQL脚本"""
    
    # 默认管理员密码
    admin_password = "123456"
    admin_password_hash = generate_password_hash(admin_password)
    
    # 当前时间戳
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    sql_content = f"""-- Locust认证系统SQLite数据库初始化脚本
-- 生成时间: {current_time}
-- 注意: 此脚本会删除现有的用户表并重新创建

-- 删除现有用户表（如果存在）
DROP TABLE IF EXISTS users;

-- 创建用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT DEFAULT NULL,
    full_name TEXT DEFAULT NULL,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL
);

-- 创建索引
CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_is_active ON users(is_active);

-- 创建触发器以自动更新 updated_at 字段
CREATE TRIGGER update_users_updated_at 
    AFTER UPDATE ON users
    FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 插入默认管理员用户
INSERT INTO users (
    username, 
    password_hash, 
    email, 
    full_name, 
    is_active, 
    is_admin
) VALUES (
    'admin',
    '{admin_password_hash}',
    'admin@locust.local',
    '管理员',
    1,
    1
);

-- 显示创建结果
SELECT 'Database initialization completed successfully!' as status;
SELECT COUNT(*) as user_count FROM users;
SELECT username, email, full_name, is_admin, is_active, created_at FROM users;
"""
    
    return sql_content

def save_init_sql(db_type: str = "mysql", output_file: str = None):
    """保存初始化SQL到文件"""
    try:
        # 根据数据库类型生成SQL内容
        if db_type.lower() == "mysql":
            sql_content = generate_mysql_sql()
            default_filename = "init_mysql.sql"
        elif db_type.lower() == "sqlite":
            sql_content = generate_sqlite_sql()
            default_filename = "init_sqlite.sql"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        
        # 如果没有指定输出文件名，使用默认文件名
        if output_file is None:
            output_file = default_filename
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else '.'
        os.makedirs(output_dir, exist_ok=True)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        
        print(f"✅ {db_type.upper()} 初始化SQL脚本已生成: {os.path.abspath(output_file)}")
        print(f"📝 文件大小: {os.path.getsize(output_file)} bytes")
        print("\n📋 默认用户信息:")
        print("   - 管理员: admin / 123456")
        
        print("\n🚀 使用方法:")
        if db_type.lower() == "mysql":
            print(f"   mysql -u root -p < {output_file}")
            print("   或在MySQL客户端中执行: source " + output_file)
        elif db_type.lower() == "sqlite":
            print(f"   sqlite3 locust_auth.db < {output_file}")
            print("   或在SQLite客户端中执行: .read " + output_file)
        
        return True
        
    except Exception as e:
        print(f"❌ 生成SQL脚本失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Locust 数据库初始化SQL脚本生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python generate_init_sql.py                    # 生成MySQL脚本 (默认)
  python generate_init_sql.py --type mysql       # 生成MySQL脚本
  python generate_init_sql.py --type sqlite      # 生成SQLite脚本
  python generate_init_sql.py --type mysql -o custom.sql  # 自定义输出文件名
  python generate_init_sql.py --all              # 生成所有类型的脚本
        """
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["mysql", "sqlite"],
        default="mysql",
        help="数据库类型 (默认: mysql)"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="输出文件名 (默认: init_<type>.sql)"
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="生成所有支持的数据库类型脚本"
    )
    
    args = parser.parse_args()
    
    print("🔧 Locust 数据库初始化脚本生成器")
    print("=" * 50)
    
    success = True
    
    if args.all:
        # 生成所有类型的脚本
        print("📦 生成所有支持的数据库类型脚本...")
        print()
        
        for db_type in ["mysql", "sqlite"]:
            print(f"🔄 正在生成 {db_type.upper()} 脚本...")
            if not save_init_sql(db_type):
                success = False
            print()
    else:
        # 生成指定类型的脚本
        print(f"🔄 正在生成 {args.type.upper()} 脚本...")
        success = save_init_sql(args.type, args.output)
    
    if success:
        print("\n✨ 脚本生成完成！")
        print("\n⚠️  注意事项:")
        if args.all or args.type == "mysql":
            print("   MySQL:")
            print("     1. 请确保MySQL服务已启动")
            print("     2. 请确保有足够的数据库权限")
        if args.all or args.type == "sqlite":
            print("   SQLite:")
            print("     1. 无需额外服务，直接使用文件数据库")
            print("     2. 确保有文件写入权限")
        print("   通用:")
        print("     1. 此脚本会删除现有的users表")
        print("     2. 密码使用SHA256哈希存储")
        print("     3. 默认创建管理员和测试用户")
    else:
        print("\n❌ 脚本生成失败！")
        exit(1)

if __name__ == "__main__":
    main()