# -*- coding: utf-8 -*-
"""
数据库配置模块
从Nacos读取数据库连接信息
"""

import os
import requests
import json
from typing import Dict, Optional

class DatabaseConfig:
    """数据库配置类"""
    
    def __init__(self):
        self.nacos_server = os.getenv('NACOS_SERVER', 'http://localhost:8848')
        self.nacos_namespace = os.getenv('NACOS_NAMESPACE', 'public')
        self.nacos_group = os.getenv('NACOS_GROUP', 'DEFAULT_GROUP')
        self.nacos_data_id = os.getenv('NACOS_DATA_ID', 'locust-db-config')
        self._db_config = None
        self.use_mysql = os.getenv('USE_MYSQL', 'true').lower() == 'true'
    
    def get_config_from_nacos(self) -> Optional[Dict]:
        """从Nacos获取配置"""
        try:
            url = f"{self.nacos_server}/nacos/v1/cs/configs"
            params = {
                'dataId': self.nacos_data_id,
                'group': self.nacos_group,
                'tenant': self.nacos_namespace
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                config_data = response.text
                if config_data:
                    return json.loads(config_data)
            return None
        except Exception as e:
            print(f"从Nacos获取配置失败: {e}")
            return None
    
    def get_database_config(self) -> Dict:
        """获取数据库配置"""
        if self._db_config is None:
            if self.use_mysql:
                # 使用MySQL配置
                # 首先尝试从Nacos获取
                nacos_config = self.get_config_from_nacos()
                if nacos_config and 'database' in nacos_config:
                    self._db_config = nacos_config['database']
                else:
                    # 如果Nacos获取失败，使用本地MySQL配置
                    self._db_config = {
                        'type': 'mysql',
                        'host': os.getenv('DB_HOST', 'localhost'),
                        'port': int(os.getenv('DB_PORT', '3306')),
                        'database': os.getenv('DB_NAME', 'locust_auth'),
                        'user': os.getenv('DB_USER', 'root'),
                        'password': os.getenv('DB_PASSWORD', 'root'),
                        'charset': 'utf8mb4',
                        'autocommit': True,
                        'connect_timeout': 10
                    }
            else:
                # 使用SQLite配置（向后兼容）
                self._db_config = {
                    'type': 'sqlite',
                    'database': os.getenv('SQLITE_DB', 'locust_auth.db')
                }
        
        return self._db_config
    
    def refresh_config(self):
        """刷新配置"""
        self._db_config = None
        return self.get_database_config()

# 全局配置实例
db_config = DatabaseConfig()