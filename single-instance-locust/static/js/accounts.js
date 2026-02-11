// ========== 账户管理逻辑 ==========
let currentAccounts = [];
let editingAccountIndex = -1;

function openAccountModal() {
    document.getElementById('accountModal').classList.add('show');
    loadAccounts();
}

function closeAccountModal() {
    document.getElementById('accountModal').classList.remove('show');
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-item').forEach(i => i.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(tabId).classList.add('active');
}

function showAlert(type, message) {
    const div = document.createElement('div');
    div.style.cssText = `
        position: fixed; top: 20px; right: 20px; padding: 12px 20px;
        border-radius: 4px; color: white; font-size: 14px; z-index: 10000;
        max-width: 300px; word-wrap: break-word; box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    `;
    const colors = { success: '#28a745', error: '#dc3545', warning: '#ffc107', info: '#17a2b8' };
    div.style.backgroundColor = colors[type] || colors.info;
    if (type === 'warning') div.style.color = '#212529';
    div.textContent = message;
    document.body.appendChild(div);
    setTimeout(() => { if (div.parentNode) div.parentNode.removeChild(div); }, 3000);
}

function initAccountManagement() {
    document.querySelectorAll('.tab-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab(item.getAttribute('data-tab'));
        });
    });

    const form = document.getElementById('accountForm');
    if (form) form.addEventListener('submit', handleAccountFormSubmit);

    const modal = document.getElementById('accountModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target.id === 'accountModal') closeAccountModal();
        });
    }
}

async function loadAccounts() {
    try {
        const resp = await fetch('/api/accounts');
        const data = await resp.json();
        if (data.success) {
            currentAccounts = data.accounts;
            renderAccountsTable();
            updateAccountCount();
        } else {
            showAlert('error', '加载账户失败: ' + data.message);
        }
    } catch (error) {
        showAlert('error', '加载账户失败: ' + error.message);
    }
}

function renderAccountsTable() {
    const tbody = document.getElementById('accountsTableBody');
    if (currentAccounts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><i>📭</i><p>暂无账户数据</p></td></tr>';
        return;
    }

    tbody.innerHTML = currentAccounts.map((acc, i) => `
        <tr>
            <td>${escapeHtml(acc.username)}</td>
            <td>${escapeHtml(acc.account_id)}</td>
            <td><span class="account-type-badge badge-${acc.account_type}">${getAccountTypeLabel(acc.account_type)}</span></td>
            <td>${acc.m_account_id ? escapeHtml(acc.m_account_id) : '-'}</td>
            <td>${acc.m_account_type ? `<span class="account-type-badge badge-${acc.m_account_type}">${getAccountTypeLabel(acc.m_account_type)}</span>` : '-'}</td>
            <td>${acc.token ? '***' + acc.token.slice(-4) : '无'}</td>
            <td class="account-actions">
                <button class="btn-icon btn-edit" onclick="editAccount(${i})" title="编辑">✏️</button>
                <button class="btn-icon btn-delete" onclick="deleteAccount(${i})" title="删除">🗑️</button>
            </td>
        </tr>
    `).join('');
}

function getAccountTypeLabel(type) {
    return { 'M': 'M', 'U': 'U', 'MG': 'MG' }[type] || type;
}

function updateAccountCount() {
    document.getElementById('accountCount').textContent = `共 ${currentAccounts.length} 个账户`;
}

function editAccount(index) {
    editingAccountIndex = index;
    const acc = currentAccounts[index];
    document.getElementById('username').value = acc.username;
    document.getElementById('password').value = acc.password;
    document.getElementById('account_id').value = acc.account_id;
    document.getElementById('account_type').value = acc.account_type;
    document.getElementById('m_account_id').value = acc.m_account_id || '';
    document.getElementById('m_account_type').value = acc.m_account_type || '';
    document.getElementById('token').value = acc.token || '';
    switchTab('add-account');
    document.querySelector('#accountForm button[type="submit"]').textContent = '更新账户';
}

async function deleteAccount(index) {
    if (!confirm(`确定要删除账户 "${currentAccounts[index].username}" 吗？`)) return;
    try {
        const resp = await fetch(`/api/accounts/${index}`, { method: 'DELETE' });
        const data = await resp.json();
        if (data.success) { showAlert('success', data.message); loadAccounts(); }
        else showAlert('error', '删除失败: ' + data.message);
    } catch (error) {
        showAlert('error', '删除失败: ' + error.message);
    }
}

