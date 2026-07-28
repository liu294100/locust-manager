// ========== 脚本树形控件逻辑 ==========
// 支持多实例：每个树控件有独立的 containerId
let treeDataCache = {};  // 缓存目录树数据

/**
 * 初始化脚本树组件
 * @param {string} containerId - 树组件容器ID，默认为 'scriptTree'
 * @param {Object} options - 配置选项
 *   - searchInputId: 搜索输入框ID
 *   - searchClearId: 清除按钮ID
 *   - selectedPathId: 选中路径显示ID
 *   - directoryInputId: 目录隐藏字段ID
 *   - fileInputId: 文件名隐藏字段ID
 *   - fullPathInputId: 完整路径隐藏字段ID
 *   - onSelect: 选中回调函数
 */
async function initScriptTree(containerId = 'scriptTree', options = {}) {
    const config = {
        searchInputId: options.searchInputId || 'treeSearch',
        searchClearId: options.searchClearId || 'searchClear',
        selectedPathId: options.selectedPathId || 'selectedPath',
        directoryInputId: options.directoryInputId || 'script_directory',
        fileInputId: options.fileInputId || 'script_file',
        fullPathInputId: options.fullPathInputId || 'script_full_path',
        onSelect: options.onSelect || null
    };

    const searchInput = document.getElementById(config.searchInputId);
    const searchClear = document.getElementById(config.searchClearId);

    await loadDirectoryTree(containerId, config);

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const term = this.value.trim();
            if (term) {
                if (searchClear) searchClear.style.display = 'block';
                filterTree(containerId, term, config);
            } else {
                if (searchClear) searchClear.style.display = 'none';
                renderTree(containerId, treeDataCache[containerId], config);
            }
        });
    }

    if (searchClear) {
        searchClear.addEventListener('click', function() {
            if (searchInput) searchInput.value = '';
            this.style.display = 'none';
            renderTree(containerId, treeDataCache[containerId], config);
        });
    }
    
    return config;
}

// 兼容旧代码：默认树数据引用
let treeData = null;

async function loadDirectoryTree(containerId = 'scriptTree', config = {}) {
    const treeView = document.getElementById(containerId);
    if (!treeView) return;
    
    try {
        const resp = await fetch('/api/directory-tree');
        const data = await resp.json();
        if (data.success && data.tree) {
            treeDataCache[containerId] = data.tree;
            // 兼容旧代码
            if (containerId === 'scriptTree') treeData = data.tree;
            renderTree(containerId, data.tree, config);
        } else {
            treeView.innerHTML = '<div class="tree-empty">加载目录结构失败</div>';
        }
    } catch (error) {
        console.error('加载目录树失败:', error);
        treeView.innerHTML = '<div class="tree-empty">加载目录结构失败</div>';
    }
}

function renderTree(containerId, data, config = {}) {
    const treeView = document.getElementById(containerId);
    if (!treeView) return;
    
    if (!data || !Array.isArray(data) || data.length === 0) {
        treeView.innerHTML = '<div class="tree-empty">没有找到脚本文件</div>';
        return;
    }

    let html = '';
    data.forEach(item => {
        if (item.type === 'directory' && item.name !== '__pycache__') {
            html += renderDirectoryNode(item, '', containerId);
        } else if (item.type === 'file') {
            html += renderFileNode(item.name, '', containerId);
        }
    });

    treeView.innerHTML = html;
    bindTreeEvents(containerId, config);
}

function renderDirectoryNode(directory, parentPath, containerId = 'scriptTree') {
    // 用 path（真实目录名）构建文件系统路径，用 name（显示名）做展示
    const realPath = directory.path || (parentPath ? `${parentPath}/${directory.name}` : directory.name);
    const displayName = directory.name;
    let html = `
        <div class="tree-node">
            <div class="tree-folder" data-path="${realPath}" data-container="${containerId}">
                <span class="tree-folder-icon">▶</span>
                <span class="tree-folder-name">${displayName}</span>
            </div>
            <div class="tree-children">`;

    if (directory.children) {
        directory.children.forEach(child => {
            if (child.type === 'directory' && child.name !== '__pycache__') {
                html += renderDirectoryNode(child, realPath, containerId);
            } else if (child.type === 'file') {
                html += renderFileNode(child.name, realPath, containerId);
            }
        });
    }

    html += '</div></div>';
    return html;
}

