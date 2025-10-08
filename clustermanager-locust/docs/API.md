# Locust Manager API 文档

本文档详细描述了 Locust Manager 的所有 API 接口。

## 基础信息

- **Base URL**: `http://localhost:5000/api`
- **认证方式**: Session-based (Cookie)
- **数据格式**: JSON
- **字符编码**: UTF-8

## 通用响应格式

### 成功响应
```json
{
  "success": true,
  "data": {},
  "message": "操作成功"
}
```

### 错误响应
```json
{
  "success": false,
  "error": "错误信息",
  "code": "ERROR_CODE"
}
```

## 状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 任务管理 API

### 获取任务列表

**GET** `/api/tasks`

#### 查询参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| per_page | int | 否 | 每页数量，默认 20 |
| status | string | 否 | 任务状态过滤 |
| search | string | 否 | 搜索关键词 |
| creator | string | 否 | 创建者过滤 |

#### 响应示例
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "id": 1,
        "name": "API 压力测试",
        "description": "测试 API 接口性能",
        "script_id": 1,
        "script_name": "api_test.py",
        "status": "running",
        "creator": "admin",
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:30:00Z",
        "config": {
          "users": 100,
          "spawn_rate": 10,
          "run_time": "5m",
          "host": "https://api.example.com"
        },
        "stats": {
          "total_requests": 1500,
          "failed_requests": 5,
          "avg_response_time": 120.5,
          "rps": 25.3
        }
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 50,
      "pages": 3
    }
  }
}
```

### 创建任务

**POST** `/api/tasks`

#### 请求体
```json
{
  "name": "新测试任务",
  "description": "任务描述",
  "script_id": 1,
  "config": {
    "users": 100,
    "spawn_rate": 10,
    "run_time": "5m",
    "host": "https://api.example.com",
    "tags": ["api", "performance"]
  }
}
```

#### 响应示例
```json
{
  "success": true,
  "data": {
    "id": 2,
    "name": "新测试任务",
    "status": "created"
  },
  "message": "任务创建成功"
}
```

### 获取任务详情

**GET** `/api/tasks/{id}`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "API 压力测试",
    "description": "测试 API 接口性能",
    "script_id": 1,
    "script_name": "api_test.py",
    "script_content": "from locust import HttpUser, task...",
    "status": "running",
    "creator": "admin",
    "created_at": "2024-01-01T10:00:00Z",
    "started_at": "2024-01-01T10:05:00Z",
    "config": {
      "users": 100,
      "spawn_rate": 10,
      "run_time": "5m",
      "host": "https://api.example.com"
    },
    "instances": [
      {
        "id": "inst_001",
        "status": "running",
        "node": "node-1",
        "users": 50,
        "rps": 12.5
      }
    ],
    "stats": {
      "total_requests": 1500,
      "failed_requests": 5,
      "avg_response_time": 120.5,
      "min_response_time": 45,
      "max_response_time": 850,
      "rps": 25.3,
      "failure_rate": 0.33
    }
  }
}
```

### 更新任务

**PUT** `/api/tasks/{id}`

#### 请求体
```json
{
  "name": "更新后的任务名称",
  "description": "更新后的描述",
  "config": {
    "users": 200,
    "spawn_rate": 20
  }
}
```

### 删除任务

**DELETE** `/api/tasks/{id}`

#### 响应示例
```json
{
  "success": true,
  "message": "任务删除成功"
}
```

### 启动任务

**POST** `/api/tasks/{id}/start`

#### 请求体（可选）
```json
{
  "config": {
    "users": 150,
    "spawn_rate": 15
  }
}
```

#### 响应示例
```json
{
  "success": true,
  "data": {
    "task_id": 1,
    "status": "starting",
    "instances": ["inst_001", "inst_002"]
  },
  "message": "任务启动成功"
}
```

### 停止任务

