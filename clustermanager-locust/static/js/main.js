// ========== 主页面公共逻辑 ==========
const form = document.getElementById('locustForm');
const startBtn = document.getElementById('startBtn');
const alertSuccess = document.getElementById('alertSuccess');
const alertError = document.getElementById('alertError');
const loading = document.getElementById('loading');

function showMessage(message, isError = false) {
    hideMessages();
    const el = isError ? alertError : alertSuccess;
    el.textContent = message;
    el.style.display = 'block';
    setTimeout(hideMessages, 3000);
}

function hideMessages() {
    alertSuccess.style.display = 'none';
    alertError.style.display = 'none';
}

function showLoading(show = true) {
    loading.style.display = show ? 'block' : 'none';
    startBtn.disabled = show;
}

// 压测模式切换
function toggleLoadMode() {
    const mode = document.querySelector('input[name="load_mode"]:checked').value;
    document.getElementById('fixedMode').style.display = mode === 'fixed' ? 'block' : 'none';
    document.getElementById('stepMode').style.display = mode === 'step' ? 'block' : 'none';
    document.getElementById('fixedRunTime').style.display = (mode === 'fixed') ? 'block' : 'none';
    
    // 集群模式
    const clusterModeDiv = document.getElementById('clusterMode');
    if (clusterModeDiv) {
        clusterModeDiv.style.display = mode === 'cluster' ? 'block' : 'none';
    }
}

// 启动新实例
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessages();
    showLoading(true);

    const formData = new FormData(form);
    const data = {};
    for (let [key, value] of formData.entries()) data[key] = value;

    // 获取压测模式
    const mode = document.querySelector('input[name="load_mode"]:checked').value;
    data.load_mode = mode;
    
    // 递增模式：把参数打包
    if (mode === 'step') {
        data.step_interval_seconds = parseInt(data.step_interval || '60');
        data.step_spawn_rate = parseInt(data.step_increment || '50');
    }
    
    // 集群模式：使用不同的API
    if (mode === 'cluster') {
        await startClusterInstance(data);
        return;
    }

    try {
        const resp = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await resp.json();

        if (result.success) {
            showMessage(`新实例已启动！实例ID: ${result.instance_id.substring(0, 8)}, 端口: ${result.port}`);
            location.reload();
        } else {
            showMessage(result.message || '启动实例失败', true);
        }
    } catch (error) {
        showMessage('启动实例失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
});

// 启动集群模式实例
async function startClusterInstance(formData) {
    const scriptFullPath = document.getElementById('script_full_path').value;
    if (!scriptFullPath) {
        showMessage('请选择脚本文件', true);
        showLoading(false);
        return;
    }
    
    const data = {
        script_file: scriptFullPath,
        target_host: formData.target_host || null,
        users: parseInt(document.getElementById('cluster_users').value) || null,
        spawn_rate: parseInt(document.getElementById('cluster_spawn_rate').value) || null,
        worker_count: parseInt(document.getElementById('cluster_workers').value) || 0,
        run_time: document.getElementById('run_time_cluster').value.trim() || null
    };
    
    try {
        const resp = await fetch('/api/cluster/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await resp.json();

        if (result.success) {
            showMessage(`集群压测启动成功！${result.message}\n实例ID: ${result.instance_id}`);
            setTimeout(() => location.reload(), 2000);
        } else {
            showMessage(result.message || '启动集群实例失败', true);
        }
    } catch (error) {
        showMessage('启动集群实例失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

// 退出登录
async function logout() {
    if (!confirm('确定要退出登录吗？')) return;
    try {
        showLoading(true);
        const resp = await fetch('/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const result = await resp.json();
        if (result.success) {
            showMessage('已成功退出登录');
            setTimeout(() => { window.location.href = result.redirect; }, 1000);
        } else {
            showMessage('退出失败: ' + result.message, true);
        }
    } catch (error) {
        showMessage('退出失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

// 关闭容器
async function shutdownContainer() {
    if (!confirm('⚠️ 确定要关闭容器吗？\n\n这将停止所有正在运行的压测实例并关闭整个应用程序。\n在集群模式下，会先关闭其他所有节点，最后关闭自己。\n此操作不可撤销！')) return;
    if (!confirm('🔴 最后确认：真的要关闭容器吗？\n\n点击确定后，容器将立即关闭！')) return;

    try {
        showLoading(true);
        showMessage('正在关闭容器...（集群模式下会先关闭其他节点）', false);
        const resp = await fetch('/api/shutdown', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const result = await resp.json();
        if (result.success) {
            // 显示其他节点关闭结果
            if (result.other_nodes_shutdown_results && result.other_nodes_shutdown_results.length > 0) {
                const successCount = result.other_nodes_shutdown_results.filter(r => r.success).length;
                showMessage(`已向 ${successCount}/${result.other_nodes_shutdown_results.length} 个其他节点发送关闭命令`, false);
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
            
            let countdown = 5;
            const interval = setInterval(() => {
                showMessage(`容器将在 ${countdown} 秒后关闭...`, false);
                countdown--;
                if (countdown < 0) { clearInterval(interval); showMessage('容器已关闭', false); }
            }, 1000);
        } else {
            showMessage('关闭容器失败: ' + result.message, true);
        }
    } catch (error) {
        showMessage('关闭容器失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

// 页面初始化
window.onload = function() {
    const btnAccountManage = document.getElementById('btnAccountManage');
    const btnShutdown = document.getElementById('btnShutdown');
    if (btnAccountManage) btnAccountManage.style.display = 'none';
    if (btnShutdown) btnShutdown.style.display = 'none';
};

document.addEventListener('DOMContentLoaded', async function() {
    initScriptTree();
    loadTempFiles();
    await refreshInstances();
    await checkClusterStatus();
    await showNodeInfo();
});

// 检查集群状态并显示入口
async function checkClusterStatus() {
    try {
        const resp = await fetch('/api/cluster/status');
        const data = await resp.json();
        console.log('集群状态:', data);
        
        const clusterLink = document.getElementById('clusterLink');
        const clusterModeLabel = document.getElementById('clusterModeLabel');
        
        if (data.cluster_enabled === true) {
            // 显示集群管理入口
            if (clusterLink) {
                clusterLink.style.display = 'inline-block';
                console.log('集群入口已显示');
            }
            // 显示集群模式选项
            if (clusterModeLabel) {
                clusterModeLabel.style.display = 'inline-flex';
                console.log('集群模式选项已显示');
            }
        } else {
            console.log('集群模式未启用');
        }
    } catch (error) {
        console.log('集群状态检查失败:', error);
    }
}

// 显示当前节点信息
async function showNodeInfo() {
    try {
        const resp = await fetch('/api/cluster/whoami');
        const data = await resp.json();
        console.log('节点信息:', data);
        
        const nodeInfoEl = document.getElementById('nodeInfo');
        if (nodeInfoEl && data.success) {
            let info = `📍 节点: ${data.hostname || 'unknown'}`;
            if (data.node_id) {
                info = `📍 节点: ${data.node_id}`;
            }
            if (data.is_leader) {
                info += ' 👑 Master';
            } else if (data.role === 'worker') {
                info += ' 🔧 Worker';
            }
            if (data.proxied) {
                info += ` (转发自 ${data.forwarded_from || 'unknown'})`;
            }
            nodeInfoEl.textContent = info;
        }
    } catch (error) {
        console.log('获取节点信息失败:', error);
    }
}
