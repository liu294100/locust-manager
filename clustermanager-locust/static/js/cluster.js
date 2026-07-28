/**
 * 集群管理 JavaScript
 */

// 集群状态
let clusterEnabled = false;
let clusterNodes = [];
let clusterInstances = [];

/**
 * 初始化集群功能
 */
async function initCluster() {
    try {
        const response = await fetch('/api/cluster/status');
        const data = await response.json();
        
        clusterEnabled = data.cluster_enabled;
        
        if (clusterEnabled) {
            console.log('集群模式已启用');
            showClusterUI();
            await refreshClusterStatus();
        } else {
            console.log('集群模式未启用');
            hideClusterUI();
        }
    } catch (error) {
        console.error('初始化集群失败:', error);
        clusterEnabled = false;
        hideClusterUI();
    }
}

/**
 * 显示集群 UI
 */
function showClusterUI() {
    const clusterSection = document.getElementById('cluster-section');
    if (clusterSection) {
        clusterSection.style.display = 'block';
    }
    
    // 添加集群模式切换按钮
    const modeToggle = document.getElementById('cluster-mode-toggle');
    if (modeToggle) {
        modeToggle.style.display = 'inline-block';
    }
}

/**
 * 隐藏集群 UI
 */
function hideClusterUI() {
    const clusterSection = document.getElementById('cluster-section');
    if (clusterSection) {
        clusterSection.style.display = 'none';
    }
}

/**
 * 刷新集群状态
 */
async function refreshClusterStatus() {
    if (!clusterEnabled) return;
    
    try {
        // 获取集群状态
        const statusResp = await fetch('/api/cluster/status');
        const statusData = await statusResp.json();
        
        if (statusData.success) {
            updateClusterStats(statusData.stats);
            updateCurrentNode(statusData.current_node);
        }
        
        // 获取节点列表
        const nodesResp = await fetch('/api/cluster/nodes');
        const nodesData = await nodesResp.json();
        
        if (nodesData.success) {
            clusterNodes = nodesData.nodes;
            updateNodesTable(clusterNodes);
        }
        
        // 获取集群实例
        const instancesResp = await fetch('/api/cluster/instances');
        const instancesData = await instancesResp.json();
        
        if (instancesData.success) {
            clusterInstances = instancesData.instances;
            updateClusterInstancesTable(clusterInstances);
        }
        
    } catch (error) {
        console.error('刷新集群状态失败:', error);
    }
}

/**
 * 更新集群统计信息
 */
function updateClusterStats(stats) {
    const statsContainer = document.getElementById('cluster-stats');
    if (!statsContainer) return;
    
    statsContainer.innerHTML = `
        <div class="stat-item">
            <span class="stat-label">在线节点</span>
            <span class="stat-value">${stats.online_nodes} / ${stats.total_nodes}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">总容量</span>
            <span class="stat-value">${stats.total_capacity}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">运行中实例</span>
            <span class="stat-value">${stats.running_instances}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">集群实例</span>
            <span class="stat-value">${stats.cluster_instances}</span>
        </div>
    `;
}

/**
 * 更新当前节点信息
 */
function updateCurrentNode(node) {
    const nodeInfo = document.getElementById('current-node-info');
    if (!nodeInfo || !node) return;
    
    const leaderBadge = node.is_leader 
        ? '<span class="badge badge-warning">👑 Leader</span>' 
        : '';
    
    nodeInfo.innerHTML = `
        <strong>当前节点:</strong> ${node.node_id}
        <span class="node-role ${node.role}">${node.role}</span>
        <span class="node-status ${node.status}">${node.status}</span>
        ${leaderBadge}
    `;
}

/**
 * 更新节点列表表格
 */
function updateNodesTable(nodes) {
    const tbody = document.getElementById('cluster-nodes-tbody');
    if (!tbody) return;
    
    if (nodes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">暂无节点</td></tr>';
        return;
    }
    
    tbody.innerHTML = nodes.map(node => `
        <tr class="${node.status === 'online' ? '' : 'offline'}">
            <td>
                ${node.node_id}
                ${node.is_leader ? '<span class="badge badge-warning">👑</span>' : ''}
            </td>
            <td>${node.ip_address}:${node.port}</td>
            <td><span class="badge badge-${getRoleBadge(node.role)}">${node.role}</span></td>
            <td><span class="status-dot ${node.status}"></span>${node.status}</td>
            <td>${node.running_instances} / ${node.capacity}</td>
            <td>${node.cpu_cores} 核 / ${Math.round(node.memory_mb / 1024)} GB</td>
            <td>${formatTime(node.last_heartbeat)}</td>
            <td>
                ${node.is_leader ? '' : '<button class="btn btn-sm btn-outline" onclick="forceReelection()" title="强制重新选举">🔄</button>'}
            </td>
        </tr>
    `).join('');
}

