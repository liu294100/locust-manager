# -*- coding: utf-8 -*-
"""账户管理API路由"""

import os
import sys
import time
import threading
from flask import Blueprint, request, jsonify
from app.auth import login_required
from app.services.instance_manager import stop_all_instances

account_bp = Blueprint('account', __name__)


@account_bp.route('/api/accounts', methods=['GET'])
@login_required
def get_accounts_api():
    """获取所有账户配置"""
    try:
        sys.path.append(os.path.join(os.getcwd(), 'scripts'))
        from common.accounts_config import load_accounts_from_csv
        accounts = load_accounts_from_csv()
        return jsonify({'success': True, 'accounts': accounts})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取账户失败: {str(e)}'}), 500


@account_bp.route('/api/accounts', methods=['POST'])
@login_required
def save_accounts_api():
    """保存账户配置"""
    try:
        data = request.get_json()
        if not data or 'accounts' not in data:
            return jsonify({'success': False, 'message': '请求数据格式错误'}), 400

        accounts = data['accounts']
        required_fields = ['username', 'password', 'account_id', 'account_type']
        optional_fields = ['token', 'm_account_id', 'm_account_type']

        for i, account in enumerate(accounts):
            for field in required_fields:
                if field not in account or not account[field]:
                    return jsonify({
                        'success': False,
                        'message': f'第{i+1}个账户缺少必需字段: {field}'
                    }), 400
            for field in optional_fields:
                if field not in account:
                    account[field] = ''

        sys.path.append(os.path.join(os.getcwd(), 'scripts'))
        from common.accounts_config import save_accounts_to_csv
        success = save_accounts_to_csv(accounts)

        if success:
            return jsonify({'success': True, 'message': f'成功保存 {len(accounts)} 个账户配置'})
        else:
            return jsonify({'success': False, 'message': '保存账户配置失败'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500


@account_bp.route('/api/accounts/<int:index>', methods=['DELETE'])
@login_required
def delete_account_api(index):
    """删除指定索引的账户"""
    try:
        sys.path.append(os.path.join(os.getcwd(), 'scripts'))
        from common.accounts_config import load_accounts_from_csv, save_accounts_to_csv

        accounts = load_accounts_from_csv()
        if index < 0 or index >= len(accounts):
            return jsonify({'success': False, 'message': '账户索引无效'}), 400

        deleted = accounts.pop(index)
        success = save_accounts_to_csv(accounts)

        if success:
            return jsonify({'success': True, 'message': f'成功删除账户: {deleted.get("username", "未知")}'})
        else:
            return jsonify({'success': False, 'message': '删除账户失败'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


@account_bp.route('/api/accounts/validate', methods=['POST'])
@login_required
def validate_account_api():
    """验证账户配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400

        sys.path.append(os.path.join(os.getcwd(), 'scripts'))
        from common.accounts_config import validate_account
        is_valid = validate_account(data)

        return jsonify({
            'success': True, 'valid': is_valid,
            'message': '账户配置有效' if is_valid else '账户配置无效'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'验证失败: {str(e)}'}), 500


@account_bp.route('/api/shutdown', methods=['POST'])
@login_required
def shutdown_container():
    """关闭容器接口"""
    try:
        results = stop_all_instances()

        def delayed_shutdown():
            time.sleep(2)
            print("\n🔴 收到关闭容器请求，正在关闭应用程序...")
            os._exit(0)

        shutdown_thread = threading.Thread(target=delayed_shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()

        return jsonify({
            'success': True,
            'message': f'容器正在关闭，已停止 {len(results)} 个Locust实例'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'关闭容器失败: {str(e)}'}), 500
