/**
 * Locust Manager 主要JavaScript文件
 * 包含通用功能和工具函数
 */

// 全局配置
const CONFIG = {
    refreshInterval: 5000, // 5秒刷新间隔
    chartColors: {
        primary: '#007bff',
        success: '#28a745',
        danger: '#dc3545',
        warning: '#ffc107',
        info: '#17a2b8',
        secondary: '#6c757d'
    },
    apiEndpoints: {
        tasks: '/api/tasks',
        instances: '/api/instances',
        scripts: '/api/scripts',
        cluster: '/api/cluster',
        stats: '/api/stats'
    }
};

// 工具函数
const Utils = {
    /**
     * 格式化字节大小
     */
    formatBytes: function(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    },

    /**
     * 格式化持续时间
     */
    formatDuration: function(seconds) {
        if (!seconds || seconds < 0) return '0s';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    },

    /**
     * 格式化日期时间
     */
    formatDateTime: function(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },

    /**
     * 格式化数字
     */
    formatNumber: function(num, decimals = 0) {
        if (num === null || num === undefined) return '-';
        return Number(num).toLocaleString('zh-CN', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    },

    /**
     * 获取状态徽章HTML
     */
    getStatusBadge: function(status) {
        const statusMap = {
            'running': { class: 'success', icon: 'play', text: '运行中' },
            'stopped': { class: 'secondary', icon: 'stop', text: '已停止' },
            'pending': { class: 'warning', icon: 'clock', text: '等待中' },
            'failed': { class: 'danger', icon: 'exclamation-triangle', text: '失败' },
            'completed': { class: 'info', icon: 'check', text: '已完成' }
        };
        
        const config = statusMap[status] || { class: 'secondary', icon: 'question', text: status };
        return `<span class="badge bg-${config.class} status-badge">
                    <i class="fas fa-${config.icon}"></i> ${config.text}
                </span>`;
    },

    /**
     * 防抖函数
     */
    debounce: function(func, wait, immediate) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func(...args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func(...args);
        };
    },

    /**
     * 节流函数
     */
    throttle: function(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// API请求封装
const API = {
    /**
     * 发送GET请求
     */
    get: async function(url, params = {}) {
        try {
            const urlParams = new URLSearchParams(params);
            const response = await fetch(`${url}?${urlParams}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API GET Error:', error);
            throw error;
        }
    },

    /**
     * 发送POST请求
     */
    post: async function(url, data = {}) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API POST Error:', error);
            throw error;
        }
    },

    /**
     * 发送PUT请求
     */
    put: async function(url, data = {}) {
        try {
            const response = await fetch(url, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API PUT Error:', error);
            throw error;
        }
    },

    /**
     * 发送DELETE请求
     */
    delete: async function(url) {
        try {
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API DELETE Error:', error);
            throw error;
        }
    }
};

// 通知系统
const Notification = {
    /**
     * 显示成功消息
     */
    success: function(message, duration = 3000) {
        this.show(message, 'success', duration);
    },

    /**
     * 显示错误消息
     */
    error: function(message, duration = 5000) {
        this.show(message, 'danger', duration);
    },

    /**
     * 显示警告消息
     */
    warning: function(message, duration = 4000) {
        this.show(message, 'warning', duration);
    },

    /**
     * 显示信息消息
     */
    info: function(message, duration = 3000) {
        this.show(message, 'info', duration);
    },

    /**
     * 显示通知
     */
    show: function(message, type = 'info', duration = 3000) {
        // 创建通知容器（如果不存在）
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }

        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show mb-2`;
        notification.style.cssText = 'animation: slideInRight 0.3s ease-out;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // 添加到容器
        container.appendChild(notification);

        // 自动移除
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.style.animation = 'slideOutRight 0.3s ease-in';
                    setTimeout(() => {
                        if (notification.parentNode) {
                            notification.remove();
                        }
                    }, 300);
                }
            }, duration);
        }
    }
};

