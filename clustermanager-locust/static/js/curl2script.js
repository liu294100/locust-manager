// ========== cURL 转压测脚本逻辑 ==========

function openCurlToScript() {
    document.getElementById('curlInput').value = '';
    document.getElementById('curlFilename').value = '';
    document.getElementById('curlPreviewArea').style.display = 'none';
    document.getElementById('curlPreviewContent').textContent = '';
    document.getElementById('curlParseInfo').style.display = 'none';
    document.getElementById('curlSaveBtn').style.display = 'none';
    document.getElementById('curlToScriptModal').style.display = 'flex';
}

function closeCurlToScript() {
    document.getElementById('curlToScriptModal').style.display = 'none';
}

async function parseCurlCommand() {
    const curlCmd = document.getElementById('curlInput').value.trim();
    const filename = document.getElementById('curlFilename').value.trim();

    if (!curlCmd) {
        showMessage('请输入 cURL 命令', true);
        return;
    }

    try {
        showLoading(true);
        const resp = await fetch('/api/curl-to-script', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ curl: curlCmd, filename: filename, save: false })
        });
        const result = await resp.json();

        if (result.success) {
            // 显示解析信息
            const info = result.parsed;
            const infoEl = document.getElementById('curlParseInfo');
            infoEl.innerHTML = `
                <span class="parse-tag method-${info.method.toLowerCase()}">${info.method}</span>
                <span class="parse-tag">${info.url}</span>
                ${info.has_body ? `<span class="parse-tag body-tag">${info.data_type || 'body'}</span>` : ''}
                <span class="parse-tag">${info.headers_count} 个请求头</span>
            `;
            infoEl.style.display = 'flex';

            // 显示预览
            document.getElementById('curlPreviewContent').textContent = result.content;
            document.getElementById('curlPreviewArea').style.display = 'block';
            document.getElementById('curlSaveBtn').style.display = 'inline-block';
        } else {
            showMessage(result.message, true);
        }
    } catch (error) {
        showMessage('解析失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

async function saveCurlScript() {
    const curlCmd = document.getElementById('curlInput').value.trim();
    let filename = document.getElementById('curlFilename').value.trim();

    if (!filename) {
        showMessage('请输入文件名后再保存', true);
        document.getElementById('curlFilename').focus();
        return;
    }

    try {
        showLoading(true);
        const resp = await fetch('/api/curl-to-script', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ curl: curlCmd, filename: filename, save: true })
        });
        const result = await resp.json();

        if (result.success && result.saved) {
            showMessage(result.message);
            closeCurlToScript();
            // 刷新脚本树和临时文件列表
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
