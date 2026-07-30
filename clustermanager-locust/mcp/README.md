# Locust 压测平台 MCP Server

基于 MCP (Model Context Protocol) 的 Locust 压测平台客户端，支持通过 AI 助手管理压测脚本、启动/停止压测实例、分析压测结果。

## 📋 功能列表

### 脚本管理
| 工具名 | 描述 |
|--------|------|
| `list_scripts` | 获取所有可用的压测脚本列表 |
| `preview_script` | 预览脚本文件内容 |
| `upload_script` | 上传/创建压测脚本到临时目录 |
| `delete_script` | 删除临时目录中的脚本文件 |
| `curl_to_script` | 将 cURL 命令转换为 Locust 压测脚本 |

### 实例管理
| 工具名 | 描述 |
|--------|------|
| `list_instances` | 获取所有压测实例的状态信息 |
| `start_instance` | 启动一个新的压测实例 |
| `stop_instance` | 停止指定的压测实例 |
| `stop_all_instances` | 停止所有运行中的压测实例 |
| `remove_instance` | 删除指定的压测实例记录 |

### 结果分析
| 工具名 | 描述 |
|--------|------|
| `get_instance_stats` | 获取压测实例的原始统计数据 |
| `analyze_results` | 分析压测结果，包括汇总统计、各端点性能和优化建议 |

## 🚀 快速开始

### 1. 安装依赖

```bash
cd mcp
pip install -r requirements.txt
```

### 2. 配置 MCP

将 `mcp-config-example.json` 的内容合并到你的 MCP 配置文件中：

**Kiro 用户配置位置**: `~/.kiro/settings/mcp.json`

**工作区配置位置**: `.kiro/settings/mcp.json`

```json
{
  "mcpServers": {
    "locust-stress-test": {
      "command": "python",
      "args": ["d:/dev/code/stresstest-locust/mcp/locust_mcp_server.py"],
      "env": {
        "LOCUST_BASE_URL": "http://localhost:8088",
        "LOCUST_USERNAME": "admin",
        "LOCUST_PASSWORD": "admin123"
      },
      "disabled": false,
      "autoApprove": [
        "list_scripts",
        "list_instances",
        "get_instance_stats"
      ]
    }
  }
}
```

### 3. 环境变量说明

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `LOCUST_BASE_URL` | Locust 平台地址 | `http://localhost:8088` |
| `LOCUST_USERNAME` | 登录用户名 | `admin` |
| `LOCUST_PASSWORD` | 登录密码 | `admin123` |

## 📖 使用示例

### 查看可用脚本

```
请列出所有可用的压测脚本
```

### 上传新脚本

```
请帮我创建一个简单的压测脚本，测试 https://api.example.com/health 接口
```

### 启动压测

```
启动压测，使用 tmp/demo.py 脚本，目标地址 https://api.example.com，10个用户
```

### 查看压测结果

```
分析一下当前运行的压测实例结果
```

### cURL 转脚本

```
把这个 cURL 命令转成压测脚本：
curl -X POST 'https://api.example.com/login' \
  -H 'Content-Type: application/json' \
  -d '{"username": "test", "password": "123456"}'
```

## 🔧 高级配置

### 连接测试环境

```json
{
  "mcpServers": {
    "locust-test": {
      "command": "python",
      "args": ["path/to/locust_mcp_server.py"],
      "env": {
        "LOCUST_BASE_URL": "https://locust.test.example.com",
        "LOCUST_USERNAME": "test_user",
        "LOCUST_PASSWORD": "test_pass"
      }
    }
  }
}
```

### 使用 uvx 运行（推荐）

如果你已安装 uv，可以使用 uvx 自动管理依赖：

```json
{
  "mcpServers": {
    "locust-stress-test": {
      "command": "uvx",
      "args": [
        "--from", "git+https://your-repo/stresstest-locust.git#subdirectory=mcp",
        "locust-mcp-server"
      ],
      "env": {
        "LOCUST_BASE_URL": "http://localhost:8088"
      }
    }
  }
}
```

## 🛠️ 开发调试

### 本地运行测试

```bash
# 直接运行服务器（会阻塞等待 stdio 输入）
python locust_mcp_server.py

# 使用 mcp CLI 测试
mcp dev locust_mcp_server.py
```

### 日志调试

在代码中添加日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 注意事项

1. **确保 Locust 平台已启动**: MCP Server 需要连接到运行中的 Locust 压测平台
2. **登录凭据**: 确保配置的用户名密码正确，否则 API 调用会失败
3. **网络访问**: 确保 MCP Server 运行环境可以访问 Locust 平台地址
4. **脚本路径**: 上传脚本会保存到 `scripts/tmp/` 目录，启动实例时使用相对路径如 `tmp/xxx.py`

## 🔗 相关链接

- [Locust 官方文档](https://docs.locust.io/)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [主项目](../README.md)
