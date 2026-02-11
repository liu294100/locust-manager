// ========== 登录页面逻辑 ==========
const form = document.getElementById('loginForm');
const loginBtn = document.getElementById('loginBtn');
const alertSuccess = document.getElementById('alertSuccess');
const alertError = document.getElementById('alertError');
const loading = document.getElementById('loading');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');

function showMessage(message, isError = false) {
    hideMessages();
    const el = isError ? alertError : alertSuccess;
    el.textContent = message;
    el.style.display = 'block';
    if (!isError) setTimeout(hideMessages, 3000);
}

function hideMessages() {
    alertSuccess.style.display = 'none';
    alertError.style.display = 'none';
}

function setLoading(isLoading) {
    loading.style.display = isLoading ? 'block' : 'none';
    loginBtn.disabled = isLoading;
    form.style.display = isLoading ? 'none' : 'block';
}

form.addEventListener('submit', async function(e) {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    if (!username || !password) {
        showMessage('请输入用户名和密码', true);
        return;
    }

    setLoading(true);
    hideMessages();

    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch('/login', { method: 'POST', body: formData });
        const result = await response.json();

        if (result.success) {
            showMessage('登录成功，正在跳转...');
            setTimeout(() => { window.location.href = result.redirect || '/'; }, 1000);
        } else {
            showMessage(result.message || '登录失败', true);
        }
    } catch (error) {
        showMessage('网络错误，请重试', true);
        console.error('登录错误:', error);
    } finally {
        setLoading(false);
    }
});

document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !loginBtn.disabled) {
        form.dispatchEvent(new Event('submit'));
    }
});

window.addEventListener('load', function() {
    usernameInput.focus();
});