**POST** `/api/tasks/{id}/stop`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "task_id": 1,
    "status": "stopping"
  },
  "message": "任务停止中"
}
```

### 克隆任务

**POST** `/api/tasks/{id}/clone`

#### 请求体
```json
{
  "name": "克隆的任务"
}
```

## 脚本管理 API

### 获取脚本列表

**GET** `/api/scripts`

#### 查询参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| per_page | int | 否 | 每页数量，默认 20 |
| search | string | 否 | 搜索关键词 |
| creator | string | 否 | 创建者过滤 |

#### 响应示例
```json
{
  "success": true,
  "data": {
    "scripts": [
      {
        "id": 1,
        "name": "api_test.py",
        "description": "API 接口测试脚本",
        "creator": "admin",
        "created_at": "2024-01-01T09:00:00Z",
        "updated_at": "2024-01-01T09:30:00Z",
        "size": 2048,
        "is_valid": true,
        "validation_errors": []
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 10,
      "pages": 1
    }
  }
}
```

### 上传脚本

**POST** `/api/scripts/upload`

#### 请求体（multipart/form-data）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | Python 脚本文件 |
| description | string | 否 | 脚本描述 |

#### 响应示例
```json
{
  "success": true,
  "data": {
    "id": 2,
    "name": "new_script.py",
    "size": 1024,
    "is_valid": true
  },
  "message": "脚本上传成功"
}
```

### 获取脚本内容

**GET** `/api/scripts/{id}`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "api_test.py",
    "description": "API 接口测试脚本",
    "content": "from locust import HttpUser, task\n\nclass ApiUser(HttpUser):\n    @task\n    def test_api(self):\n        self.client.get('/api/test')",
    "creator": "admin",
    "created_at": "2024-01-01T09:00:00Z",
    "size": 2048,
    "is_valid": true,
    "validation_errors": []
  }
}
```

### 更新脚本

**PUT** `/api/scripts/{id}`

#### 请求体
```json
{
  "description": "更新后的描述",
  "content": "from locust import HttpUser, task..."
}
```

### 删除脚本

**DELETE** `/api/scripts/{id}`

### 验证脚本

**POST** `/api/scripts/{id}/validate`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "is_valid": true,
    "errors": [],
    "warnings": [
      "建议添加更多的任务方法"
    ]
  }
}
```

## 实例管理 API

### 获取实例列表

**GET** `/api/instances`

#### 查询参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 实例状态过滤 |
| task_id | int | 否 | 任务 ID 过滤 |
| node | string | 否 | 节点过滤 |

#### 响应示例
```json
{
  "success": true,
  "data": {
    "instances": [
      {
        "id": "inst_001",
        "task_id": 1,
        "task_name": "API 压力测试",
        "status": "running",
        "node": "node-1",
        "created_at": "2024-01-01T10:05:00Z",
        "started_at": "2024-01-01T10:06:00Z",
        "config": {
          "users": 50,
          "spawn_rate": 5
        },
        "stats": {
          "users": 50,
          "rps": 12.5,
          "avg_response_time": 115.2,
          "total_requests": 750,
          "failed_requests": 2
        },
        "resources": {
          "cpu_percent": 45.2,
          "memory_mb": 128,
          "memory_percent": 12.5
        }
      }
    ],
    "summary": {
      "total": 5,
      "running": 3,
      "stopped": 2,
      "failed": 0
    }
  }
}
```

### 获取实例详情

**GET** `/api/instances/{id}`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "id": "inst_001",
    "task_id": 1,
    "task_name": "API 压力测试",
    "status": "running",
    "node": "node-1",
    "created_at": "2024-01-01T10:05:00Z",
    "started_at": "2024-01-01T10:06:00Z",
    "config": {
      "users": 50,
      "spawn_rate": 5,
      "host": "https://api.example.com"
    },
    "stats": {
      "users": 50,
      "rps": 12.5,
      "avg_response_time": 115.2,
      "min_response_time": 45,
      "max_response_time": 420,
      "total_requests": 750,
      "failed_requests": 2,
      "failure_rate": 0.27
    },
    "resources": {
      "cpu_percent": 45.2,
      "memory_mb": 128,
      "memory_percent": 12.5,
      "disk_io": {
        "read_mb": 5.2,
        "write_mb": 2.1
      },
      "network_io": {
        "sent_mb": 15.3,
        "recv_mb": 8.7
      }
    }
  }
}
```

