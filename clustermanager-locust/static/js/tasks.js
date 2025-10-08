/**
 * 任务管理页面JavaScript
 * 处理任务列表、筛选、操作等功能
 */

class TaskManager {
    constructor() {
        this.currentFilters = {
            status: '',
            search: '',
            creator: ''
        };
        this.refreshInterval = null;
        this.init();
    }

    /**
     * 初始化任务管理器
     */
    init() {
        this.bindEvents();
        this.loadTasks();
        this.startAutoRefresh();
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 筛选器事件
        this.bindFilterEvents();
        
        // 操作按钮事件
        this.bindActionEvents();
        
        // 刷新按钮
        const refreshBtn = document.getElementById('refresh-tasks-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadTasks();
            });
        }

        // 创建任务按钮
        const createBtn = document.getElementById('create-task-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                window.location.href = '/tasks/create';
            });
        }

        // 批量操作
        this.bindBatchActions();
    }

    /**
     * 绑定筛选器事件
     */
    bindFilterEvents() {
        // 状态筛选
        const statusFilter = document.getElementById('status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.currentFilters.status = e.target.value;
                this.loadTasks();
            });
        }

        // 搜索框
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', Utils.debounce((e) => {
                this.currentFilters.search = e.target.value;
                this.loadTasks();
            }, 500));
        }

        // 创建者筛选
        const creatorFilter = document.getElementById('creator-filter');
        if (creatorFilter) {
            creatorFilter.addEventListener('change', (e) => {
                this.currentFilters.creator = e.target.value;
                this.loadTasks();
            });
        }

        // 清除筛选器
        const clearFiltersBtn = document.getElementById('clear-filters-btn');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => {
                this.clearFilters();
            });
        }
    }

    /**
     * 绑定操作按钮事件
     */
    bindActionEvents() {
        // 使用事件委托处理动态生成的按钮
        const tasksList = document.getElementById('tasks-list');
        if (tasksList) {
            tasksList.addEventListener('click', (e) => {
                const target = e.target.closest('[data-action]');
                if (!target) return;

                const action = target.dataset.action;
                const taskId = target.dataset.taskId;
                
                switch (action) {
                    case 'view':
                        this.viewTask(taskId);
                        break;
                    case 'start':
                        this.startTask(taskId);
                        break;
                    case 'stop':
                        this.stopTask(taskId);
                        break;
                    case 'delete':
                        this.deleteTask(taskId);
                        break;
                    case 'clone':
                        this.cloneTask(taskId);
                        break;
                }
            });
        }
    }

    /**
     * 绑定批量操作事件
     */
    bindBatchActions() {
        // 全选/取消全选
        const selectAllCheckbox = document.getElementById('select-all-tasks');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                const checkboxes = document.querySelectorAll('.task-checkbox');
                checkboxes.forEach(checkbox => {
                    checkbox.checked = e.target.checked;
                });
                this.updateBatchActions();
            });
        }

        // 批量操作按钮
        const batchStartBtn = document.getElementById('batch-start-btn');
        const batchStopBtn = document.getElementById('batch-stop-btn');
        const batchDeleteBtn = document.getElementById('batch-delete-btn');

        if (batchStartBtn) {
            batchStartBtn.addEventListener('click', () => {
                this.batchStartTasks();
            });
        }

        if (batchStopBtn) {
            batchStopBtn.addEventListener('click', () => {
                this.batchStopTasks();
            });
        }

        if (batchDeleteBtn) {
            batchDeleteBtn.addEventListener('click', () => {
                this.batchDeleteTasks();
            });
        }
    }

    /**
     * 加载任务列表
     */
    async loadTasks() {
        try {
            const params = {
                ...this.currentFilters,
                page: 1,
                per_page: 50
            };

            // 移除空值
            Object.keys(params).forEach(key => {
                if (!params[key]) {
                    delete params[key];
                }
            });

            const data = await API.get('/api/tasks', params);
            this.renderTasks(data.tasks || []);
            this.updatePagination(data.pagination);
            
        } catch (error) {
            console.error('加载任务列表失败:', error);
            Notification.error('加载任务列表失败: ' + error.message);
        }
    }

    /**
     * 渲染任务列表
     */
    renderTasks(tasks) {
        const container = document.getElementById('tasks-list');
        if (!container) return;

        if (tasks.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-tasks fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">暂无任务</h5>
                    <p class="text-muted">点击"创建任务"按钮开始创建您的第一个负载测试任务</p>
                    <a href="/tasks/create" class="btn btn-primary">
                        <i class="fas fa-plus"></i> 创建任务
                    </a>
                </div>
            `;
            return;
        }

        const tasksHtml = tasks.map(task => this.renderTaskCard(task)).join('');
        container.innerHTML = tasksHtml;

        // 重新绑定复选框事件
        this.bindTaskCheckboxes();
    }

    /**
     * 渲染单个任务卡片
     */
    renderTaskCard(task) {
        const statusBadge = Utils.getStatusBadge(task.status);
        const createdAt = Utils.formatDateTime(task.created_at);
        const updatedAt = Utils.formatDateTime(task.updated_at);
        
        return `
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card task-card h-100" data-task-id="${task.id}">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <div class="form-check">
                            <input class="form-check-input task-checkbox" type="checkbox" 
                                   value="${task.id}" id="task-${task.id}">
                            <label class="form-check-label fw-bold" for="task-${task.id}">
                                ${task.name}
                            </label>
                        </div>
                        ${statusBadge}
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <small class="text-muted">脚本:</small>
                            <div class="fw-medium">${task.script_name}</div>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">负载配置:</small>
                            <div class="fw-medium">
                                ${task.users || 0} 用户, ${task.spawn_rate || 0}/s 启动速率
                            </div>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">目标主机:</small>
                            <div class="fw-medium">${task.host || '-'}</div>
                        </div>
                        <div class="mb-2">
                            <small class="text-muted">创建时间:</small>
                            <div class="fw-medium">${createdAt}</div>
                        </div>
                        ${task.description ? `
                            <div class="mb-2">
                                <small class="text-muted">描述:</small>
                                <div class="text-truncate" title="${task.description}">
                                    ${task.description}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="card-footer bg-transparent">
                        <div class="btn-group w-100" role="group">
                            <button type="button" class="btn btn-outline-primary btn-sm" 
                                    data-action="view" data-task-id="${task.id}"
                                    title="查看详情">
                                <i class="fas fa-eye"></i>
                            </button>
                            ${this.getActionButtons(task)}
                            <div class="btn-group" role="group">
                                <button type="button" class="btn btn-outline-secondary btn-sm dropdown-toggle" 
                                        data-bs-toggle="dropdown">
                                    <i class="fas fa-ellipsis-h"></i>
                                </button>
                                <ul class="dropdown-menu">
                                    <li>
                                        <a class="dropdown-item" href="#" 
                                           data-action="clone" data-task-id="${task.id}">
                                            <i class="fas fa-copy"></i> 克隆任务
                                        </a>
                                    </li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li>
                                        <a class="dropdown-item text-danger" href="#" 
                                           data-action="delete" data-task-id="${task.id}">
                                            <i class="fas fa-trash"></i> 删除任务
                                        </a>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 获取操作按钮
     */
    getActionButtons(task) {
        switch (task.status) {
            case 'running':
                return `
                    <button type="button" class="btn btn-outline-danger btn-sm" 
                            data-action="stop" data-task-id="${task.id}"
                            title="停止任务">
                        <i class="fas fa-stop"></i>
                    </button>
                `;
            case 'stopped':
            case 'failed':
            case 'completed':
                return `
                    <button type="button" class="btn btn-outline-success btn-sm" 
                            data-action="start" data-task-id="${task.id}"
                            title="启动任务">
                        <i class="fas fa-play"></i>
                    </button>
                `;
            default:
                return `
                    <button type="button" class="btn btn-outline-success btn-sm" 
                            data-action="start" data-task-id="${task.id}"
                            title="启动任务">
                        <i class="fas fa-play"></i>
                    </button>
                `;
        }
    }

    /**
     * 绑定任务复选框事件
     */
    bindTaskCheckboxes() {
        const checkboxes = document.querySelectorAll('.task-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateBatchActions();
            });
        });
    }

    /**
     * 更新批量操作按钮状态
     */
    updateBatchActions() {
        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        const batchActionsContainer = document.getElementById('batch-actions');
        
        if (batchActionsContainer) {
            if (selectedCheckboxes.length > 0) {
                batchActionsContainer.style.display = 'block';
                document.getElementById('selected-count').textContent = selectedCheckboxes.length;
            } else {
                batchActionsContainer.style.display = 'none';
            }
        }
    }

    /**
     * 查看任务详情
     */
    viewTask(taskId) {
        window.location.href = `/tasks/${taskId}`;
    }

    /**
     * 启动任务
     */
    async startTask(taskId) {
        try {
            const confirmed = await Confirm.show(
                '确定要启动这个任务吗？',
                '启动任务'
            );
            
            if (!confirmed) return;

            Loading.show('正在启动任务...');
            
            const result = await API.post(`/api/tasks/${taskId}/start`);
            
            if (result.success) {
                Notification.success('任务启动成功');
                this.loadTasks(); // 刷新列表
            } else {
                Notification.error('任务启动失败: ' + (result.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('启动任务失败:', error);
            Notification.error('启动任务失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 停止任务
     */
    async stopTask(taskId) {
        try {
            const confirmed = await Confirm.show(
                '确定要停止这个任务吗？',
                '停止任务'
            );
            
            if (!confirmed) return;

            Loading.show('正在停止任务...');
            
            const result = await API.post(`/api/tasks/${taskId}/stop`);
            
            if (result.success) {
                Notification.success('任务停止成功');
                this.loadTasks(); // 刷新列表
            } else {
                Notification.error('任务停止失败: ' + (result.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('停止任务失败:', error);
            Notification.error('停止任务失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 删除任务
     */
    async deleteTask(taskId) {
        try {
            const confirmed = await Confirm.show(
                '确定要删除这个任务吗？此操作不可撤销。',
                '删除任务'
            );
            
            if (!confirmed) return;

            Loading.show('正在删除任务...');
            
            const result = await API.delete(`/api/tasks/${taskId}`);
            
            if (result.success) {
                Notification.success('任务删除成功');
                this.loadTasks(); // 刷新列表
            } else {
                Notification.error('任务删除失败: ' + (result.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('删除任务失败:', error);
            Notification.error('删除任务失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 克隆任务
     */
    async cloneTask(taskId) {
        try {
            Loading.show('正在克隆任务...');
            
            const result = await API.post(`/api/tasks/${taskId}/clone`);
            
            if (result.success) {
                Notification.success('任务克隆成功');
                this.loadTasks(); // 刷新列表
            } else {
                Notification.error('任务克隆失败: ' + (result.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('克隆任务失败:', error);
            Notification.error('克隆任务失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 批量启动任务
     */
    async batchStartTasks() {
        const selectedIds = this.getSelectedTaskIds();
        if (selectedIds.length === 0) return;

        try {
            const confirmed = await Confirm.show(
                `确定要启动选中的 ${selectedIds.length} 个任务吗？`,
                '批量启动任务'
            );
            
            if (!confirmed) return;

            Loading.show('正在批量启动任务...');
            
            const result = await API.post('/api/tasks/batch/start', {
                task_ids: selectedIds
            });
            
            if (result.success) {
                Notification.success(`成功启动 ${result.success_count} 个任务`);
                if (result.failed_count > 0) {
                    Notification.warning(`${result.failed_count} 个任务启动失败`);
                }
                this.loadTasks(); // 刷新列表
            } else {
                Notification.error('批量启动失败: ' + (result.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('批量启动任务失败:', error);
            Notification.error('批量启动任务失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 批量停止任务
     */
    async batchStopTasks() {
        const selectedIds = this.getSelectedTaskIds();
        if (selectedIds.length === 0) return;

        try {
            const confirmed = await Confirm.show(
                `确定要停止选中的 ${selectedIds.length} 个任务吗？`,
                '批量停止任务'
            );
            
            if (!confirmed) return;

            Loading.show('正在批量停止任务...');
            
            const result = await API.post('/api/tasks/batch/stop', {
                task_ids: selectedIds
            });
            
            if (result.success) {
                Notification.success(`成功停止 ${result.success_count} 个任务`);
                if (result.failed_count > 0) {
                    Notification.warning(`${result.failed_count} 个任务停止失败`);
                }
                this.loadTasks(); // 刷新列表
            } else {
                Notification.error('批量停止失败: ' + (result.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('批量停止任务失败:', error);
            Notification.error('批量停止任务失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 批量删除任务
     */
    async batchDeleteTasks() {
        const selectedIds = this.getSelectedTaskIds();
        if (selectedIds.length === 0) return;

        try {
            const confirmed = await Confirm.show(
                `确定要删除选中的 ${selectedIds.length} 个任务吗？此操作不可撤销。`,
                '批量删除任务'
            );
            
            if (!confirmed) return;

            Loading.show('正在批量删除任务...');
            
            const result = await API.post('/api/tasks/batch/delete', {
                task_ids: selectedIds
            });
            
            if (result.success) {
                Notification.success(`成功删除 ${result.success_count} 个任务`);
                if (result.failed_count > 0) {
                    Notification.warning(`${result.failed_count} 个任务删除失败`);
                }
                this.loadTasks(); // 刷新列表
            } else {
                Notification.error('批量删除失败: ' + (result.message || '未知错误'));
            }
            
        } catch (error) {
            console.error('批量删除任务失败:', error);
            Notification.error('批量删除任务失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 获取选中的任务ID列表
     */
    getSelectedTaskIds() {
        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        return Array.from(selectedCheckboxes).map(checkbox => checkbox.value);
    }

    /**
     * 清除筛选器
     */
    clearFilters() {
        this.currentFilters = {
            status: '',
            search: '',
            creator: ''
        };

        // 重置表单
        const statusFilter = document.getElementById('status-filter');
        const searchInput = document.getElementById('search-input');
        const creatorFilter = document.getElementById('creator-filter');

        if (statusFilter) statusFilter.value = '';
        if (searchInput) searchInput.value = '';
        if (creatorFilter) creatorFilter.value = '';

        // 重新加载任务
        this.loadTasks();
    }

    /**
     * 更新分页
     */
    updatePagination(pagination) {
        // 这里可以实现分页逻辑
        // 暂时简化处理
    }

    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => {
            this.loadTasks();
        }, CONFIG.refreshInterval);
    }

    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * 销毁任务管理器
     */
    destroy() {
        this.stopAutoRefresh();
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在任务页面
    if (document.body.dataset.page === 'tasks') {
        window.taskManager = new TaskManager();
    }
});

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    if (window.taskManager) {
        window.taskManager.destroy();
    }
});