/**
 * 更新集群实例表格 - 树形展示主从关系
 */
function updateClusterInstancesTable(instances) {
    const tbody = document.getElementById('cluster-instances-tbody');
    if (!tbody) return;
    
    if (instances.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">暂无集群实例</td></tr>';
        return;
    }
    
    // 按主从关系组织实例
    const rows = [];
    
    instances.forEach(inst => {
        // Master 行
        const masterRow = createInstanceRow(inst, false);
        rows.push(masterRow);
        
        // 如果有 Workers，展示 Worker 行
        if (inst.workers && inst.workers.length > 0) {
            inst.workers.forEach((workerId, index) => {
                const workerRow = createWorkerRow(inst.instance_id, workerId, index, inst.workers.length);
                rows.push(workerRow);
            });
        }
    });
    
    tbody.innerHTML = rows.join('');
}

/**
 * 创建 Master 实例行
 */
function createInstanceRow(inst, isWorker) {
    const workerCount = inst.workers ? inst.workers.length : 0;
    const statusClass = inst.status === 'running' ? 'status-running' : 
                        inst.status === 'error' ? 'status-error' : 
                        inst.status === 'offline' ? 'status-offline' : 'status-stopped';
    const rowClass = inst.status === 'offline' ? 'instance-master instance-offline' : 'instance-master';
    
    return `
        <tr class="${rowClass}">
            <td>
                <span class="instance-icon">${inst.mode === 'master' ? '👑' : '📦'}</span>
                <strong>${inst.instance_id}</strong>
            </td>
            <td>
                <span class="node-name" title="${inst.node_id}">${shortenNodeId(inst.node_id)}</span>
            </td>
            <td title="${inst.script_file}">
                <span class="script-name">📜 ${getFileName(inst.script_file)}</span>
            </td>
            <td><span class="badge badge-${inst.mode === 'master' ? 'primary' : 'info'}">${inst.mode === 'master' ? 'Master' : 'Standalone'}</span></td>
            <td><span class="status-dot ${statusClass}"></span>${inst.status}</td>
            <td>${inst.users || '-'}</td>
            <td>
                <span class="worker-count ${workerCount > 0 ? 'has-workers' : ''}">${workerCount}</span>
            </td>
            <td class="actions">
                ${inst.status === 'running' ? `
                    <button class="btn btn-sm btn-danger" onclick="stopClusterInstance('${inst.instance_id}')" title="停止整个集群">⏹</button>
                    ${inst.web_url ? `<a href="${inst.web_url}" target="_blank" class="btn btn-sm btn-info" title="打开 Locust Web UI">🎯</a>` : ''}
                ` : `
                    <button class="btn btn-sm btn-warning" onclick="removeClusterInstance('${inst.instance_id}')" title="删除实例">🗑</button>
                `}
            </td>
        </tr>
    `;
}

/**
 * 创建 Worker 行
 */
function createWorkerRow(masterInstanceId, workerId, index, totalWorkers) {
    const isLast = index === totalWorkers - 1;
    const treeSymbol = isLast ? '└──' : '├──';
    
    return `
        <tr class="instance-worker">
            <td class="worker-indent">
                <span class="tree-line">${treeSymbol}</span>
                <span class="instance-icon">👷</span>
                <span class="worker-id">${masterInstanceId}-worker-${index}</span>
            </td>
            <td>
                <span class="node-name" title="${workerId}">${shortenNodeId(workerId)}</span>
            </td>
            <td class="worker-script">─</td>
            <td><span class="badge badge-success">Worker</span></td>
            <td><span class="status-dot status-running"></span>connected</td>
            <td>─</td>
            <td>─</td>
            <td></td>
        </tr>
    `;
}

/**
 * 缩短节点 ID 显示
 */
