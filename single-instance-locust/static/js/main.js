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

// 启动新实例
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessages();
    showLoading(true);

    const formData = new FormData(form);
    const data = {};
    for (let [key, value] of formData.entries()) data[key] = value;

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
    if (!confirm('⚠️ 确定要关闭容器吗？\n\n这将停止所有正在运行的压测实例并关闭整个应用程序。\n此操作不可撤销！')) return;
    if (!confirm('🔴 最后确认：真的要关闭容器吗？\n\n点击确定后，容器将立即关闭！')) return;

    try {
        showLoading(true);
        showMessage('正在关闭容器...', false);
        const resp = await fetch('/api/shutdown', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const result = await resp.json();
        if (result.success) {
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
});
