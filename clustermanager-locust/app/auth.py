# -*- coding: utf-8 -*-
"""
用户认证模块
包含登录验证装饰器和会话管理功能
"""

from functools import wraps
from flask import session, request, redirect, url_for, jsonify
from .database import db_manager

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'username' not in session:
            # 如果是API请求，返回JSON错误
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'success': False, 'message': '请先登录', 'redirect': '/login'}), 401
            # 否则重定向到登录页面
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def authenticate_user(username: str, password: str) -> tuple:
    """用户认证函数
    
    Returns:
        tuple: (success, message, user_info)
    """
    if not username or not password:
        return False, "用户名和密码不能为空", None
    
    user = db_manager.verify_user(username, password)
    if user:
        return True, "登录成功", user
    else:
        return False, "用户名或密码错误", None

def create_session(user_info: dict):
    """创建用户会话"""
    session.permanent = True
    session['user_id'] = user_info['id']
    session['username'] = user_info['username']
    session['role'] = user_info['role']

def clear_session():
    """清除用户会话"""
    session.clear()

def get_current_user():
    """获取当前登录用户信息"""
    if 'user_id' in session:
        return {
            'id': session['user_id'],
            'username': session['username'],
            'role': session['role']
        }
    return None

def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user['role'] != 'admin':
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'success': False, 'message': '需要管理员权限'}), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function