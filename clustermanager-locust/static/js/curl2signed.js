// ========== 签名 cURL 转压测脚本逻辑 ==========

function openSignedCurlToScript() {
    document.getElementById('signedCurlInput').value = '';
    document.getElementById('signedCurlFilename').value = '';
    document.getElementById('signedSecretPath').value = '/api/secret/fetch';
    document.getElementById('signedCurlPreviewArea').style.display = 'none';
    document.getElementById('signedCurlPreviewContent').textContent = '';
    document.getElementById('signedCurlParseInfo').style.display = 'none';
    document.getElementById('signedCurlSaveBtn').style.display = 'none';
    document.getElementById('signedCurlModal').style.display = 'flex';
}

function closeSignedCurlToScript() {
    document.getElementById('signedCurlModal').style.display = 'none';
}

async function parseSignedCurlCommand() {
    const curlCmd = document.getElementById('signedCurlInput').value.trim();
    const filename = document.getElementById('signedCurlFilename').value.trim();
    const secretPath = document.getElementById('signedSecretPath').value.trim();

    if (!secretPath) {
        showMessage('请输入签名URI', true);
        return;
    }
    if (!curlCmd) {
        showMessage('请输入 cURL 命令', true);
        return;
    }

    try {
        showLoading(true);
        const resp = await fetch('/api/curl-to-signed-script', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                curl: curlCmd,
                filename: filename,
                secret_path: secretPath,
                save: false
            })
        });
        const result = await resp.json();

        if (result.success) {
            const info = result.parsed;
            const infoEl = document.getElementById('signedCurlParseInfo');
            infoEl.innerHTML = `
                <span class="parse-tag method-${info.method.toLowerCase()}">${info.method}</span>
                <span class="parse-tag">${info.url}</span>
                ${info.has_body ? `<span class="parse-tag body-tag">${info.data_type || 'body'}</span>` : ''}
                <span class="parse-tag">${info.headers_count} 个请求头</span>
                <span class="parse-tag" style="background:#ff6b35;color:white;">🔐 签名: ${info.secret_path}</span>
            `;
            infoEl.style.display = 'flex';

            document.getElementById('signedCurlPreviewContent').textContent = result.content;
            document.getElementById('signedCurlPreviewArea').style.display = 'block';
            document.getElementById('signedCurlSaveBtn').style.display = 'inline-block';
        } else {
            showMessage(result.message, true);
        }
    } catch (error) {
        showMessage('解析失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

async function saveSignedCurlScript() {
    const curlCmd = document.getElementById('signedCurlInput').value.trim();
    const filename = document.getElementById('signedCurlFilename').value.trim();
    const secretPath = document.getElementById('signedSecretPath').value.trim();

    if (!filename) {
        showMessage('请输入文件名后再保存', true);
        document.getElementById('signedCurlFilename').focus();
        return;
    }

    try {
        showLoading(true);
        const resp = await fetch('/api/curl-to-signed-script', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                curl: curlCmd,
                filename: filename,
                secret_path: secretPath,
                save: true
            })
        });
        const result = await resp.json();

        if (result.success && result.saved) {
            showMessage(result.message);
            closeSignedCurlToScript();
            initScriptTree();
            loadTempFiles();
        } else {
            showMessage(result.message, true);
        }
    } catch (error) {
        showMessage('保存失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}