function renderFileNode(file, parentPath, containerId = 'scriptTree') {
    const fullPath = parentPath ? `${parentPath}/${file}` : file;
    return `
        <div class="tree-file" data-file="${file}" data-directory="${parentPath}" data-full-path="${fullPath}" data-container="${containerId}">
            <div class="tree-file-content">
                <span class="tree-file-icon">🐍</span>
                <span class="tree-file-name">${file}</span>
            </div>
            <button class="btn-preview" onclick="previewScript('${fullPath}'); event.stopPropagation();" title="预览脚本内容">
                <span>👁</span>
            </button>
        </div>`;
}

function bindTreeEvents(containerId = 'scriptTree', config = {}) {
    const treeView = document.getElementById(containerId);
    if (!treeView) return;
    
    // 移除旧事件监听（通过克隆节点方式）
    const newTreeView = treeView.cloneNode(true);
    treeView.parentNode.replaceChild(newTreeView, treeView);
    
    newTreeView.addEventListener('click', function(e) {
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
            selectScriptFile(e.target.closest('.tree-file'), config);
        }
    });
}

function selectScriptFile(fileNode, config = {}) {
    const containerId = fileNode.dataset.container || 'scriptTree';
    const container = document.getElementById(containerId);
    
    // 只在当前容器内清除选中状态
    if (container) {
        container.querySelectorAll('.tree-file.selected').forEach(n => n.classList.remove('selected'));
    }
    fileNode.classList.add('selected');

    const fileName = fileNode.dataset.file;
    const directory = fileNode.dataset.directory || '';
    const fullPath = fileNode.dataset.fullPath || '';

    // 更新对应的隐藏字段
    const selectedPathEl = document.getElementById(config.selectedPathId || 'selectedPath');
    const directoryInput = document.getElementById(config.directoryInputId || 'script_directory');
    const fileInput = document.getElementById(config.fileInputId || 'script_file');
    const fullPathInput = document.getElementById(config.fullPathInputId || 'script_full_path');

    if (selectedPathEl) selectedPathEl.textContent = fullPath || fileName;
    if (directoryInput) directoryInput.value = directory;
    if (fileInput) fileInput.value = fileName;
    if (fullPathInput) fullPathInput.value = fullPath;
    
    // 调用回调函数
    if (config.onSelect && typeof config.onSelect === 'function') {
        config.onSelect({ fileName, directory, fullPath });
    }
}

function filterTree(containerId, searchTerm, config = {}) {
    const treeView = document.getElementById(containerId);
    const data = treeDataCache[containerId];
    if (!treeView || !data) return;

    const term = searchTerm.toLowerCase();
    const filtered = filterTreeData(data, term);

    if (filtered.length === 0) {
        treeView.innerHTML = '<div class="tree-no-results">没有匹配的脚本文件</div>';
        return;
    }

    let html = '';
    filtered.forEach(item => {
        if (item.type === 'directory') {
            html += renderDirectoryNodeExpanded(item, '', containerId);
        } else if (item.type === 'file') {
            html += renderFileNode(item.name, '', containerId);
        }
    });

    treeView.innerHTML = html;
    bindTreeEvents(containerId, config);

    // 展开所有目录
    treeView.querySelectorAll('.tree-folder').forEach(f => {
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

function renderDirectoryNodeExpanded(directory, parentPath, containerId = 'scriptTree') {
    const realPath = directory.path || (parentPath ? `${parentPath}/${directory.name}` : directory.name);
    const displayName = directory.name;
    let html = `
        <div class="tree-node">
            <div class="tree-folder expanded" data-path="${realPath}" data-container="${containerId}">
                <span class="tree-folder-icon">▶</span>
                <span class="tree-folder-name">${displayName}</span>
            </div>
            <div class="tree-children" style="display: block;">`;

    if (directory.children) {
        directory.children.forEach(child => {
            if (child.type === 'directory') {
                html += renderDirectoryNodeExpanded(child, realPath, containerId);
            } else if (child.type === 'file') {
                html += renderFileNode(child.name, realPath, containerId);
            }
        });
    }

    html += '</div></div>';
    return html;
}
