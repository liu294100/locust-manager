# -*- coding: utf-8 -*-
"""认证相关路由"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.auth import (login_required, authenticate_user, create_session,
                      clear_session, get_current_user)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面和处理"""
    if request.method == 'GET':
        if get_current_user():
            return redirect(url_for('main.index'))
        return render_template('login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    success, message, user_info = authenticate_user(username, password)

    if success:
        create_session(user_info)
        return jsonify({
            'success': True, 'message': message,
            'redirect': url_for('main.index')
        })
    else:
        return jsonify({'success': False, 'message': message}), 401


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """登出"""
    clear_session()
    return jsonify({
        'success': True, 'message': '已成功登出',
        'redirect': url_for('auth.login')
    })


@auth_bp.route('/api/user')
@login_required
def get_user_info():
    """获取当前用户信息"""
    user = get_current_user()
    return jsonify({'success': True, 'user': user})
