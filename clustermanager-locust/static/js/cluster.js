/**
 * 集群管理页面JavaScript
 * 处理集群状态监控、节点管理、性能图表等功能
 */

class ClusterManager {
    constructor() {
        this.nodes = [];
        this.clusterStats = {};
        this.refreshInterval = null;
        this.charts = {};
        this.init();
    }

    /**
     * 初始化集群管理器
     */
    init() {
        this.bindEvents();
        this.initCharts();
        this.loadClusterData();
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
                this.loadClusterData();
            });
        }

        // 清理集群按钮
        const cleanupBtn = document.getElementById('cleanup-btn');
        if (cleanupBtn) {
            cleanupBtn.addEventListener('click', () => {
                this.cleanupCluster();
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

        // 图表时间范围选择
        const timeRangeSelect = document.getElementById('time-range-select');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', (e) => {
                this.updateChartsTimeRange(e.target.value);
            });
        }
    }

    /**
     * 初始化图表
     */
    initCharts() {
        // 任务分布饼图
        const taskDistCtx = document.getElementById('taskDistributionChart');
        if (taskDistCtx) {
            this.charts.taskDistribution = new Chart(taskDistCtx, {
                type: 'pie',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            '#007bff', '#28a745', '#ffc107', '#dc3545',
                            '#6f42c1', '#fd7e14', '#20c997', '#6c757d'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }

        // CPU使用率趋势图
        const cpuTrendCtx = document.getElementById('cpuTrendChart');
        if (cpuTrendCtx) {
            this.charts.cpuTrend = new Chart(cpuTrendCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '平均CPU使用率',
                        data: [],
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        },
                        x: {
                            type: 'time',
                            time: {
                                displayFormats: {
                                    minute: 'HH:mm',
                                    hour: 'HH:mm'
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `CPU: ${context.parsed.y.toFixed(1)}%`;
                                }
                            }
                        }
                    }
                }
            });
        }

        // 内存使用率趋势图
        const memoryTrendCtx = document.getElementById('memoryTrendChart');
        if (memoryTrendCtx) {
            this.charts.memoryTrend = new Chart(memoryTrendCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '平均内存使用率',
                        data: [],
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        },
                        x: {
                            type: 'time',
                            time: {
                                displayFormats: {
                                    minute: 'HH:mm',
                                    hour: 'HH:mm'
                                }
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `内存: ${context.parsed.y.toFixed(1)}%`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    /**
     * 加载集群数据
     */
    async loadClusterData() {
        try {
            Loading.show('加载集群数据...');
            
            const response = await API.get('/api/cluster/status');
            
            if (response.success) {
                this.clusterStats = response.data.statistics || {};
                this.nodes = response.data.nodes || [];
                
                this.updateClusterOverview();
                this.renderNodes();
                this.updateCharts(response.data.metrics);
            } else {
                Notification.error('加载集群数据失败: ' + response.message);
            }
        } catch (error) {
            console.error('加载集群数据失败:', error);
            Notification.error('加载集群数据失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 更新集群概览
     */
    updateClusterOverview() {
        const elements = {
            'total-nodes': this.clusterStats.total_nodes || 0,
            'active-nodes': this.clusterStats.active_nodes || 0,
            'total-instances': this.clusterStats.total_instances || 0,
            'running-instances': this.clusterStats.running_instances || 0,
            'avg-cpu': (this.clusterStats.avg_cpu || 0).toFixed(1),
            'avg-memory': (this.clusterStats.avg_memory || 0).toFixed(1),
            'avg-load': (this.clusterStats.avg_load || 0).toFixed(2)
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        // 更新健康状态
        const healthStatus = document.getElementById('cluster-health');
        if (healthStatus) {
            const healthPercentage = this.clusterStats.total_nodes > 0 
                ? (this.clusterStats.active_nodes / this.clusterStats.total_nodes) * 100 
                : 0;
            
            let healthClass = 'success';
            let healthText = '健康';
            
            if (healthPercentage < 50) {
                healthClass = 'danger';
                healthText = '严重';
            } else if (healthPercentage < 80) {
                healthClass = 'warning';
                healthText = '警告';
            }
            
            healthStatus.className = `badge bg-${healthClass}`;
            healthStatus.textContent = healthText;
        }
    }

    /**
     * 渲染节点列表
     */
    renderNodes() {
        const container = document.getElementById('nodes-container');
        if (!container) return;

        if (this.nodes.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-server fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">没有找到节点</h5>
                    <p class="text-muted">集群中暂无可用节点</p>
                </div>
            `;
            return;
        }

        const html = this.nodes.map(node => this.renderNodeCard(node)).join('');
        container.innerHTML = html;

        // 绑定节点操作事件
        this.bindNodeEvents();
    }

    /**
     * 渲染单个节点卡片
     */
    renderNodeCard(node) {
        const statusBadge = this.getNodeStatusBadge(node.status);
        const lastHeartbeat = node.last_heartbeat 
            ? Utils.formatDateTime(new Date(node.last_heartbeat))
            : '从未';
        
        return `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card node-card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <div class="fw-bold">${node.hostname || node.ip}</div>
                        ${statusBadge}
                    </div>
                    <div class="card-body">
                        <div class="row g-2 mb-3">
                            <div class="col-6">
                                <small class="text-muted">IP地址</small>
                                <div class="fw-bold small">${node.ip}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">实例数</small>
                                <div class="fw-bold small">${node.instance_count || 0}</div>
                            </div>
                            <div class="col-12">
                                <small class="text-muted">最后心跳</small>
                                <div class="fw-bold small">${lastHeartbeat}</div>
                            </div>
                        </div>
                        
                        ${this.renderNodeResourceUsage(node)}
                        
                        <div class="d-flex gap-2 mt-3">
                            <button class="btn btn-sm btn-outline-primary view-node-details-btn" 
                                    data-node-id="${node.node_id}"
                                    title="查看详情">
                                <i class="fas fa-info-circle"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-warning ping-node-btn" 
                                    data-node-id="${node.node_id}"
                                    title="Ping节点">
                                <i class="fas fa-satellite-dish"></i>
                            </button>
                            ${node.status === 'offline' ? `
                                <button class="btn btn-sm btn-outline-danger remove-node-btn" 
                                        data-node-id="${node.node_id}"
                                        title="移除节点">
                                    <i class="fas fa-trash"></i>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 获取节点状态徽章
     */
    getNodeStatusBadge(status) {
        const badges = {
            'online': '<span class="badge bg-success">在线</span>',
            'offline': '<span class="badge bg-danger">离线</span>',
            'warning': '<span class="badge bg-warning">警告</span>',
            'unknown': '<span class="badge bg-secondary">未知</span>'
        };
        return badges[status] || badges['unknown'];
    }

    /**
     * 渲染节点资源使用情况
     */
    renderNodeResourceUsage(node) {
        if (!node.cpu_usage && !node.memory_usage && !node.load_average) {
            return '<div class="text-muted small">资源使用情况不可用</div>';
        }

        const cpuUsage = parseFloat(node.cpu_usage) || 0;
        const memoryUsage = parseFloat(node.memory_usage) || 0;
        const loadAverage = parseFloat(node.load_average) || 0;

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
                <div class="progress mb-2" style="height: 4px;">
                    <div class="progress-bar ${memoryUsage > 80 ? 'bg-danger' : memoryUsage > 60 ? 'bg-warning' : 'bg-success'}" 
                         style="width: ${memoryUsage}%"></div>
                </div>
                
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">负载</small>
                    <small class="fw-bold">${loadAverage.toFixed(2)}</small>
                </div>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar ${loadAverage > 2 ? 'bg-danger' : loadAverage > 1 ? 'bg-warning' : 'bg-success'}" 
                         style="width: ${Math.min(loadAverage * 50, 100)}%"></div>
                </div>
            </div>
        `;
    }

    /**
     * 绑定节点操作事件
     */
    bindNodeEvents() {
        // 查看节点详情
        document.querySelectorAll('.view-node-details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const nodeId = e.target.closest('[data-node-id]').dataset.nodeId;
                this.viewNodeDetails(nodeId);
            });
        });

        // Ping节点
        document.querySelectorAll('.ping-node-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const nodeId = e.target.closest('[data-node-id]').dataset.nodeId;
                this.pingNode(nodeId);
            });
        });

        // 移除节点
        document.querySelectorAll('.remove-node-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const nodeId = e.target.closest('[data-node-id]').dataset.nodeId;
                this.removeNode(nodeId);
            });
        });
    }

    /**
     * 更新图表
     */
    updateCharts(metrics) {
        if (!metrics) return;

        // 更新任务分布图
        if (this.charts.taskDistribution && metrics.task_distribution) {
            const taskData = metrics.task_distribution;
            this.charts.taskDistribution.data.labels = Object.keys(taskData);
            this.charts.taskDistribution.data.datasets[0].data = Object.values(taskData);
            this.charts.taskDistribution.update();
        }

        // 更新CPU趋势图
        if (this.charts.cpuTrend && metrics.cpu_trend) {
            const cpuData = metrics.cpu_trend;
            this.charts.cpuTrend.data.labels = cpuData.map(item => new Date(item.timestamp));
            this.charts.cpuTrend.data.datasets[0].data = cpuData.map(item => item.value);
            this.charts.cpuTrend.update();
        }

        // 更新内存趋势图
        if (this.charts.memoryTrend && metrics.memory_trend) {
            const memoryData = metrics.memory_trend;
            this.charts.memoryTrend.data.labels = memoryData.map(item => new Date(item.timestamp));
            this.charts.memoryTrend.data.datasets[0].data = memoryData.map(item => item.value);
            this.charts.memoryTrend.update();
        }
    }

    /**
     * 更新图表时间范围
     */
    async updateChartsTimeRange(timeRange) {
        try {
            const response = await API.get(`/api/cluster/metrics?time_range=${timeRange}`);
            
            if (response.success) {
                this.updateCharts(response.data);
            }
        } catch (error) {
            console.error('更新图表数据失败:', error);
        }
    }

    /**
     * 查看节点详情
     */
    async viewNodeDetails(nodeId) {
        try {
            const node = this.nodes.find(n => n.node_id === nodeId);
            if (!node) return;

            // 获取详细信息
            const response = await API.get(`/api/cluster/nodes/${nodeId}`);
            
            if (response.success) {
                this.showNodeDetailsModal(response.data);
            } else {
                Notification.error('获取节点详情失败: ' + response.message);
            }
        } catch (error) {
            console.error('获取节点详情失败:', error);
            Notification.error('获取节点详情失败: ' + error.message);
        }
    }

    /**
     * 显示节点详情模态框
     */
    showNodeDetailsModal(nodeData) {
        const modalHtml = `
            <div class="modal fade" id="nodeDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">节点详情 - ${nodeData.hostname || nodeData.ip}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>基本信息</h6>
                                    <table class="table table-sm">
                                        <tr><td>主机名</td><td>${nodeData.hostname || '-'}</td></tr>
                                        <tr><td>IP地址</td><td>${nodeData.ip}</td></tr>
                                        <tr><td>状态</td><td>${this.getNodeStatusBadge(nodeData.status)}</td></tr>
                                        <tr><td>实例数</td><td>${nodeData.instance_count || 0}</td></tr>
                                        <tr><td>最后心跳</td><td>${nodeData.last_heartbeat ? Utils.formatDateTime(new Date(nodeData.last_heartbeat)) : '从未'}</td></tr>
                                    </table>
                                </div>
                                <div class="col-md-6">
                                    <h6>系统信息</h6>
                                    <table class="table table-sm">
                                        <tr><td>操作系统</td><td>${nodeData.os_info || '-'}</td></tr>
                                        <tr><td>CPU核心数</td><td>${nodeData.cpu_cores || '-'}</td></tr>
                                        <tr><td>总内存</td><td>${nodeData.total_memory ? Utils.formatBytes(nodeData.total_memory) : '-'}</td></tr>
                                        <tr><td>Python版本</td><td>${nodeData.python_version || '-'}</td></tr>
                                        <tr><td>Locust版本</td><td>${nodeData.locust_version || '-'}</td></tr>
                                    </table>
                                </div>
                            </div>
                            
                            ${nodeData.instances && nodeData.instances.length > 0 ? `
                                <h6 class="mt-3">运行中的实例</h6>
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>实例ID</th>
                                                <th>任务名称</th>
                                                <th>端口</th>
                                                <th>状态</th>
                                                <th>开始时间</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${nodeData.instances.map(instance => `
                                                <tr>
                                                    <td>${instance.instance_id}</td>
                                                    <td>${instance.task_name}</td>
                                                    <td>${instance.port}</td>
                                                    <td>${Utils.getStatusBadge(instance.status)}</td>
                                                    <td>${instance.start_time ? Utils.formatDateTime(new Date(instance.start_time)) : '-'}</td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : ''}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 移除已存在的模态框
        const existingModal = document.getElementById('nodeDetailsModal');
        if (existingModal) {
            existingModal.remove();
        }

        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('nodeDetailsModal'));
        modal.show();
    }

    /**
     * Ping节点
     */
    async pingNode(nodeId) {
        try {
            Loading.show('正在Ping节点...');
            
            const response = await API.post(`/api/cluster/nodes/${nodeId}/ping`);
            
            if (response.success) {
                Notification.success(`节点响应时间: ${response.data.response_time}ms`);
            } else {
                Notification.error('Ping节点失败: ' + response.message);
            }
        } catch (error) {
            console.error('Ping节点失败:', error);
            Notification.error('Ping节点失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 移除节点
     */
    async removeNode(nodeId) {
        const confirmed = await ConfirmDialog.show(
            '确认移除节点',
            '确定要从集群中移除这个节点吗？此操作不可撤销。',
            'danger'
        );

        if (!confirmed) return;

        try {
            Loading.show('正在移除节点...');
            
            const response = await API.delete(`/api/cluster/nodes/${nodeId}`);
            
            if (response.success) {
                Notification.success('节点已移除');
                this.loadClusterData();
            } else {
                Notification.error('移除节点失败: ' + response.message);
            }
        } catch (error) {
            console.error('移除节点失败:', error);
            Notification.error('移除节点失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 清理集群
     */
    async cleanupCluster() {
        const confirmed = await ConfirmDialog.show(
            '确认清理集群',
            '这将移除所有离线节点和无效实例。确定要继续吗？',
            'warning'
        );

        if (!confirmed) return;

        try {
            Loading.show('正在清理集群...');
            
            const response = await API.post('/api/cluster/cleanup');
            
            if (response.success) {
                Notification.success('集群清理完成');
                this.loadClusterData();
            } else {
                Notification.error('集群清理失败: ' + response.message);
            }
        } catch (error) {
            console.error('集群清理失败:', error);
            Notification.error('集群清理失败: ' + error.message);
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
            this.loadClusterData();
        }, 10000); // 10秒刷新一次
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
     * 销毁集群管理器
     */
    destroy() {
        this.stopAutoRefresh();
        
        // 销毁图表
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在集群管理页面
    if (document.body.dataset.page === 'cluster') {
        window.clusterManager = new ClusterManager();
    }
});

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    if (window.clusterManager) {
        window.clusterManager.destroy();
    }
});