async function handleAccountFormSubmit(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const accountData = {
        username: fd.get('username'), password: fd.get('password'),
        account_id: fd.get('account_id'), account_type: fd.get('account_type'),
        m_account_id: fd.get('m_account_id') || '', m_account_type: fd.get('m_account_type') || '',
        token: fd.get('token') || generateToken()
    };

    if (!accountData.username || !accountData.password || !accountData.account_id || !accountData.account_type) {
        showAlert('error', '请填写所有必需字段');
        return;
    }

    try {
        let accounts = [...currentAccounts];
        if (editingAccountIndex >= 0) accounts[editingAccountIndex] = accountData;
        else accounts.push(accountData);

        const resp = await fetch('/api/accounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ accounts })
        });
        const data = await resp.json();
        if (data.success) {
            showAlert('success', data.message);
            resetAccountForm();
            loadAccounts();
            switchTab('accounts-list');
        } else {
            showAlert('error', '保存失败: ' + data.message);
        }
    } catch (error) {
        showAlert('error', '保存失败: ' + error.message);
    }
}

function resetAccountForm() {
    document.getElementById('accountForm').reset();
    editingAccountIndex = -1;
    document.querySelector('#accountForm button[type="submit"]').textContent = '保存账户';
}

function generateToken() { return 'token_' + Math.random().toString(36).substr(2, 16); }

async function exportAccounts() {
    if (currentAccounts.length === 0) { showAlert('error', '没有账户数据可导出'); return; }
    const headers = ['username', 'password', 'account_id', 'account_type', 'token', 'm_account_id', 'm_account_type'];
    const rows = [headers.join(',')];
    currentAccounts.forEach(acc => {
        rows.push(headers.map(h => `"${(acc[h] || '').toString().replace(/"/g, '""')}"`).join(','));
    });
    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `accounts_${new Date().toISOString().split('T')[0]}.csv`;
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showAlert('success', '账户数据已导出为CSV文件');
}

function importAccounts() {
    const file = document.getElementById('csvFile').files[0];
    if (!file) { showAlert('error', '请选择CSV文件'); return; }

    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const accounts = parseCSV(e.target.result);
            if (accounts.length === 0) { showAlert('error', 'CSV文件中没有有效的账户数据'); return; }
            if (!confirm(`将导入 ${accounts.length} 个账户，这将覆盖现有数据。确定继续吗？`)) return;

            const resp = await fetch('/api/accounts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ accounts })
            });
            const data = await resp.json();
            if (data.success) {
                showAlert('success', `成功导入 ${accounts.length} 个账户`);
                loadAccounts();
                switchTab('accounts-list');
                document.getElementById('csvFile').value = '';
            } else {
                showAlert('error', '导入失败: ' + data.message);
            }
        } catch (error) {
            showAlert('error', '导入失败: ' + error.message);
        }
    };
    reader.readAsText(file);
}

function parseCSV(csv) {
    const lines = csv.split('\n').filter(l => l.trim());
    if (lines.length < 2) return [];
    const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
    const accounts = [];
    for (let i = 1; i < lines.length; i++) {
        const values = parseCSVLine(lines[i]);
        if (values.length >= 4) {
            const acc = {};
            headers.forEach((h, idx) => { acc[h] = values[idx] || ''; });
            if (acc.username && acc.password && acc.account_id && acc.account_type) accounts.push(acc);
        }
    }
    return accounts;
}

function parseCSVLine(line) {
    const result = [];
    let current = '', inQuotes = false;
    for (let i = 0; i < line.length; i++) {
        const c = line[i];
        if (c === '"') {
            if (inQuotes && line[i + 1] === '"') { current += '"'; i++; }
            else inQuotes = !inQuotes;
        } else if (c === ',' && !inQuotes) { result.push(current.trim()); current = ''; }
        else current += c;
    }
    result.push(current.trim());
    return result;
}

async function validateAllAccounts() {
    let validCount = 0, invalid = [];
    for (const acc of currentAccounts) {
        try {
            const resp = await fetch('/api/accounts/validate', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(acc)
            });
            const data = await resp.json();
            if (data.success && data.valid) validCount++;
            else invalid.push(acc.username);
        } catch { invalid.push(acc.username); }
    }
    if (invalid.length === 0) showAlert('success', `所有 ${validCount} 个账户配置都有效`);
    else showAlert('error', `发现 ${invalid.length} 个无效账户: ${invalid.join(', ')}`);
}

async function clearAllAccounts() {
    if (!confirm('确定要清空所有账户配置吗？此操作不可恢复！')) return;
    try {
        const resp = await fetch('/api/accounts', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ accounts: [] })
        });
        const data = await resp.json();
        if (data.success) { showAlert('success', '已清空所有账户配置'); loadAccounts(); }
        else showAlert('error', '清空失败: ' + data.message);
    } catch (error) {
        showAlert('error', '清空失败: ' + error.message);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 初始化
document.addEventListener('DOMContentLoaded', initAccountManagement);
if (document.readyState !== 'loading') initAccountManagement();
