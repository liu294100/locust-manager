/**
 * 实例管理页面JavaScript
 * 处理实例列表、状态监控、日志查看等功能
 */

class InstanceManager {
    constructor() {
        this.instances = [];
        this.filteredInstances = [];
        this.currentFilter = 'all';
        this.currentSort = { field: 'start_time', direction: 'desc' };
        this.refreshInterval = null;
        this.logRefreshInterval = null;
        this.selectedInstances = new Set();
        this.init();
    }

    /**
     * 初始化实例管理器
     */
    init() {
        this.bindEvents();
        this.loadInstances();
        this.startAutoRefresh();
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 刷新按钮
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadInstances();
            });
        }

        // 停止所有按钮
        const stopAllBtn = document.getElementById('stop-all-btn');
        if (stopAllBtn) {
            stopAllBtn.addEventListener('click', () => {
                this.stopAllInstances();
            });
        }

        // 过滤器
        const filterButtons = document.querySelectorAll('[data-filter]');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setFilter(e.target.dataset.filter);
            });
        });

        // 搜索
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', Utils.debounce((e) => {
                this.searchInstances(e.target.value);
            }, 300));
        }

        // 排序
        const sortButtons = document.querySelectorAll('[data-sort]');
        sortButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const field = e.target.dataset.sort;
                this.sortInstances(field);
            });
        });

        // 全选/取消全选
        const selectAllCheckbox = document.getElementById('select-all');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                this.toggleSelectAll(e.target.checked);
            });
        }

        // 批量操作
        const batchStopBtn = document.getElementById('batch-stop-btn');
        if (batchStopBtn) {
            batchStopBtn.addEventListener('click', () => {
                this.batchStopInstances();
            });
        }

        // 日志模态框事件
        const logModal = document.getElementById('logModal');
        if (logModal) {
            logModal.addEventListener('hidden.bs.modal', () => {
                this.stopLogRefresh();
            });
        }

        // 自动刷新切换
        const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }
    }

    /**
     * 加载实例列表
     */
    async loadInstances() {
        try {
            Loading.show('加载实例列表...');
            
            const response = await API.get('/api/instances');
            
            if (response.success) {
                this.instances = response.data.instances || [];
                this.updateStatistics(response.data.statistics);
                this.filterAndRenderInstances();
            } else {
                Notification.error('加载实例列表失败: ' + response.message);
            }
        } catch (error) {
            console.error('加载实例列表失败:', error);
            Notification.error('加载实例列表失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 更新统计信息
     */
    updateStatistics(stats) {
        if (!stats) return;

        const elements = {
            'total-instances': stats.total || 0,
            'running-instances': stats.running || 0,
            'stopped-instances': stats.stopped || 0,
            'error-instances': stats.error || 0
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        // 更新进度条
        const progressBar = document.getElementById('running-progress');
        if (progressBar && stats.total > 0) {
            const percentage = (stats.running / stats.total) * 100;
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }
    }

    /**
     * 设置过滤器
     */
    setFilter(filter) {
        this.currentFilter = filter;
        
        // 更新按钮状态
        document.querySelectorAll('[data-filter]').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-filter="${filter}"]`).classList.add('active');
        
        this.filterAndRenderInstances();
    }

    /**
     * 搜索实例
     */
    searchInstances(query) {
        this.searchQuery = query.toLowerCase();
        this.filterAndRenderInstances();
    }

    /**
     * 排序实例
     */
    sortInstances(field) {
        if (this.currentSort.field === field) {
            this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.currentSort.field = field;
            this.currentSort.direction = 'asc';
        }

        // 更新排序按钮状态
        document.querySelectorAll('[data-sort]').forEach(btn => {
            btn.classList.remove('sort-asc', 'sort-desc');
        });
        
        const sortBtn = document.querySelector(`[data-sort="${field}"]`);
        if (sortBtn) {
            sortBtn.classList.add(`sort-${this.currentSort.direction}`);
        }

        this.filterAndRenderInstances();
    }

    /**
     * 过滤和渲染实例
     */
    filterAndRenderInstances() {
        // 过滤
        this.filteredInstances = this.instances.filter(instance => {
            // 状态过滤
            if (this.currentFilter !== 'all' && instance.status !== this.currentFilter) {
                return false;
            }

            // 搜索过滤
            if (this.searchQuery) {
                const searchFields = [
                    instance.task_name,
                    instance.node,
                    instance.instance_id,
                    instance.port?.toString()
                ].filter(Boolean);

                const matchesSearch = searchFields.some(field => 
                    field.toLowerCase().includes(this.searchQuery)
                );

                if (!matchesSearch) {
                    return false;
                }
            }

            return true;
        });

        // 排序
        this.filteredInstances.sort((a, b) => {
            const field = this.currentSort.field;
            let aValue = a[field];
            let bValue = b[field];

            // 特殊处理某些字段
            if (field === 'start_time') {
                aValue = new Date(aValue);
                bValue = new Date(bValue);
            } else if (field === 'cpu_usage' || field === 'memory_usage') {
                aValue = parseFloat(aValue) || 0;
                bValue = parseFloat(bValue) || 0;
            }

            if (aValue < bValue) {
                return this.currentSort.direction === 'asc' ? -1 : 1;
            }
            if (aValue > bValue) {
                return this.currentSort.direction === 'asc' ? 1 : -1;
            }
            return 0;
        });

        this.renderInstances();
        this.updateFilterCounts();
    }

    /**
     * 渲染实例列表
     */
    renderInstances() {
        const container = document.getElementById('instances-container');
        if (!container) return;

        if (this.filteredInstances.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-server fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">没有找到实例</h5>
                    <p class="text-muted">当前没有符合条件的实例</p>
                </div>
            `;
            return;
        }

        const html = this.filteredInstances.map(instance => this.renderInstanceCard(instance)).join('');
        container.innerHTML = html;

        // 绑定实例操作事件
        this.bindInstanceEvents();
    }

    /**
     * 渲染单个实例卡片
     */
    renderInstanceCard(instance) {
        const statusBadge = Utils.getStatusBadge(instance.status);
        const runtime = instance.start_time ? Utils.formatDuration(Date.now() - new Date(instance.start_time)) : '-';
        
        return `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card instance-card" data-instance-id="${instance.instance_id}">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <div class="form-check">
                            <input class="form-check-input instance-checkbox" type="checkbox" 
                                   value="${instance.instance_id}" id="check-${instance.instance_id}">
                            <label class="form-check-label fw-bold" for="check-${instance.instance_id}">
                                ${instance.task_name || '未知任务'}
                            </label>
                        </div>
                        ${statusBadge}
                    </div>
                    <div class="card-body">
                        <div class="row g-2 mb-3">
                            <div class="col-6">
                                <small class="text-muted">实例ID</small>
                                <div class="fw-bold small">${instance.instance_id}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">节点</small>
                                <div class="fw-bold small">${instance.node || '-'}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">端口</small>
                                <div class="fw-bold small">${instance.port || '-'}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">运行时间</small>
                                <div class="fw-bold small">${runtime}</div>
                            </div>
                        </div>
                        
                        ${this.renderResourceUsage(instance)}
                        
                        <div class="d-flex gap-2 mt-3">
                            <button class="btn btn-sm btn-outline-primary view-logs-btn" 
                                    data-instance-id="${instance.instance_id}"
                                    title="查看日志">
                                <i class="fas fa-file-alt"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-info view-details-btn" 
                                    data-instance-id="${instance.instance_id}"
                                    title="查看详情">
                                <i class="fas fa-info-circle"></i>
                            </button>
                            ${instance.status === 'running' ? `
                                <button class="btn btn-sm btn-outline-warning stop-instance-btn" 
                                        data-instance-id="${instance.instance_id}"
                                        title="停止实例">
                                    <i class="fas fa-stop"></i>
                                </button>
                            ` : ''}
                            <button class="btn btn-sm btn-outline-danger remove-instance-btn" 
                                    data-instance-id="${instance.instance_id}"
                                    title="移除实例">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 渲染资源使用情况
     */
    renderResourceUsage(instance) {
        if (!instance.cpu_usage && !instance.memory_usage) {
            return '<div class="text-muted small">资源使用情况不可用</div>';
        }

        const cpuUsage = parseFloat(instance.cpu_usage) || 0;
        const memoryUsage = parseFloat(instance.memory_usage) || 0;

        return `
            <div class="resource-usage">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">CPU</small>
                    <small class="fw-bold">${cpuUsage.toFixed(1)}%</small>
                </div>
                <div class="progress mb-2" style="height: 4px;">
                    <div class="progress-bar ${cpuUsage > 80 ? 'bg-danger' : cpuUsage > 60 ? 'bg-warning' : 'bg-success'}" 
                         style="width: ${cpuUsage}%"></div>
                </div>
                
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">内存</small>
                    <small class="fw-bold">${memoryUsage.toFixed(1)}%</small>
                </div>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar ${memoryUsage > 80 ? 'bg-danger' : memoryUsage > 60 ? 'bg-warning' : 'bg-success'}" 
                         style="width: ${memoryUsage}%"></div>
                </div>
            </div>
        `;
    }

    /**
     * 绑定实例操作事件
     */
    bindInstanceEvents() {
        // 实例选择
        document.querySelectorAll('.instance-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const instanceId = e.target.value;
                if (e.target.checked) {
                    this.selectedInstances.add(instanceId);
                } else {
                    this.selectedInstances.delete(instanceId);
                }
                this.updateBatchActions();
            });
        });

        // 查看日志
        document.querySelectorAll('.view-logs-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const instanceId = e.target.closest('[data-instance-id]').dataset.instanceId;
                this.viewInstanceLogs(instanceId);
            });
        });

        // 查看详情
        document.querySelectorAll('.view-details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const instanceId = e.target.closest('[data-instance-id]').dataset.instanceId;
                this.viewInstanceDetails(instanceId);
            });
        });

        // 停止实例
        document.querySelectorAll('.stop-instance-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const instanceId = e.target.closest('[data-instance-id]').dataset.instanceId;
                this.stopInstance(instanceId);
            });
        });

        // 移除实例
        document.querySelectorAll('.remove-instance-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const instanceId = e.target.closest('[data-instance-id]').dataset.instanceId;
                this.removeInstance(instanceId);
            });
        });
    }

    /**
     * 更新过滤器计数
     */
    updateFilterCounts() {
        const counts = {
            all: this.instances.length,
            running: this.instances.filter(i => i.status === 'running').length,
            stopped: this.instances.filter(i => i.status === 'stopped').length,
            error: this.instances.filter(i => i.status === 'error').length
        };

        Object.entries(counts).forEach(([filter, count]) => {
            const badge = document.querySelector(`[data-filter="${filter}"] .badge`);
            if (badge) {
                badge.textContent = count;
            }
        });
    }

    /**
     * 全选/取消全选
     */
    toggleSelectAll(checked) {
        this.selectedInstances.clear();
        
        document.querySelectorAll('.instance-checkbox').forEach(checkbox => {
            checkbox.checked = checked;
            if (checked) {
                this.selectedInstances.add(checkbox.value);
            }
        });
        
        this.updateBatchActions();
    }

    /**
     * 更新批量操作按钮状态
     */
    updateBatchActions() {
        const batchActions = document.getElementById('batch-actions');
        const selectedCount = document.getElementById('selected-count');
        
        if (batchActions && selectedCount) {
            if (this.selectedInstances.size > 0) {
                batchActions.style.display = 'block';
                selectedCount.textContent = this.selectedInstances.size;
            } else {
                batchActions.style.display = 'none';
            }
        }
    }

    /**
     * 查看实例日志
     */
    async viewInstanceLogs(instanceId) {
        try {
            const instance = this.instances.find(i => i.instance_id === instanceId);
            if (!instance) return;

            // 设置模态框标题
            const modalTitle = document.getElementById('logModalLabel');
            if (modalTitle) {
                modalTitle.textContent = `实例日志 - ${instance.task_name} (${instanceId})`;
            }

            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('logModal'));
            modal.show();

            // 加载日志
            await this.loadInstanceLogs(instanceId);
            
            // 开始自动刷新日志
            this.startLogRefresh(instanceId);

        } catch (error) {
            console.error('查看实例日志失败:', error);
            Notification.error('查看实例日志失败: ' + error.message);
        }
    }

    /**
     * 加载实例日志
     */
    async loadInstanceLogs(instanceId) {
        try {
            const response = await API.get(`/api/instances/${instanceId}/logs`);
            
            const logContent = document.getElementById('log-content');
            if (logContent) {
                if (response.success && response.data.logs) {
                    logContent.textContent = response.data.logs;
                    // 滚动到底部
                    logContent.scrollTop = logContent.scrollHeight;
                } else {
                    logContent.textContent = '暂无日志数据';
                }
            }
        } catch (error) {
            console.error('加载实例日志失败:', error);
            const logContent = document.getElementById('log-content');
            if (logContent) {
                logContent.textContent = '加载日志失败: ' + error.message;
            }
        }
    }

    /**
     * 开始日志自动刷新
     */
    startLogRefresh(instanceId) {
        this.stopLogRefresh();
        this.logRefreshInterval = setInterval(() => {
            this.loadInstanceLogs(instanceId);
        }, 2000);
    }

    /**
     * 停止日志自动刷新
     */
    stopLogRefresh() {
        if (this.logRefreshInterval) {
            clearInterval(this.logRefreshInterval);
            this.logRefreshInterval = null;
        }
    }

    /**
     * 查看实例详情
     */
    viewInstanceDetails(instanceId) {
        // 跳转到实例详情页面或显示详情模态框
        window.location.href = `/instances/${instanceId}`;
    }

    /**
     * 停止实例
     */
    async stopInstance(instanceId) {
        const confirmed = await ConfirmDialog.show(
            '确认停止实例',
            '确定要停止这个实例吗？',
            'warning'
        );

        if (!confirmed) return;

        try {
            Loading.show('正在停止实例...');
            
            const response = await API.post(`/api/instances/${instanceId}/stop`);
            
            if (response.success) {
                Notification.success('实例已停止');
                this.loadInstances();
            } else {
                Notification.error('停止实例失败: ' + response.message);
            }
        } catch (error) {
            console.error('停止实例失败:', error);
            Notification.error('停止实例失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 移除实例
     */
    async removeInstance(instanceId) {
        const confirmed = await ConfirmDialog.show(
            '确认移除实例',
            '确定要移除这个实例吗？此操作不可撤销。',
            'danger'
        );

        if (!confirmed) return;

        try {
            Loading.show('正在移除实例...');
            
            const response = await API.delete(`/api/instances/${instanceId}`);
            
            if (response.success) {
                Notification.success('实例已移除');
                this.loadInstances();
            } else {
                Notification.error('移除实例失败: ' + response.message);
            }
        } catch (error) {
            console.error('移除实例失败:', error);
            Notification.error('移除实例失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 停止所有实例
     */
    async stopAllInstances() {
        const runningInstances = this.instances.filter(i => i.status === 'running');
        
        if (runningInstances.length === 0) {
            Notification.info('没有正在运行的实例');
            return;
        }

        const confirmed = await ConfirmDialog.show(
            '确认停止所有实例',
            `确定要停止所有 ${runningInstances.length} 个正在运行的实例吗？`,
            'warning'
        );

        if (!confirmed) return;

        try {
            Loading.show('正在停止所有实例...');
            
            const response = await API.post('/api/instances/stop-all');
            
            if (response.success) {
                Notification.success('所有实例已停止');
                this.loadInstances();
            } else {
                Notification.error('停止实例失败: ' + response.message);
            }
        } catch (error) {
            console.error('停止所有实例失败:', error);
            Notification.error('停止所有实例失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 批量停止实例
     */
    async batchStopInstances() {
        if (this.selectedInstances.size === 0) {
            Notification.warning('请选择要停止的实例');
            return;
        }

        const confirmed = await ConfirmDialog.show(
            '确认批量停止',
            `确定要停止选中的 ${this.selectedInstances.size} 个实例吗？`,
            'warning'
        );

        if (!confirmed) return;

        try {
            Loading.show('正在停止选中的实例...');
            
            const instanceIds = Array.from(this.selectedInstances);
            const response = await API.post('/api/instances/batch-stop', {
                instance_ids: instanceIds
            });
            
            if (response.success) {
                Notification.success('选中的实例已停止');
                this.selectedInstances.clear();
                this.loadInstances();
            } else {
                Notification.error('批量停止失败: ' + response.message);
            }
        } catch (error) {
            console.error('批量停止实例失败:', error);
            Notification.error('批量停止失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => {
            this.loadInstances();
        }, 5000);
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
     * 销毁实例管理器
     */
    destroy() {
        this.stopAutoRefresh();
        this.stopLogRefresh();
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在实例管理页面
    if (document.body.dataset.page === 'instances') {
        window.instanceManager = new InstanceManager();
    }
});

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    if (window.instanceManager) {
        window.instanceManager.destroy();
    }
});