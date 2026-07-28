# -*- coding: utf-8 -*-
"""集群管理 API 路由"""

from flask import Blueprint, request, jsonify
from app.auth import login_required

cluster_bp = Blueprint('cluster', __name__)


@cluster_bp.route('/api/cluster/status')
def cluster_status():
    """获取集群状态"""
    try:
        from app.cluster import redis_client, node_registry, cluster_manager
        
        if not redis_client.is_connected():
            return jsonify({
                'success': False,
                'message': 'Redis 未连接',
                'cluster_enabled': False
            })
            
        stats = cluster_manager.get_cluster_stats()
        current_node = node_registry.get_current_node()
        
        return jsonify({
            'success': True,
            'cluster_enabled': True,
            'current_node': current_node.to_dict() if current_node else None,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取集群状态失败: {str(e)}',
            'cluster_enabled': False
        }), 500


@cluster_bp.route('/api/cluster/nodes')
def list_nodes():
    """获取所有集群节点"""
    try:
        from app.cluster import redis_client, node_registry
        
        if not redis_client.is_connected():
            return jsonify({
                'success': False,
                'message': 'Redis 未连接',
                'nodes': []
            })
            
        nodes = node_registry.get_all_nodes()
        current_node_id = node_registry.get_node_id()
        
        return jsonify({
            'success': True,
            'nodes': [n.to_dict() for n in nodes],
            'current_node_id': current_node_id,
            'count': len(nodes)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取节点列表失败: {str(e)}',
            'nodes': []
        }), 500


