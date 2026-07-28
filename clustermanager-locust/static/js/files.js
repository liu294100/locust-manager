// ========== 文件管理逻辑 ==========
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');

// 文件上传
fileInput.addEventListener('change', function() {
    if (this.files.length > 0) uploadFile(this.files[0]);
});

async function uploadFile(file) {
    if (!file.name.endsWith('.py')) {
        showMessage('只允许上传.py文件', true);
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        showLoading(true);
        const resp = await fetch('/api/upload', { method: 'POST', body: formData });
        const result = await resp.json();
        if (result.success) {
            showMessage(result.message);
            loadTempFiles();
            await loadDirectoryTree();
            expandTmpFolder();
        } else {
            showMessage(result.message, true);
        }
    } catch (error) {
        showMessage('上传失败: ' + error.message, true);
    } finally {
        showLoading(false);
        fileInput.value = '';
    }
}

async function loadTempFiles() {
    try {
        const resp = await fetch('/api/scripts/临时文件');
        const data = await resp.json();
        const fileListEl = document.getElementById('fileList');
        const noFiles = document.getElementById('noFiles');

        if (data.scripts && data.scripts.length > 0) {
            if (noFiles) noFiles.style.display = 'none';
            fileListEl.innerHTML = data.scripts.map(file => `
                <div class="file-item">
                    <span class="file-name">${file}</span>
                    <div>
                        <button class="btn-preview" onclick="previewScript('tmp/${file}')">👁 预览</button>
                        <button class="delete-btn" onclick="deleteTempFile('${file}')">🗑️ 删除</button>
                    </div>
                </div>
            `).join('');
        } else {
            fileListEl.innerHTML = '<p id="noFiles" style="text-align: center; color: #666;">暂无临时文件</p>';
        }
    } catch (error) {
        console.error('加载临时文件失败:', error);
    }
}

async function deleteTempFile(filename) {
    if (!confirm(`确定要删除文件 ${filename} 吗？`)) return;
    try {
        showLoading(true);
        const resp = await fetch('/api/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const result = await resp.json();
        if (result.success) {
            showMessage(result.message);
            loadTempFiles();
            await loadDirectoryTree();
            expandTmpFolder();
        } else {
            showMessage(result.message, true);
        }
    } catch (error) {
        showMessage('删除失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

// 拖拽上传
uploadArea.addEventListener('dragover', function(e) {
    e.preventDefault();
    this.classList.add('dragover');
});
uploadArea.addEventListener('dragleave', function() {
    this.classList.remove('dragover');
});
uploadArea.addEventListener('drop', function(e) {
    e.preventDefault();
    this.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) uploadFile(e.dataTransfer.files[0]);
});

// 脚本预览
async function previewScript(scriptPath) {
    try {
        showLoading(true);
        const resp = await fetch(`/api/preview/${encodeURIComponent(scriptPath)}`);
        const result = await resp.json();
        if (result.success) {
            document.getElementById('previewScriptPath').textContent = scriptPath;
            document.getElementById('scriptContent').textContent = result.content;
            document.getElementById('scriptPreviewModal').style.display = 'flex';
        } else {
            showMessage(result.message, true);
        }
    } catch (error) {
        showMessage('预览脚本失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

function closeScriptPreview() {
    document.getElementById('scriptPreviewModal').style.display = 'none';
}

// 创建临时脚本
function openCreateTempScript() {
    document.getElementById('tempScriptFilename').value = '';
    document.getElementById('tempScriptContent').value = '';
    document.getElementById('createTempScriptModal').style.display = 'flex';
}

function closeCreateTempScript() {
    document.getElementById('createTempScriptModal').style.display = 'none';
}

async function saveTempScript() {
    const filename = document.getElementById('tempScriptFilename').value.trim();
    const content = document.getElementById('tempScriptContent').value;

    if (!filename) { showMessage('请输入文件名', true); return; }
    if (!content.trim()) { showMessage('请输入脚本内容', true); return; }
    if (!/^[a-zA-Z0-9_-]+$/.test(filename)) {
        showMessage('文件名只能包含字母、数字、下划线和连字符', true);
        return;
    }

    try {
        showLoading(true);
        const resp = await fetch('/api/create-temp-script', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename, content })
        });
        const result = await resp.json();
        if (result.success) {
            showMessage(result.message);
            closeCreateTempScript();
            await loadDirectoryTree();
            expandTmpFolder();
            loadTempFiles();
        } else {
            showMessage(result.message, true);
        }
    } catch (error) {
        showMessage('保存脚本失败: ' + error.message, true);
    } finally {
        showLoading(false);
    }
}

// 自动展开临时文件目录
function expandTmpFolder() {
    setTimeout(() => {
        document.querySelectorAll('.tree-folder').forEach(folder => {
            const name = folder.querySelector('.tree-folder-name');
            if (name && name.textContent.trim() === '临时文件') {
                if (!folder.classList.contains('expanded')) {
                    folder.classList.add('expanded');
                    const children = folder.nextElementSibling;
                    if (children) children.style.display = 'block';
                }
            }
        });
    }, 100);
}
