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
    """
    关闭容器接口
    先关闭集群中的其他所有节点，最后关闭自己
    """
    try:
        import requests
        from app.config import is_cluster_enabled
        
        shutdown_other_nodes_results = []
        
        # 检查是否启用集群模式
        if is_cluster_enabled():
            try:
                from app.cluster import node_registry
                
                # 获取所有节点，排除自己
                all_nodes = node_registry.get_all_nodes()
                current_node_id = node_registry.get_node_id()
                other_nodes = [n for n in all_nodes if n.node_id != current_node_id and n.status == 'online']
                
                if other_nodes:
                    print(f"🔴 开始关闭集群，先关闭其他 {len(other_nodes)} 个节点")
                    
                    for node in other_nodes:
                        node_url = f"http://{node.ip_address}:{node.port}/api/shutdown/self"
                        role_label = "Master" if node.is_leader else "Worker"
                        try:
                            print(f"   📤 正在关闭 {role_label} 节点: {node.node_id} ({node.ip_address}:{node.port})")
                            resp = requests.post(node_url, timeout=10)
                            if resp.status_code == 200:
                                shutdown_other_nodes_results.append({
                                    'node_id': node.node_id,
                                    'role': role_label,
                                    'success': True,
                                    'message': '关闭命令已发送'
                                })
                                print(f"   ✅ {role_label} 节点 {node.node_id} 关闭命令已发送")
                            else:
                                shutdown_other_nodes_results.append({
                                    'node_id': node.node_id,
                                    'role': role_label,
                                    'success': False,
                                    'message': f'HTTP {resp.status_code}'
                                })
                                print(f"   ⚠️ {role_label} 节点 {node.node_id} 关闭失败: HTTP {resp.status_code}")
                        except requests.exceptions.RequestException as e:
                            shutdown_other_nodes_results.append({
                                'node_id': node.node_id,
                                'role': role_label,
                                'success': False,
                                'message': str(e)
                            })
                            print(f"   ❌ {role_label} 节点 {node.node_id} 关闭失败: {e}")
                    
                    # 等待其他节点关闭
                    print("   ⏳ 等待其他节点关闭...")
                    time.sleep(3)
                        
            except Exception as cluster_err:
                print(f"⚠️ 集群关闭处理出错: {cluster_err}，继续关闭本节点")
        
        # 停止本节点的所有实例
        results = stop_all_instances()

        def delayed_shutdown():
            time.sleep(2)
            print("\n🔴 收到关闭容器请求，正在关闭应用程序...")
            os._exit(0)

        shutdown_thread = threading.Thread(target=delayed_shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()

        message = f'容器正在关闭，已停止 {len(results)} 个Locust实例'
        if shutdown_other_nodes_results:
            success_count = sum(1 for r in shutdown_other_nodes_results if r['success'])
            message += f'，已向 {success_count}/{len(shutdown_other_nodes_results)} 个其他节点发送关闭命令'

        return jsonify({
            'success': True,
            'message': message,
            'other_nodes_shutdown_results': shutdown_other_nodes_results
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'关闭容器失败: {str(e)}'}), 500


@account_bp.route('/api/shutdown/self', methods=['POST'])
def shutdown_self():
    """
    关闭自身节点接口（供 Master 节点调用）
    不需要登录验证，因为这是内部节点间通信
    """
    try:
        # 验证请求来源（可选：可以添加更严格的验证）
        print("📥 收到来自 Master 的关闭命令")
        
        # 停止本节点的所有实例
        results = stop_all_instances()

        def delayed_shutdown():
            time.sleep(2)
            print("\n🔴 Worker 节点收到关闭命令，正在关闭应用程序...")
            os._exit(0)

        shutdown_thread = threading.Thread(target=delayed_shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()

        return jsonify({
            'success': True,
            'message': f'Worker 节点正在关闭，已停止 {len(results)} 个Locust实例'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'关闭失败: {str(e)}'}), 500