// 加载指示器
const Loading = {
    /**
     * 显示全屏加载
     */
    show: function(message = '加载中...') {
        // 移除现有的加载层
        this.hide();
        
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="text-center text-white">
                <div class="loading-spinner mb-3"></div>
                <div>${message}</div>
            </div>
        `;
        
        document.body.appendChild(overlay);
    },

    /**
     * 隐藏全屏加载
     */
    hide: function() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    },

    /**
     * 显示按钮加载状态
     */
    button: function(button, loading = true) {
        if (loading) {
            button.disabled = true;
            button.dataset.originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
        } else {
            button.disabled = false;
            button.innerHTML = button.dataset.originalText || button.innerHTML;
        }
    }
};

// 确认对话框
const Confirm = {
    /**
     * 显示确认对话框
     */
    show: function(message, title = '确认操作', onConfirm = null, onCancel = null) {
        return new Promise((resolve) => {
            // 创建模态框
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'confirm-modal';
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" id="confirm-btn">确认</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            const bsModal = new bootstrap.Modal(modal);
            
            // 绑定事件
            modal.querySelector('#confirm-btn').addEventListener('click', () => {
                bsModal.hide();
                resolve(true);
                if (onConfirm) onConfirm();
            });
            
            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
                resolve(false);
                if (onCancel) onCancel();
            });
            
            bsModal.show();
        });
    }
};

// 表格工具
const Table = {
    /**
     * 初始化数据表格
     */
    init: function(tableId, options = {}) {
        const table = document.getElementById(tableId);
        if (!table) return;

        // 默认选项
        const defaultOptions = {
            sortable: true,
            searchable: true,
            pagination: true,
            pageSize: 10
        };

        const config = { ...defaultOptions, ...options };

        // 添加搜索功能
        if (config.searchable) {
            this.addSearch(table);
        }

        // 添加排序功能
        if (config.sortable) {
            this.addSort(table);
        }

        // 添加分页功能
        if (config.pagination) {
            this.addPagination(table, config.pageSize);
        }
    },

    /**
     * 添加搜索功能
     */
    addSearch: function(table) {
        const searchInput = table.parentElement.querySelector('.table-search');
        if (!searchInput) return;

        searchInput.addEventListener('input', Utils.debounce((e) => {
            const searchTerm = e.target.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        }, 300));
    },

    /**
     * 添加排序功能
     */
    addSort: function(table) {
        const headers = table.querySelectorAll('thead th[data-sort]');
        
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.innerHTML += ' <i class="fas fa-sort text-muted"></i>';
            
            header.addEventListener('click', () => {
                const column = header.dataset.sort;
                const currentOrder = header.dataset.order || 'asc';
                const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
                
                // 重置其他列的排序图标
                headers.forEach(h => {
                    if (h !== header) {
                        h.dataset.order = '';
                        h.querySelector('i').className = 'fas fa-sort text-muted';
                    }
                });
                
                // 更新当前列的排序图标
                header.dataset.order = newOrder;
                header.querySelector('i').className = `fas fa-sort-${newOrder === 'asc' ? 'up' : 'down'}`;
                
                // 执行排序
                this.sortTable(table, column, newOrder);
            });
        });
    },

    /**
     * 排序表格
     */
    sortTable: function(table, column, order) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aValue = a.querySelector(`[data-value="${column}"]`)?.dataset.value || 
                          a.querySelector(`td:nth-child(${this.getColumnIndex(table, column)})`)?.textContent || '';
            const bValue = b.querySelector(`[data-value="${column}"]`)?.dataset.value || 
                          b.querySelector(`td:nth-child(${this.getColumnIndex(table, column)})`)?.textContent || '';
            
            // 尝试数字比较
            const aNum = parseFloat(aValue);
            const bNum = parseFloat(bValue);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return order === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // 字符串比较
            return order === 'asc' ? 
                aValue.localeCompare(bValue) : 
                bValue.localeCompare(aValue);
        });
        
        // 重新插入排序后的行
        rows.forEach(row => tbody.appendChild(row));
    },

    /**
     * 获取列索引
     */
    getColumnIndex: function(table, column) {
        const headers = table.querySelectorAll('thead th');
        for (let i = 0; i < headers.length; i++) {
            if (headers[i].dataset.sort === column) {
                return i + 1;
            }
        }
        return 1;
    },

    /**
     * 添加分页功能
     */
    addPagination: function(table, pageSize) {
        // 分页功能实现（简化版）
        const rows = table.querySelectorAll('tbody tr');
        const totalPages = Math.ceil(rows.length / pageSize);
        let currentPage = 1;

        const showPage = (page) => {
            const start = (page - 1) * pageSize;
            const end = start + pageSize;
            
            rows.forEach((row, index) => {
                row.style.display = (index >= start && index < end) ? '' : 'none';
            });
        };

        // 初始显示第一页
        showPage(1);
        
        // 这里可以添加分页控件的创建和事件绑定
    }
};

// 图表工具
const Charts = {
    /**
     * 创建线性图表
     */
    createLineChart: function(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                }
            }
        };

        return new Chart(ctx, {
            type: 'line',
            data: data,
            options: { ...defaultOptions, ...options }
        });
    },

    /**
     * 创建饼图
     */
    createPieChart: function(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        };

        return new Chart(ctx, {
            type: 'pie',
            data: data,
            options: { ...defaultOptions, ...options }
        });
    },

    /**
     * 创建柱状图
     */
    createBarChart: function(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        };

        return new Chart(ctx, {
            type: 'bar',
            data: data,
            options: { ...defaultOptions, ...options }
        });
    }
};

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化弹出框
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // 侧边栏切换
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');

    if (sidebarToggle && sidebar && mainContent) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('sidebar-collapsed');
        });
    }

    // 自动隐藏消息提示
    const alerts = document.querySelectorAll('.alert[data-auto-dismiss]');
    alerts.forEach(alert => {
        const delay = parseInt(alert.dataset.autoHide) || 5000;
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, delay);
    });

    // 表单验证增强
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // 初始化数据表格
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(table => {
        Table.init(table.id);
    });

    console.log('Locust Manager 初始化完成');
});

// 导出全局对象
window.LocustManager = {
    Utils,
    API,
    Notification,
    Loading,
    Confirm,
    Table,
    Charts,
    CONFIG
};