@cluster_bp.route('/api/cluster/nodes/<node_id>')
def get_node(node_id):
    """获取指定节点信息"""
    try:
        from app.cluster import node_registry
        
        node = node_registry.get_node(node_id)
        if not node:
            return jsonify({
                'success': False,
                'message': '节点不存在'
            }), 404
            
        return jsonify({
            'success': True,
            'node': node.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取节点信息失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/instances')
def list_cluster_instances():
    """获取所有集群实例"""
    try:
        from app.cluster import cluster_manager
        
        instances = cluster_manager.get_all_cluster_instances()
        
        return jsonify({
            'success': True,
            'instances': [i.to_dict() for i in instances],
            'count': len(instances)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取实例列表失败: {str(e)}',
            'instances': []
        }), 500


@cluster_bp.route('/api/cluster/instances/<instance_id>')
def get_cluster_instance(instance_id):
    """获取指定集群实例"""
    try:
        from app.cluster import cluster_manager
        
        instance = cluster_manager.get_cluster_instance(instance_id)
        if not instance:
            return jsonify({
                'success': False,
                'message': '实例不存在'
            }), 404
            
        return jsonify({
            'success': True,
            'instance': instance.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取实例信息失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/start', methods=['POST'])
@login_required
def start_cluster_instance():
    """在集群中启动压测实例"""
    try:
        from app.cluster import cluster_manager, redis_client
        
        if not redis_client.is_connected():
            return jsonify({
                'success': False,
                'message': 'Redis 未连接，无法使用集群模式'
            }), 503
            
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '无效的请求数据'
            }), 400
            
        script_file = data.get('script_file')
        if not script_file:
            return jsonify({
                'success': False,
                'message': '请指定脚本文件'
            }), 400
            
        target_host = data.get('target_host')
        users = data.get('users')
        spawn_rate = data.get('spawn_rate', 1)
        run_time = data.get('run_time')
        worker_count = int(data.get('worker_count', 0))
        preferred_nodes = data.get('preferred_nodes', [])
        
        success, message, instance_id = cluster_manager.create_cluster_instance(
            script_file=script_file,
            target_host=target_host,
            users=int(users) if users else None,
            spawn_rate=int(spawn_rate) if spawn_rate else 1,
            run_time=run_time,
            worker_count=worker_count,
            preferred_nodes=preferred_nodes
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'instance_id': instance_id
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'启动失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/stop/<instance_id>', methods=['POST'])
@login_required
def stop_cluster_instance(instance_id):
    """停止集群实例"""
    try:
        from app.cluster import cluster_manager
        
        success, message = cluster_manager.stop_cluster_instance(instance_id)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'停止失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/remove/<instance_id>', methods=['DELETE'])
@login_required
def remove_cluster_instance(instance_id):
    """删除集群实例"""
    try:
        from app.cluster import cluster_manager
        
        success, message = cluster_manager.remove_cluster_instance(instance_id)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/sync', methods=['POST'])
@login_required
def sync_cluster():
    """同步集群状态"""
    try:
        from app.cluster import cluster_manager
        
        cluster_manager.sync_all_status()
        
        return jsonify({
            'success': True,
            'message': '同步命令已发送'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'同步失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/node/register', methods=['POST'])
def register_node():
    """手动注册当前节点（用于调试）"""
    try:
        from app.cluster import node_registry, redis_client
        
        if not redis_client.is_connected():
            return jsonify({
                'success': False,
                'message': 'Redis 未连接'
            }), 503
            
        data = request.get_json() or {}
        
        success = node_registry.register(
            port=data.get('port', 8088),
            role=data.get('role', 'standalone'),
            capacity=data.get('capacity', 10),
            labels=data.get('labels', {})
        )
        
        if success:
            node = node_registry.get_current_node()
            return jsonify({
                'success': True,
                'message': '节点注册成功',
                'node': node.to_dict() if node else None
            })
        else:
            return jsonify({
                'success': False,
                'message': '节点注册失败'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'注册失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/node/unregister', methods=['POST'])
@login_required
def unregister_node():
    """注销当前节点"""
    try:
        from app.cluster import node_registry
        
        node_registry.unregister()
        
        return jsonify({
            'success': True,
            'message': '节点已注销'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'注销失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/config')
def get_cluster_config_api():
    """获取集群配置信息"""
    try:
        from app.config import get_cluster_config, get_nacos_info, get_redis_config
        
        nacos_info = get_nacos_info()
        cluster_cfg = get_cluster_config()
        redis_cfg = get_redis_config()
        
        # 隐藏 Redis 密码
        safe_redis = redis_cfg.copy()
        if safe_redis.get('password'):
            safe_redis['password'] = '******'
        
        return jsonify({
            'success': True,
            'nacos': nacos_info,
            'cluster': cluster_cfg,
            'redis': safe_redis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取配置失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/whoami')
def whoami():
    """
    获取当前处理请求的节点信息
    用于验证代理转发是否生效
    """
    try:
        from app.config import is_cluster_enabled
        from flask import request
        import socket
        
        result = {
            'success': True,
            'hostname': socket.gethostname(),
            'cluster_enabled': is_cluster_enabled(),
            'proxied': request.headers.get('X-Proxy-By') == 'locust-worker',
            'forwarded_from': request.headers.get('X-Forwarded-From'),
        }
        
        if is_cluster_enabled():
            try:
                from app.cluster import node_registry
                current_node = node_registry.get_current_node()
                master_node = node_registry.get_master_node()
                
                if current_node:
                    result['node_id'] = current_node.node_id
                    result['node_ip'] = current_node.ip_address
                    result['node_port'] = current_node.port
                    result['is_leader'] = current_node.is_leader
                    result['role'] = current_node.role
                    
                if master_node:
                    result['master_node_id'] = master_node.node_id
                    result['master_ip'] = master_node.ip_address
                    result['master_port'] = master_node.port
            except Exception as e:
                result['node_error'] = str(e)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取节点信息失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/proxy-test')
def proxy_test():
    """
    测试代理转发 - 这个接口会被转发到主节点
    """
    import socket
    from flask import request
    
    return jsonify({
        'success': True,
        'message': '如果你看到这个响应，说明请求在此节点处理',
        'handled_by': socket.gethostname(),
        'proxied': request.headers.get('X-Proxy-By') == 'locust-worker',
        'forwarded_from': request.headers.get('X-Forwarded-From'),
    })


@cluster_bp.route('/api/cluster/test-connectivity')
def test_connectivity():
    """
    测试当前节点到 Master 节点的网络连通性
    """
    import socket
    import requests
    
    result = {
        'success': True,
        'current_node': socket.gethostname(),
        'tests': []
    }
    
    try:
        from app.config import is_cluster_enabled
        from app.cluster import node_registry
        
        if not is_cluster_enabled():
            result['message'] = '集群模式未启用'
            return jsonify(result)
        
        current_node = node_registry.get_current_node()
        master_node = node_registry.get_master_node()
        
        if not master_node:
            result['message'] = '无法获取 Master 节点信息'
            return jsonify(result)
        
        result['current_is_leader'] = node_registry.is_current_node_leader()
        result['master_node_id'] = master_node.node_id
        result['master_ip'] = master_node.ip_address
        result['master_port'] = master_node.port
        
        if node_registry.is_current_node_leader():
            result['message'] = '当前节点是 Master，无需测试连通性'
            return jsonify(result)
        
        # 测试 TCP 连接
        master_url = f"http://{master_node.ip_address}:{master_node.port}"
        
        # 测试 1: Socket 连接
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock_result = sock.connect_ex((master_node.ip_address, master_node.port))
            sock.close()
            result['tests'].append({
                'name': 'TCP Socket',
                'target': f"{master_node.ip_address}:{master_node.port}",
                'success': sock_result == 0,
                'error': None if sock_result == 0 else f'Connection failed: {sock_result}'
            })
        except Exception as e:
            result['tests'].append({
                'name': 'TCP Socket',
                'target': f"{master_node.ip_address}:{master_node.port}",
                'success': False,
                'error': str(e)
            })
        
        # 测试 2: HTTP 健康检查
        try:
            resp = requests.get(f"{master_url}/ok", timeout=5)
            result['tests'].append({
                'name': 'HTTP /ok',
                'target': f"{master_url}/ok",
                'success': resp.status_code == 200,
                'status_code': resp.status_code,
                'response': resp.text[:100]
            })
        except Exception as e:
            result['tests'].append({
                'name': 'HTTP /ok',
                'target': f"{master_url}/ok",
                'success': False,
                'error': str(e)
            })
        
        # 测试 3: HTTP whoami
        try:
            resp = requests.get(f"{master_url}/api/cluster/whoami", timeout=5)
            result['tests'].append({
                'name': 'HTTP /api/cluster/whoami',
                'target': f"{master_url}/api/cluster/whoami",
                'success': resp.status_code == 200,
                'status_code': resp.status_code,
                'response': resp.json() if resp.status_code == 200 else resp.text[:100]
            })
        except Exception as e:
            result['tests'].append({
                'name': 'HTTP /api/cluster/whoami',
                'target': f"{master_url}/api/cluster/whoami",
                'success': False,
                'error': str(e)
            })
        
        # 总结
        all_passed = all(t['success'] for t in result['tests'])
        result['all_tests_passed'] = all_passed
        result['message'] = '所有测试通过，网络连通正常' if all_passed else '部分测试失败，网络可能有问题'
        
    except Exception as e:
        result['success'] = False
        result['message'] = f'测试失败: {str(e)}'
    
    return jsonify(result)


@cluster_bp.route('/api/cluster/config/refresh', methods=['POST'])
@login_required
def refresh_cluster_config():
    """刷新集群配置（从 Nacos 重新加载）"""
    try:
        from app.config import refresh_config, get_cluster_config, get_redis_config
        
        # 刷新 Nacos 配置
        refresh_config()
        cluster_cfg = get_cluster_config()
        redis_cfg = get_redis_config()
        
        # 隐藏 Redis 密码
        safe_redis = redis_cfg.copy()
        if safe_redis.get('password'):
            safe_redis['password'] = '******'
        
        return jsonify({
            'success': True,
            'message': '配置已刷新',
            'cluster': cluster_cfg,
            'redis': safe_redis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'刷新配置失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/leader')
def get_leader():
    """获取当前 Leader 信息"""
    try:
        from app.cluster import node_registry, leader_election
        
        leader_id = leader_election.get_current_leader()
        leader_node = node_registry.get_master_node()
        current_is_leader = node_registry.is_current_node_leader()
        current_node_id = node_registry.get_node_id()
        
        return jsonify({
            'success': True,
            'leader_id': leader_id,
            'leader_node': leader_node.to_dict() if leader_node else None,
            'current_node_id': current_node_id,
            'current_is_leader': current_is_leader
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取 Leader 信息失败: {str(e)}'
        }), 500


@cluster_bp.route('/api/cluster/election/force', methods=['POST'])
@login_required
def force_reelection():
    """强制重新选举（仅用于调试）"""
    try:
        from app.cluster import node_registry
        
        success = node_registry.force_reelection()
        
        if success:
            return jsonify({
                'success': True,
                'message': '已触发重新选举，请等待几秒后刷新'
            })
        else:
            return jsonify({
                'success': False,
                'message': '触发选举失败'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'强制选举失败: {str(e)}'
        }), 500
