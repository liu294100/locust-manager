# -*- coding: utf-8 -*-
"""
配置管理模块
从环境变量和.env文件读取配置信息
"""

import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class Config:
    """应用配置类"""
    
    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'locust-manager-secret-key-2024')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    # 应用配置
    APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.getenv('APP_PORT', 8088))
    BASE_LOCUST_PORT = int(os.getenv('BASE_LOCUST_PORT', 8089))
    
    # 数据库配置
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '123456')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'locust_manager')
    
    # Redis配置
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    # 集群配置
    CLUSTER_MODE = os.getenv('CLUSTER_MODE', 'true').lower() == 'true'
    CLUSTER_NODE_ID = os.getenv('CLUSTER_NODE_ID', 'node-1')
    CLUSTER_HEARTBEAT_INTERVAL = int(os.getenv('CLUSTER_HEARTBEAT_INTERVAL', 30))
    
    # 文件上传配置
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'scripts/tmp')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    ALLOWED_EXTENSIONS = {'py'}
    
    # AWS S3配置（预留扩展）
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_REGION = os.getenv('AWS_REGION', '')
    S3_BUCKET = os.getenv('S3_BUCKET', '')
    S3_ENABLED = os.getenv('S3_ENABLED', 'false').lower() == 'true'
    
    @classmethod
    def get_mysql_config(cls):
        """获取MySQL配置字典"""
        return {
            'host': cls.MYSQL_HOST,
            'port': cls.MYSQL_PORT,
            'user': cls.MYSQL_USER,
            'password': cls.MYSQL_PASSWORD,
            'database': cls.MYSQL_DATABASE,
            'charset': 'utf8mb4'
        }
    
    @classmethod
    def get_redis_config(cls):
        """获取Redis配置字典"""
        config = {
            'host': cls.REDIS_HOST,
            'port': cls.REDIS_PORT,
            'db': cls.REDIS_DB,
            'decode_responses': True
        }
        if cls.REDIS_PASSWORD:
            config['password'] = cls.REDIS_PASSWORD
        return config

# 创建配置实例
config = Config()