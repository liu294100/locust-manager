/**
 * 仪表板页面JavaScript
 * 处理统计数据刷新、图表更新等功能
 */

class Dashboard {
    constructor() {
        this.refreshInterval = null;
        this.charts = {};
        this.init();
    }

    /**
     * 初始化仪表板
     */
    init() {
        this.bindEvents();
        this.initCharts();
        this.loadData();
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
                this.loadData();
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

        // 时间范围选择
        const timeRangeSelect = document.getElementById('time-range-select');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', () => {
                this.loadChartData();
            });
        }
    }

    /**
     * 初始化图表
     */
    initCharts() {
        // 任务状态分布饼图
        this.initTaskStatusChart();
        
        // 系统性能趋势图
        this.initPerformanceChart();
        
        // 实例状态图
        this.initInstanceChart();
    }

    /**
     * 初始化任务状态图表
     */
    initTaskStatusChart() {
        const ctx = document.getElementById('task-status-chart');
        if (!ctx) return;

        this.charts.taskStatus = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['运行中', '已停止', '等待中', '失败'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        CONFIG.chartColors.success,
                        CONFIG.chartColors.secondary,
                        CONFIG.chartColors.warning,
                        CONFIG.chartColors.danger
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
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

    /**
     * 初始化性能图表
     */
    initPerformanceChart() {
        const ctx = document.getElementById('performance-chart');
        if (!ctx) return;

        this.charts.performance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU使用率 (%)',
                        data: [],
                        borderColor: CONFIG.chartColors.primary,
                        backgroundColor: CONFIG.chartColors.primary + '20',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: '内存使用率 (%)',
                        data: [],
                        borderColor: CONFIG.chartColors.success,
                        backgroundColor: CONFIG.chartColors.success + '20',
                        tension: 0.4,
                        fill: true
                    }
                ]
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
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    /**
     * 初始化实例图表
     */
    initInstanceChart() {
        const ctx = document.getElementById('instance-chart');
        if (!ctx) return;

        this.charts.instance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: '实例数量',
                    data: [],
                    backgroundColor: CONFIG.chartColors.info,
                    borderColor: CONFIG.chartColors.info,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    /**
     * 加载数据
     */
    async loadData() {
        try {
            Loading.show('加载仪表板数据...');
            
            // 并行加载所有数据
            const [statsData, tasksData, instancesData] = await Promise.all([
                this.loadStats(),
                this.loadTasks(),
                this.loadInstances()
            ]);

            // 更新统计卡片
            this.updateStatsCards(statsData);
            
            // 更新任务列表
            this.updateRecentTasks(tasksData);
            
            // 更新实例列表
            this.updateActiveInstances(instancesData);
            
            // 更新图表
            this.updateCharts(statsData, tasksData, instancesData);
            
            // 更新最后刷新时间
            this.updateLastRefreshTime();
            
        } catch (error) {
            console.error('加载仪表板数据失败:', error);
            Notification.error('加载数据失败: ' + error.message);
        } finally {
            Loading.hide();
        }
    }

    /**
     * 加载统计数据
     */
    async loadStats() {
        return await API.get('/api/dashboard/stats');
    }

    /**
     * 加载任务数据
     */
    async loadTasks() {
        return await API.get('/api/tasks', { limit: 10, sort: 'created_at', order: 'desc' });
    }

    /**
     * 加载实例数据
     */
    async loadInstances() {
        return await API.get('/api/instances', { status: 'running' });
    }

    /**
     * 更新统计卡片
     */
    updateStatsCards(data) {
        const cards = {
            'total-tasks': data.total_tasks || 0,
            'running-instances': data.running_instances || 0,
            'script-files': data.script_files || 0,
            'test-results': data.test_results || 0
        };

        Object.entries(cards).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                // 添加数字动画效果
                this.animateNumber(element, parseInt(element.textContent) || 0, value);
            }
        });

        // 更新集群状态（如果启用）
        if (data.cluster_enabled) {
            this.updateClusterStatus(data.cluster_stats);
        }
    }

    /**
     * 数字动画效果
     */
    animateNumber(element, start, end, duration = 1000) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                current = end;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current);
        }, 16);
    }

    /**
     * 更新最近任务
     */
    updateRecentTasks(data) {
        const container = document.getElementById('recent-tasks-list');
        if (!container || !data.tasks) return;

        container.innerHTML = '';

        if (data.tasks.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-3">暂无任务</div>';
            return;
        }

        data.tasks.forEach(task => {
            const taskElement = document.createElement('div');
            taskElement.className = 'list-group-item list-group-item-action';
            taskElement.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${task.name}</h6>
                    <small>${Utils.formatDateTime(task.created_at)}</small>
                </div>
                <div class="d-flex w-100 justify-content-between align-items-center">
                    <p class="mb-1 text-muted">${task.script_name}</p>
                    ${Utils.getStatusBadge(task.status)}
                </div>
            `;
            
            taskElement.addEventListener('click', () => {
                window.location.href = `/tasks/${task.id}`;
            });
            
            container.appendChild(taskElement);
        });
    }

    /**
     * 更新活跃实例
     */
    updateActiveInstances(data) {
        const container = document.getElementById('active-instances-list');
        if (!container || !data.instances) return;

        container.innerHTML = '';

        if (data.instances.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-3">暂无运行实例</div>';
            return;
        }

        data.instances.forEach(instance => {
            const instanceElement = document.createElement('div');
            instanceElement.className = 'list-group-item';
            instanceElement.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${instance.task_name}</h6>
                    <small>端口: ${instance.port}</small>
                </div>
                <div class="d-flex w-100 justify-content-between align-items-center">
                    <p class="mb-1 text-muted">${instance.node || 'localhost'}</p>
                    <div class="d-flex gap-2">
                        <span class="badge bg-info">CPU: ${instance.cpu_usage || 0}%</span>
                        <span class="badge bg-success">内存: ${instance.memory_usage || 0}%</span>
                    </div>
                </div>
            `;
            container.appendChild(instanceElement);
        });
    }

    /**
     * 更新图表
     */
    updateCharts(statsData, tasksData, instancesData) {
        // 更新任务状态图表
        if (this.charts.taskStatus && statsData.task_status) {
            const statusData = [
                statsData.task_status.running || 0,
                statsData.task_status.stopped || 0,
                statsData.task_status.pending || 0,
                statsData.task_status.failed || 0
            ];
            this.charts.taskStatus.data.datasets[0].data = statusData;
            this.charts.taskStatus.update();
        }

        // 更新实例图表
        if (this.charts.instance && instancesData.node_stats) {
            const nodeLabels = Object.keys(instancesData.node_stats);
            const nodeData = Object.values(instancesData.node_stats);
            
            this.charts.instance.data.labels = nodeLabels;
            this.charts.instance.data.datasets[0].data = nodeData;
            this.charts.instance.update();
        }

        // 加载性能图表数据
        this.loadChartData();
    }

    /**
     * 加载图表数据
     */
    async loadChartData() {
        try {
            const timeRange = document.getElementById('time-range-select')?.value || '1h';
            const data = await API.get('/api/dashboard/performance', { range: timeRange });
            
            if (this.charts.performance && data.performance) {
                const labels = data.performance.map(item => new Date(item.timestamp));
                const cpuData = data.performance.map(item => item.cpu_usage);
                const memoryData = data.performance.map(item => item.memory_usage);
                
                this.charts.performance.data.labels = labels;
                this.charts.performance.data.datasets[0].data = cpuData;
                this.charts.performance.data.datasets[1].data = memoryData;
                this.charts.performance.update();
            }
        } catch (error) {
            console.error('加载图表数据失败:', error);
        }
    }

    /**
     * 更新集群状态
     */
    updateClusterStatus(clusterStats) {
        const clusterSection = document.getElementById('cluster-status-section');
        if (!clusterSection || !clusterStats) return;

        clusterSection.style.display = 'block';
        
        // 更新集群统计
        const elements = {
            'cluster-total-nodes': clusterStats.total_nodes || 0,
            'cluster-active-nodes': clusterStats.active_nodes || 0,
            'cluster-total-instances': clusterStats.total_instances || 0
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    /**
     * 更新最后刷新时间
     */
    updateLastRefreshTime() {
        const element = document.getElementById('last-refresh-time');
        if (element) {
            element.textContent = new Date().toLocaleTimeString('zh-CN');
        }
    }

    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => {
            this.loadData();
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
     * 销毁仪表板
     */
    destroy() {
        this.stopAutoRefresh();
        
        // 销毁图表
        Object.values(this.charts).forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });
        
        this.charts = {};
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在仪表板页面
    if (document.body.dataset.page === 'dashboard') {
        window.dashboard = new Dashboard();
    }
});

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
});