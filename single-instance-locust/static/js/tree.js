// ========== 脚本树形控件逻辑 ==========
let treeData = null;

async function initScriptTree() {
    const searchInput = document.getElementById('treeSearch');
    const searchClear = document.getElementById('searchClear');

    await loadDirectoryTree();

    searchInput.addEventListener('input', function() {
        const term = this.value.trim();
        if (term) {
            searchClear.style.display = 'block';
            filterTree(term);
        } else {
            searchClear.style.display = 'none';
            renderTree(treeData);
        }
    });

    searchClear.addEventListener('click', function() {
        searchInput.value = '';
        this.style.display = 'none';
        renderTree(treeData);
    });
}

async function loadDirectoryTree() {
    const treeView = document.getElementById('scriptTree');
    try {
        const resp = await fetch('/api/directory-tree');
        const data = await resp.json();
        if (data.success && data.tree) {
            treeData = data.tree;
            renderTree(treeData);
        } else {
            treeView.innerHTML = '<div class="tree-empty">加载目录结构失败</div>';
        }
    } catch (error) {
        console.error('加载目录树失败:', error);
        treeView.innerHTML = '<div class="tree-empty">加载目录结构失败</div>';
    }
}

function renderTree(data) {
    const treeView = document.getElementById('scriptTree');
    if (!data || !Array.isArray(data) || data.length === 0) {
        treeView.innerHTML = '<div class="tree-empty">没有找到脚本文件</div>';
        return;
    }

    let html = '';
    data.forEach(item => {
        if (item.type === 'directory' && item.name !== '__pycache__') {
            html += renderDirectoryNode(item, '');
        } else if (item.type === 'file') {
            html += renderFileNode(item.name, '');
        }
    });

    treeView.innerHTML = html;
    bindTreeEvents();
}

function renderDirectoryNode(directory, parentPath) {
    // 用 path（真实目录名）构建文件系统路径，用 name（显示名）做展示
    const realPath = directory.path || (parentPath ? `${parentPath}/${directory.name}` : directory.name);
    const displayName = directory.name;
    let html = `
        <div class="tree-node">
            <div class="tree-folder" data-path="${realPath}">
                <span class="tree-folder-icon">▶</span>
                <span class="tree-folder-name">${displayName}</span>
            </div>
            <div class="tree-children">`;

    if (directory.children) {
        directory.children.forEach(child => {
            if (child.type === 'directory' && child.name !== '__pycache__') {
                html += renderDirectoryNode(child, realPath);
            } else if (child.type === 'file') {
                html += renderFileNode(child.name, realPath);
            }
        });
    }

    html += '</div></div>';
    return html;
}

function renderFileNode(file, parentPath) {
    const fullPath = parentPath ? `${parentPath}/${file}` : file;
    return `
        <div class="tree-file" data-file="${file}" data-directory="${parentPath}" data-full-path="${fullPath}">
            <div class="tree-file-content">
                <span class="tree-file-icon">🐍</span>
                <span class="tree-file-name">${file}</span>
            </div>
            <button class="btn-preview" onclick="previewScript('${fullPath}'); event.stopPropagation();" title="预览脚本内容">
                <span>👁</span>
            </button>
        </div>`;
}

function bindTreeEvents() {
    const treeView = document.getElementById('scriptTree');
    treeView.addEventListener('click', function(e) {
        if (e.target.closest('.tree-folder')) {
            const folder = e.target.closest('.tree-folder');
            const children = folder.nextElementSibling;
            if (folder.classList.contains('expanded')) {
                folder.classList.remove('expanded');
                children.style.display = 'none';
            } else {
                folder.classList.add('expanded');
                children.style.display = 'block';
            }
        }
        if (e.target.closest('.tree-file')) {
            selectScriptFile(e.target.closest('.tree-file'));
        }
    });
}

function selectScriptFile(fileNode) {
    document.querySelectorAll('.tree-file.selected').forEach(n => n.classList.remove('selected'));
    fileNode.classList.add('selected');

    const fileName = fileNode.dataset.file;
    const directory = fileNode.dataset.directory || '';
    const fullPath = fileNode.dataset.fullPath || '';

    document.getElementById('selectedPath').textContent = fullPath || fileName;
    document.getElementById('script_directory').value = directory;
    document.getElementById('script_file').value = fileName;
    document.getElementById('script_full_path').value = fullPath;
}

function filterTree(searchTerm) {
    const treeView = document.getElementById('scriptTree');
    if (!treeData) return;

    const term = searchTerm.toLowerCase();
    const filtered = filterTreeData(treeData, term);

    if (filtered.length === 0) {
        treeView.innerHTML = '<div class="tree-no-results">没有匹配的脚本文件</div>';
        return;
    }

    let html = '';
    filtered.forEach(item => {
        if (item.type === 'directory') {
            html += renderDirectoryNodeExpanded(item, '');
        } else if (item.type === 'file') {
            html += renderFileNode(item.name, '');
        }
    });

    treeView.innerHTML = html;
    bindTreeEvents();

    // 展开所有目录
    document.querySelectorAll('.tree-folder').forEach(f => {
        f.classList.add('expanded');
        const children = f.nextElementSibling;
        if (children) children.style.display = 'block';
    });
}

function filterTreeData(data, term) {
    const result = [];
    data.forEach(item => {
        if (item.type === 'file') {
            if (item.name.toLowerCase().includes(term)) result.push(item);
        } else if (item.type === 'directory') {
            const filteredChildren = filterTreeData(item.children || [], term);
            if (filteredChildren.length > 0 || item.name.toLowerCase().includes(term)) {
                result.push({ ...item, children: filteredChildren });
            }
        }
    });
    return result;
}

function renderDirectoryNodeExpanded(directory, parentPath) {
    const realPath = directory.path || (parentPath ? `${parentPath}/${directory.name}` : directory.name);
    const displayName = directory.name;
    let html = `
        <div class="tree-node">
            <div class="tree-folder expanded" data-path="${realPath}">
                <span class="tree-folder-icon">▶</span>
                <span class="tree-folder-name">${displayName}</span>
            </div>
            <div class="tree-children" style="display: block;">`;

    if (directory.children) {
        directory.children.forEach(child => {
            if (child.type === 'directory') {
                html += renderDirectoryNodeExpanded(child, realPath);
            } else if (child.type === 'file') {
                html += renderFileNode(child.name, realPath);
            }
        });
    }

    html += '</div></div>';
    return html;
}