### 停止实例

**POST** `/api/instances/{id}/stop`

### 删除实例

**DELETE** `/api/instances/{id}`

### 获取实例日志

**GET** `/api/instances/{id}/logs`

#### 查询参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| lines | int | 否 | 日志行数，默认 100 |
| follow | bool | 否 | 是否实时跟踪，默认 false |

#### 响应示例
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "timestamp": "2024-01-01T10:06:15Z",
        "level": "INFO",
        "message": "Starting Locust with 50 users"
      },
      {
        "timestamp": "2024-01-01T10:06:20Z",
        "level": "INFO",
        "message": "Spawning users at rate 5.0/s"
      }
    ],
    "total_lines": 150
  }
}
```

### 批量停止实例

**POST** `/api/instances/batch/stop`

#### 请求体
```json
{
  "instance_ids": ["inst_001", "inst_002", "inst_003"]
}
```

## 集群管理 API

### 获取集群状态

**GET** `/api/cluster/status`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "overview": {
      "total_nodes": 3,
      "active_nodes": 3,
      "total_instances": 5,
      "running_instances": 3,
      "total_users": 250,
      "total_rps": 45.8
    },
    "health": {
      "status": "healthy",
      "issues": []
    },
    "resources": {
      "total_cpu_cores": 24,
      "used_cpu_cores": 8.5,
      "total_memory_gb": 64,
      "used_memory_gb": 12.3,
      "avg_load": 0.65
    }
  }
}
```

### 获取节点列表

**GET** `/api/cluster/nodes`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "node-1",
        "name": "locust-manager-node-1",
        "ip": "192.168.1.10",
        "status": "active",
        "last_heartbeat": "2024-01-01T10:30:00Z",
        "instances": 2,
        "resources": {
          "cpu_cores": 8,
          "cpu_usage": 35.2,
          "memory_gb": 16,
          "memory_usage": 4.2,
          "load_average": [0.5, 0.6, 0.7],
          "disk_usage": 45.8
        },
        "capabilities": ["master", "worker"],
        "version": "1.0.0"
      }
    ]
  }
}
```

### 获取节点详情

**GET** `/api/cluster/nodes/{id}`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "id": "node-1",
    "name": "locust-manager-node-1",
    "ip": "192.168.1.10",
    "status": "active",
    "last_heartbeat": "2024-01-01T10:30:00Z",
    "created_at": "2024-01-01T08:00:00Z",
    "instances": [
      {
        "id": "inst_001",
        "task_name": "API 压力测试",
        "status": "running",
        "users": 50
      }
    ],
    "resources": {
      "cpu_cores": 8,
      "cpu_usage": 35.2,
      "memory_gb": 16,
      "memory_usage": 4.2,
      "load_average": [0.5, 0.6, 0.7],
      "disk_usage": 45.8,
      "network_io": {
        "sent_mb_per_sec": 2.5,
        "recv_mb_per_sec": 1.8
      }
    },
    "capabilities": ["master", "worker"],
    "version": "1.0.0",
    "config": {
      "max_instances": 10,
      "max_users_per_instance": 100
    }
  }
}
```

### 移除节点

**DELETE** `/api/cluster/nodes/{id}`

#### 查询参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| force | bool | 否 | 是否强制移除，默认 false |

### 清理集群

**POST** `/api/cluster/cleanup`

#### 请求体
```json
{
  "cleanup_stopped_instances": true,
  "cleanup_failed_instances": true,
  "cleanup_orphaned_data": true
}
```

