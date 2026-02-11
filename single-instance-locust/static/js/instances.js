// ========== 实例管理逻辑 ==========
let instances = {};

const instancesGrid = document.getElementById('instancesGrid');
const runningCount = document.getElementById('runningCount');
const totalCount = document.getElementById('totalCount');

// 刷新实例列表
async function refreshInstances() {
    try {
        const response = await fetch('/api/instances');
        const data = await response.json();
        const arr = data.instances || [];
        instances = {};
        arr.forEach(inst => { instances[inst.instance_id] = inst; });
        updateInstancesDisplay();
        updateStatusSummary();
    } catch (error) {
        console.error('刷新实例失败:', error);
    }
}

function updateInstancesDisplay() {
    const ids = Object.keys(instances);
    const runningIds = ids.filter(id => instances[id].is_running);

    if (runningIds.length === 0) {
        instancesGrid.innerHTML = '<div id="noInstances" style="text-align: center; color: #666; grid-column: 1 / -1;">暂无运行的实例</div>';
        return;
    }

    instancesGrid.innerHTML = '';
    runningIds.forEach(id => {
        instancesGrid.appendChild(createInstanceCard(id, instances[id]));
    });
}

function createInstanceCard(instanceId, instance) {
    const card = document.createElement('div');
    card.className = `instance-card ${instance.is_running ? 'instance-running' : 'instance-stopped'}`;
    const shortId = instanceId.substring(0, 8);
    const statusClass = instance.is_running ? 'status-running' : 'status-stopped';
    const statusText = instance.is_running ? '运行中' : '已停止';

    card.innerHTML = `
        <div class="instance-header">
            <div class="instance-id">ID: ${shortId}</div>
            <div class="instance-status ${statusClass}">${statusText}</div>
        </div>
        <div class="instance-info">
            <p><strong>端口:</strong> ${instance.port}</p>
            <p><strong>脚本:</strong> ${instance.script_file || '未知'}</p>
            <p><strong>目标:</strong> ${instance.target_host || '未设置'}</p>
            ${instance.is_running ? `<p><strong>PID:</strong> ${instance.pid}</p>` : ''}
        </div>
        <div class="instance-actions"></div>
    `;

    const actions = card.querySelector('.instance-actions');
    if (instance.is_running) {
        const link = document.createElement('a');
        link.href = `/proxy/${instanceId}/`;
        link.target = '_blank';
        link.className = 'btn btn-primary btn-sm';
        link.textContent = '🎯 打开Web UI';
        actions.appendChild(link);

        const stopBtn = document.createElement('button');
        stopBtn.className = 'btn btn-stop btn-sm';
        stopBtn.textContent = '⏹️ 停止';
        stopBtn.onclick = () => stopInstance(instanceId);
        actions.appendChild(stopBtn);
    } else {
        const removeBtn = document.createElement('button');
        removeBtn.className = 'btn btn-secondary btn-sm';
        removeBtn.textContent = '🗑️ 移除';
        removeBtn.onclick = () => removeInstance(instanceId);
        actions.appendChild(removeBtn);
    }

    return card;
}

function updateStatusSummary() {
    const ids = Object.keys(instances);
    runningCount.textContent = ids.filter(id => instances[id].is_running).length;
    totalCount.textContent = ids.length;
}

async function stopInstance(instanceId) {
    try {
        showLoading(true);
        const resp = await fetch(`/api/stop/${instanceId}`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showMessage(`实例 ${instanceId.substring(0, 8)} 已停止`);
            await refreshInstances();
        } else {
            showMessage(data.error || '停止实例失败', true);
        }
    } catch (error) {
        showMessage('停止实例失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

async function removeInstance(instanceId) {
    if (!confirm(`确定要移除实例 ${instanceId.substring(0, 8)} 吗？`)) return;
    try {
        showLoading(true);
        const resp = await fetch(`/api/remove/${instanceId}`, { method: 'DELETE' });
        const data = await resp.json();
        if (data.success) {
            showMessage(`实例 ${instanceId.substring(0, 8)} 已移除`);
            await refreshInstances();
        } else {
            showMessage(data.error || '移除实例失败', true);
        }
    } catch (error) {
        showMessage('移除实例失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

async function stopAllInstances() {
    if (!confirm('确定要停止所有运行中的实例吗？')) return;
    try {
        showLoading(true);
        const resp = await fetch('/api/stop_all', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            showMessage(data.message);
            await refreshInstances();
        } else {
            showMessage(data.error || '停止所有实例失败', true);
        }
    } catch (error) {
        showMessage('停止所有实例失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

// 定期刷新
setInterval(refreshInstances, 5000);
