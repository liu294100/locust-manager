-- 压测服务管理器数据库初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS locust_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE locust_manager;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role ENUM('admin', 'user') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 压测任务表
CREATE TABLE IF NOT EXISTS test_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    script_file VARCHAR(255) NOT NULL,
    target_host VARCHAR(255),
    users INT DEFAULT 1,
    spawn_rate DECIMAL(10,2) DEFAULT 1.0,
    run_time INT,  -- 运行时间（秒）
    status ENUM('pending', 'running', 'completed', 'failed', 'stopped') DEFAULT 'pending',
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    cluster_mode BOOLEAN DEFAULT FALSE,
    node_count INT DEFAULT 1,
    description TEXT,
    INDEX idx_status (status),
    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 压测实例表
CREATE TABLE IF NOT EXISTS test_instances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instance_id VARCHAR(50) NOT NULL UNIQUE,
    task_id INT,
    node_id VARCHAR(50),
    port INT,
    pid INT,
    status ENUM('starting', 'running', 'stopping', 'stopped', 'failed') DEFAULT 'starting',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    stopped_at TIMESTAMP NULL,
    last_heartbeat TIMESTAMP NULL,
    INDEX idx_instance_id (instance_id),
    INDEX idx_task_id (task_id),
    INDEX idx_node_id (node_id),
    INDEX idx_status (status),
    FOREIGN KEY (task_id) REFERENCES test_tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 压测结果表
CREATE TABLE IF NOT EXISTS test_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT,
    instance_id VARCHAR(50),
    request_method VARCHAR(10),
    request_name VARCHAR(255),
    num_requests INT DEFAULT 0,
    num_failures INT DEFAULT 0,
    median_response_time DECIMAL(10,2) DEFAULT 0,
    average_response_time DECIMAL(10,2) DEFAULT 0,
    min_response_time DECIMAL(10,2) DEFAULT 0,
    max_response_time DECIMAL(10,2) DEFAULT 0,
    average_content_size DECIMAL(10,2) DEFAULT 0,
    requests_per_second DECIMAL(10,2) DEFAULT 0,
    failures_per_second DECIMAL(10,2) DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_instance_id (instance_id),
    INDEX idx_recorded_at (recorded_at),
    FOREIGN KEY (task_id) REFERENCES test_tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 集群节点表
CREATE TABLE IF NOT EXISTS cluster_nodes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    node_id VARCHAR(50) NOT NULL UNIQUE,
    node_name VARCHAR(100),
    ip_address VARCHAR(45),
    port INT,
    status ENUM('online', 'offline', 'maintenance') DEFAULT 'offline',
    cpu_usage DECIMAL(5,2) DEFAULT 0,
    memory_usage DECIMAL(5,2) DEFAULT 0,
    active_instances INT DEFAULT 0,
    max_instances INT DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP NULL,
    metadata JSON,
    INDEX idx_node_id (node_id),
    INDEX idx_status (status),
    INDEX idx_last_heartbeat (last_heartbeat)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') DEFAULT 'INFO',
    message TEXT NOT NULL,
    module VARCHAR(50),
    function_name VARCHAR(100),
    line_number INT,
    user_id INT,
    task_id INT,
    instance_id VARCHAR(50),
    node_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extra_data JSON,
    INDEX idx_level (level),
    INDEX idx_created_at (created_at),
    INDEX idx_user_id (user_id),
    INDEX idx_task_id (task_id),
    INDEX idx_node_id (node_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (task_id) REFERENCES test_tasks(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 文件管理表
CREATE TABLE IF NOT EXISTS script_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT DEFAULT 0,
    file_hash VARCHAR(64),
    uploaded_by INT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    INDEX idx_filename (filename),
    INDEX idx_uploaded_by (uploaded_by),
    INDEX idx_uploaded_at (uploaded_at),
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认管理员用户
-- 密码: admin123 (使用SHA-256哈希)
INSERT INTO users (username, password_hash, email, role) VALUES 
('admin', 'SHA2(CONCAT("admin123", "locust-manager-salt"), 256)', 'admin@locust-manager.com', 'admin')
ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash);

-- 创建视图：活跃任务统计
CREATE OR REPLACE VIEW active_tasks_summary AS
SELECT 
    COUNT(*) as total_tasks,
    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_tasks,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_tasks,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks
FROM test_tasks 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR);

-- 创建视图：集群状态统计
CREATE OR REPLACE VIEW cluster_status_summary AS
SELECT 
    COUNT(*) as total_nodes,
    SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online_nodes,
    SUM(CASE WHEN status = 'offline' THEN 1 ELSE 0 END) as offline_nodes,
    SUM(active_instances) as total_instances,
    AVG(cpu_usage) as avg_cpu_usage,
    AVG(memory_usage) as avg_memory_usage
FROM cluster_nodes;