#### 响应示例
```json
{
  "success": true,
  "data": {
    "cleaned_instances": 3,
    "cleaned_data_mb": 15.2,
    "cleanup_time": "2.5s"
  },
  "message": "集群清理完成"
}
```

### Ping 节点

**POST** `/api/cluster/nodes/{id}/ping`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "node_id": "node-1",
    "response_time_ms": 15,
    "status": "active"
  }
}
```

## 统计和监控 API

### 获取仪表板数据

**GET** `/api/dashboard/stats`

#### 响应示例
```json
{
  "success": true,
  "data": {
    "overview": {
      "total_tasks": 25,
      "running_tasks": 3,
      "total_instances": 8,
      "total_users": 400,
      "total_rps": 85.6
    },
    "recent_tasks": [
      {
        "id": 1,
        "name": "API 压力测试",
        "status": "running",
        "started_at": "2024-01-01T10:00:00Z",
        "users": 100,
        "rps": 25.3
      }
    ],
    "performance": {
      "avg_response_time": 125.8,
      "success_rate": 99.2,
      "total_requests_today": 15000
    }
  }
}
```

### 获取性能指标

**GET** `/api/metrics/performance`

#### 查询参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | int | 否 | 任务 ID |
| time_range | string | 否 | 时间范围：1h, 6h, 24h, 7d |
| metrics | string | 否 | 指标类型：rps,response_time,users |

#### 响应示例
```json
{
  "success": true,
  "data": {
    "time_range": "1h",
    "interval": "1m",
    "metrics": {
      "rps": [
        {"timestamp": "2024-01-01T10:00:00Z", "value": 20.5},
        {"timestamp": "2024-01-01T10:01:00Z", "value": 22.1}
      ],
      "response_time": [
        {"timestamp": "2024-01-01T10:00:00Z", "value": 120.5},
        {"timestamp": "2024-01-01T10:01:00Z", "value": 118.2}
      ],
      "users": [
        {"timestamp": "2024-01-01T10:00:00Z", "value": 100},
        {"timestamp": "2024-01-01T10:01:00Z", "value": 100}
      ]
    }
  }
}
```

## WebSocket API

### 实时数据推送

**WebSocket** `/ws/realtime`

#### 连接参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| token | string | 是 | 认证令牌 |
| subscribe | string | 否 | 订阅类型：tasks,instances,cluster |

#### 消息格式
```json
{
  "type": "task_update",
  "data": {
    "task_id": 1,
    "status": "running",
    "stats": {
      "rps": 25.3,
      "users": 100
    }
  },
  "timestamp": "2024-01-01T10:30:00Z"
}
```

#### 消息类型
- `task_update`: 任务状态更新
- `instance_update`: 实例状态更新
- `cluster_update`: 集群状态更新
- `stats_update`: 统计数据更新

## 错误代码

| 错误代码 | 说明 |
|----------|------|
| INVALID_PARAMS | 请求参数无效 |
| RESOURCE_NOT_FOUND | 资源不存在 |
| PERMISSION_DENIED | 权限不足 |
| SCRIPT_INVALID | 脚本格式无效 |
| TASK_ALREADY_RUNNING | 任务已在运行 |
| INSTANCE_NOT_FOUND | 实例不存在 |
| NODE_UNREACHABLE | 节点不可达 |
| CLUSTER_ERROR | 集群错误 |
| DATABASE_ERROR | 数据库错误 |
| INTERNAL_ERROR | 内部服务器错误 |

## 限制说明

- API 请求频率限制：每分钟 1000 次
- 文件上传大小限制：10MB
- 脚本文件大小限制：1MB
- 单次批量操作数量限制：100 个
- WebSocket 连接数限制：每用户 5 个

## 版本信息

当前 API 版本：v1.0

版本更新历史请参考 [CHANGELOG.md](../CHANGELOG.md)。