function shortenNodeId(nodeId) {
    if (!nodeId) return '-';
    // 格式: locust-node-77ddfdd9d9-gm2fq-4da4a94d
    // 只显示最后两部分: gm2fq-4da4a94d
    const parts = nodeId.split('-');
    if (parts.length >= 2) {
        return parts.slice(-2).join('-');
    }
    return nodeId.length > 20 ? nodeId.substring(0, 17) + '...' : nodeId;
}

/**
 * 在集群中启动实例
 */
async function startClusterInstance() {
    const scriptFile = document.getElementById('cluster-script-file').value;
    const targetHost = document.getElementById('cluster-target-host').value;
    const users = document.getElementById('cluster-users').value;
    const spawnRate = document.getElementById('cluster-spawn-rate').value;
    const runTime = document.getElementById('cluster-run-time').value;
    const workerCount = document.getElementById('cluster-worker-count').value;
    
    if (!scriptFile) {
        alert('请选择脚本文件');
        return;
    }
    
    try {
        const response = await fetch('/api/cluster/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                script_file: scriptFile,
                target_host: targetHost,
                users: users ? parseInt(users) : null,
                spawn_rate: spawnRate ? parseInt(spawnRate) : 1,
                run_time: runTime || null,
                worker_count: workerCount ? parseInt(workerCount) : 0
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`集群实例启动成功！\n实例ID: ${data.instance_id}`);
            await refreshClusterStatus();
        } else {
            alert(`启动失败: ${data.message}`);
        }
    } catch (error) {
        console.error('启动集群实例失败:', error);
        alert('启动失败: ' + error.message);
    }
}

/**
 * 停止集群实例
 */
async function stopClusterInstance(instanceId) {
    if (!confirm(`确定要停止实例 ${instanceId} 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/cluster/stop/${instanceId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('停止命令已发送');
            await refreshClusterStatus();
        } else {
            alert(`停止失败: ${data.message}`);
        }
    } catch (error) {
        console.error('停止集群实例失败:', error);
        alert('停止失败: ' + error.message);
    }
}

/**
 * 删除集群实例
 */
async function removeClusterInstance(instanceId) {
    if (!confirm(`确定要删除实例 ${instanceId} 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/cluster/remove/${instanceId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('实例已删除');
            await refreshClusterStatus();
        } else {
            alert(`删除失败: ${data.message}`);
        }
    } catch (error) {
        console.error('删除集群实例失败:', error);
        alert('删除失败: ' + error.message);
    }
}

/**
 * 同步集群状态
 */
async function syncCluster() {
    try {
        const response = await fetch('/api/cluster/sync', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('同步命令已发送');
            setTimeout(refreshClusterStatus, 2000);
        }
    } catch (error) {
        console.error('同步集群状态失败:', error);
    }
}

// 辅助函数
function getRoleBadge(role) {
    const badges = {
        'master': 'primary',
        'worker': 'success',
        'standalone': 'secondary'
    };
    return badges[role] || 'secondary';
}

function getModeBadge(mode) {
    const badges = {
        'master': 'primary',
        'worker': 'success',
        'standalone': 'info'
    };
    return badges[mode] || 'secondary';
}

function getFileName(path) {
    return path ? path.split(/[/\\]/).pop() : '';
}

function formatTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleTimeString();
}

/**
 * 强制重新选举
 */
async function forceReelection() {
    if (!confirm('确定要强制重新选举吗？这会导致当前 Leader 失去领导权。')) {
        return;
    }
    
    try {
        const response = await fetch('/api/cluster/election/force', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(data.message);
            setTimeout(refreshClusterStatus, 3000);
        } else {
            alert(`操作失败: ${data.message}`);
        }
    } catch (error) {
        console.error('强制选举失败:', error);
        alert('操作失败: ' + error.message);
    }
}

/**
 * 获取 Leader 信息
 */
async function getLeaderInfo() {
    try {
        const response = await fetch('/api/cluster/leader');
        const data = await response.json();
        
        if (data.success) {
            console.log('Leader 信息:', data);
            return data;
        }
    } catch (error) {
        console.error('获取 Leader 信息失败:', error);
    }
    return null;
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    initCluster();
    
    // 定时刷新集群状态
    setInterval(refreshClusterStatus, 10000);
});
