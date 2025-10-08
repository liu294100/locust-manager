# Locust Manager

一个基于 Flask 的 Locust 负载测试管理平台，提供 Web 界面来管理和监控 Locust 测试任务。

## 🚀 功能特性

### 核心功能
- **任务管理**: 创建、编辑、启动、停止和删除负载测试任务
- **脚本管理**: 上传、编辑和管理 Locust 测试脚本
- **实例监控**: 实时监控测试实例的状态和性能
- **集群管理**: 支持多节点集群部署和管理
- **数据可视化**: 丰富的图表展示测试结果和性能指标

### 界面特性
- 现代化的响应式 Web 界面
- 实时数据更新和状态监控
- 直观的拖拽文件上传
- 丰富的过滤和搜索功能
- 详细的日志查看和分析

### 技术特性
- 支持 Docker 容器化部署
- 支持 Kubernetes 集群部署
- RESTful API 接口
- 数据库持久化存储
- Redis 缓存支持
- 完整的错误处理和日志记录

## 📋 系统要求

### 基础要求
- Python 3.8+
- MySQL 5.7+ 或 MariaDB 10.3+
- Redis 5.0+

### 可选要求
- Docker 20.0+
- Kubernetes 1.20+
- Nginx (用于反向代理)

## 🛠️ 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/your-username/locust-manager.git
cd locust-manager
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库和 Redis 连接信息
```

### 4. 初始化数据库
```bash
python manage.py init-db
```

### 5. 启动应用
```bash
python app.py
```

访问 http://localhost:5000 即可使用。

## 🐳 Docker 部署

### 使用 Docker Compose (推荐)
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f locust-manager
```

### 单独构建镜像
```bash
# 构建镜像
docker build -t locust-manager .

# 运行容器
docker run -d \
  --name locust-manager \
  -p 5000:5000 \
  -e DATABASE_URL=mysql://user:password@host:3306/locust_manager \
  -e REDIS_URL=redis://host:6379/0 \
  locust-manager
```

## ☸️ Kubernetes 部署

### 1. 创建命名空间和配置
```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. 部署存储
```bash
kubectl apply -f k8s/storage.yaml
```

### 3. 部署 RBAC
```bash
kubectl apply -f k8s/rbac.yaml
```

### 4. 部署应用
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### 5. 使用部署脚本 (推荐)
```bash
# 安装
./k8s/deploy.sh install

# 升级
./k8s/deploy.sh upgrade

# 卸载
./k8s/deploy.sh uninstall

# 查看状态
./k8s/deploy.sh status
```

## 📖 使用指南

### 创建测试任务
1. 进入"任务管理"页面
2. 点击"创建任务"按钮
3. 填写任务基本信息
4. 选择测试脚本
5. 配置负载测试参数
6. 保存并启动任务

### 上传测试脚本
1. 进入"脚本管理"页面
2. 点击"上传脚本"按钮
3. 拖拽或选择 Python 脚本文件
4. 填写脚本描述信息
5. 系统会自动验证脚本格式
6. 确认上传

### 监控测试实例
1. 进入"实例管理"页面
2. 查看所有运行中的测试实例
3. 可以查看实例日志、性能指标
4. 支持批量操作和过滤搜索

### 集群管理
1. 进入"集群状态"页面
2. 查看集群节点状态
3. 监控资源使用情况
4. 管理节点和实例分布

## 🔧 配置说明

### 环境变量
| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `FLASK_ENV` | Flask 运行环境 | `production` |
| `SECRET_KEY` | Flask 密钥 | 随机生成 |
| `DATABASE_URL` | 数据库连接 URL | - |
| `REDIS_URL` | Redis 连接 URL | - |
| `UPLOAD_FOLDER` | 文件上传目录 | `uploads` |
| `SCRIPTS_FOLDER` | 脚本存储目录 | `scripts` |
| `LOGS_FOLDER` | 日志存储目录 | `logs` |
| `CLUSTER_ENABLED` | 是否启用集群模式 | `false` |

### 数据库配置
支持 MySQL 和 MariaDB，推荐配置：
```sql
CREATE DATABASE locust_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'locust_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON locust_manager.* TO 'locust_user'@'%';
FLUSH PRIVILEGES;
```

## 📚 API 文档

### 认证
目前支持基于 Session 的认证，后续版本将支持 JWT Token。

### 主要接口

#### 任务管理
- `GET /api/tasks` - 获取任务列表
- `POST /api/tasks` - 创建新任务
- `GET /api/tasks/{id}` - 获取任务详情
- `PUT /api/tasks/{id}` - 更新任务
- `DELETE /api/tasks/{id}` - 删除任务
- `POST /api/tasks/{id}/start` - 启动任务
- `POST /api/tasks/{id}/stop` - 停止任务

#### 脚本管理
- `GET /api/scripts` - 获取脚本列表
- `POST /api/scripts/upload` - 上传脚本
- `GET /api/scripts/{id}` - 获取脚本内容
- `PUT /api/scripts/{id}` - 更新脚本
- `DELETE /api/scripts/{id}` - 删除脚本

#### 实例管理
- `GET /api/instances` - 获取实例列表
- `GET /api/instances/{id}` - 获取实例详情
- `POST /api/instances/{id}/stop` - 停止实例
- `DELETE /api/instances/{id}` - 删除实例
- `GET /api/instances/{id}/logs` - 获取实例日志

#### 集群管理
- `GET /api/cluster/status` - 获取集群状态
- `GET /api/cluster/nodes` - 获取节点列表
- `GET /api/cluster/nodes/{id}` - 获取节点详情
- `DELETE /api/cluster/nodes/{id}` - 移除节点
- `POST /api/cluster/cleanup` - 清理集群

详细的 API 文档请参考 [API.md](docs/API.md)。

## 🔍 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库服务状态
systemctl status mysql

# 检查连接配置
mysql -h host -u user -p database_name
```

#### 2. Redis 连接失败
```bash
# 检查 Redis 服务状态
systemctl status redis

# 测试连接
redis-cli -h host -p port ping
```

#### 3. 文件上传失败
- 检查上传目录权限
- 确认文件大小限制
- 验证文件格式

#### 4. 任务启动失败
- 检查脚本语法
- 确认 Locust 版本兼容性
- 查看详细错误日志

### 日志查看
```bash
# Docker 环境
docker-compose logs -f locust-manager

# Kubernetes 环境
kubectl logs -f deployment/locust-manager -n locust-manager

# 本地环境
tail -f logs/app.log
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 开发环境设置
1. Fork 项目
2. 创建功能分支
3. 安装开发依赖：`pip install -r requirements-dev.txt`
4. 运行测试：`pytest`
5. 提交更改
6. 创建 Pull Request

### 代码规范
- 遵循 PEP 8 代码风格
- 添加适当的注释和文档
- 编写单元测试
- 确保所有测试通过

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [Locust](https://locust.io/) - 优秀的负载测试框架
- [Flask](https://flask.palletsprojects.com/) - 轻量级 Web 框架
- [Bootstrap](https://getbootstrap.com/) - 前端 UI 框架
- [Chart.js](https://www.chartjs.org/) - 图表库

## 📞 联系我们

- 项目主页: https://github.com/your-username/locust-manager
- 问题反馈: https://github.com/your-username/locust-manager/issues
- 邮箱: your-email@example.com

---

如果这个项目对你有帮助，请给我们一个 ⭐️！
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```
