# -*- coding: utf-8 -*-
"""
脚本文件管理模块
负责上传、存储和管理Locust测试脚本
"""

import os
import hashlib
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from werkzeug.utils import secure_filename
import logging
from .config import config
from .database import db_manager

class ScriptManager:
    """脚本管理器"""
    
    def __init__(self):
        self.upload_folder = config.UPLOAD_FOLDER
        self.allowed_extensions = {'.py'}
        self.logger = logging.getLogger(__name__)
        
        # 确保上传目录存在
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def _is_allowed_file(self, filename: str) -> bool:
        """检查文件扩展名是否允许"""
        return os.path.splitext(filename)[1].lower() in self.allowed_extensions
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _validate_locust_script(self, file_path: str) -> bool:
        """验证Locust脚本的有效性"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 基本检查：是否包含必要的Locust导入和类
            required_patterns = [
                'from locust import',
                'class',
                'HttpUser'
            ]
            
            for pattern in required_patterns:
                if pattern not in content:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证脚本失败: {e}")
            return False
    
    def upload_script(self, file, user_id: int, description: str = None) -> Optional[Dict]:
        """上传脚本文件"""
        try:
            if not file or not file.filename:
                return None
            
            # 检查文件扩展名
            if not self._is_allowed_file(file.filename):
                raise ValueError("不支持的文件类型，只允许.py文件")
            
            # 生成安全的文件名
            filename = secure_filename(file.filename)
            if not filename:
                raise ValueError("无效的文件名")
            
            # 生成唯一文件名（添加时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{timestamp}{ext}"
            
            # 保存文件
            file_path = os.path.join(self.upload_folder, unique_filename)
            file.save(file_path)
            
            # 验证脚本
            if not self._validate_locust_script(file_path):
                os.remove(file_path)
                raise ValueError("无效的Locust脚本文件")
            
            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)
            
            # 保存到数据库
            script_data = {
                'filename': unique_filename,
                'original_name': filename,
                'file_path': file_path,
                'file_size': file_size,
                'file_hash': file_hash,
                'uploaded_by': user_id,
                'description': description or '',
                'upload_time': datetime.now()
            }
            
            script_id = db_manager.create_script_file(script_data)
            if script_id:
                script_data['id'] = script_id
                self.logger.info(f"脚本上传成功: {filename} -> {unique_filename}")
                return script_data
            else:
                # 数据库保存失败，删除文件
                os.remove(file_path)
                raise ValueError("保存脚本信息到数据库失败")
                
        except Exception as e:
            self.logger.error(f"上传脚本失败: {e}")
            raise e
    
    def delete_script(self, script_id: int, user_id: int = None) -> bool:
        """删除脚本文件"""
        try:
            # 获取脚本信息
            script = db_manager.get_script_file(script_id)
            if not script:
                return False
            
            # 检查权限（如果指定了用户ID）
            if user_id and script['uploaded_by'] != user_id:
                raise PermissionError("没有权限删除此脚本")
            
            # 删除物理文件
            if os.path.exists(script['file_path']):
                os.remove(script['file_path'])
            
            # 从数据库删除
            success = db_manager.delete_script_file(script_id)
            
            if success:
                self.logger.info(f"删除脚本: {script['filename']}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除脚本失败: {e}")
            return False
    
    def get_script(self, script_id: int) -> Optional[Dict]:
        """获取脚本信息"""
        return db_manager.get_script_file(script_id)
    
    def get_script_by_filename(self, filename: str) -> Optional[Dict]:
        """通过文件名获取脚本信息"""
        return db_manager.get_script_file_by_filename(filename)
    
    def get_all_scripts(self, user_id: int = None) -> List[Dict]:
        """获取所有脚本列表"""
        scripts = db_manager.get_all_script_files(user_id)
        
        # 检查文件是否存在
        for script in scripts:
            script['file_exists'] = os.path.exists(script['file_path'])
        
        return scripts
    
    def get_script_content(self, script_id: int) -> Optional[str]:
        """获取脚本内容"""
        try:
            script = self.get_script(script_id)
            if not script or not os.path.exists(script['file_path']):
                return None

            with open(script['file_path'], 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            self.logger.error(f"读取脚本内容失败: {e}")
            return None
    
    def get_script_content_by_filename(self, filename: str) -> Optional[str]:
        """通过文件名获取脚本内容"""
        try:
            script = self.get_script_by_filename(filename)
            if not script or not os.path.exists(script['file_path']):
                return None

            with open(script['file_path'], 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            self.logger.error(f"读取脚本内容失败: {e}")
            return None
    
    def update_script_content(self, script_id: int, content: str, user_id: int = None) -> bool:
        """更新脚本内容"""
        try:
            script = self.get_script(script_id)
            if not script:
                return False
            
            # 检查权限
            if user_id and script['uploaded_by'] != user_id:
                raise PermissionError("没有权限修改此脚本")
            
            # 备份原文件
            backup_path = script['file_path'] + '.backup'
            shutil.copy2(script['file_path'], backup_path)
            
            try:
                # 写入新内容
                with open(script['file_path'], 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 验证脚本
                if not self._validate_locust_script(script['file_path']):
                    # 恢复备份
                    shutil.move(backup_path, script['file_path'])
                    raise ValueError("无效的Locust脚本内容")
                
                # 更新数据库中的文件信息
                file_hash = self._calculate_file_hash(script['file_path'])
                file_size = os.path.getsize(script['file_path'])
                
                db_manager.update_script_file(script_id, {
                    'file_size': file_size,
                    'file_hash': file_hash,
                    'updated_at': datetime.now()
                })
                
                # 删除备份文件
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                
                self.logger.info(f"更新脚本内容: {script['filename']}")
                return True
                
            except Exception as e:
                # 恢复备份
                if os.path.exists(backup_path):
                    shutil.move(backup_path, script['file_path'])
                raise e
                
        except Exception as e:
            self.logger.error(f"更新脚本内容失败: {e}")
            return False
    
    def cleanup_orphaned_files(self) -> int:
        """清理孤立的文件（数据库中不存在的文件）"""
        try:
            # 获取数据库中的所有脚本文件
            db_scripts = db_manager.get_all_script_files()
            db_files = {script['filename'] for script in db_scripts}
            
            # 获取上传目录中的所有文件
            upload_files = set()
            if os.path.exists(self.upload_folder):
                for filename in os.listdir(self.upload_folder):
                    if os.path.isfile(os.path.join(self.upload_folder, filename)):
                        upload_files.add(filename)
            
            # 找出孤立的文件
            orphaned_files = upload_files - db_files
            
            # 删除孤立的文件
            deleted_count = 0
            for filename in orphaned_files:
                file_path = os.path.join(self.upload_folder, filename)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    self.logger.info(f"删除孤立文件: {filename}")
                except Exception as e:
                    self.logger.error(f"删除孤立文件失败 {filename}: {e}")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"清理孤立文件失败: {e}")
            return 0

# 创建脚本管理器实例
script_manager = ScriptManager()