# ASE MCP Server - Claude MCP配置

这个文件包含了在Claude Desktop中使用ASE MCP Server的配置信息。

## 配置Claude MCP

在你的Claude配置文件中添加以下内容：

### macOS/Linux
编辑文件: `~/.config/claude/mcp_settings.json`

### Windows
编辑文件: `%APPDATA%/Claude/mcp_settings.json`

## 配置内容

```json
{
  "mcpServers": {
    "ase-mcp": {
      "command": "python",
      "args": ["/path/to/ASE_MCP/server/main.py", "--mcp-only"],
      "cwd": "/path/to/ASE_MCP",
      "env": {
        "PYTHONPATH": "/path/to/ASE_MCP",
        "REDIS_URL": "redis://localhost:6379",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## 使用说明

1. **替换路径**: 将 `/path/to/ASE_MCP` 替换为你的实际项目路径

2. **启动Redis**: 确保Redis服务正在运行
   ```bash
   redis-server
   ```

3. **测试连接**: 在Claude中使用以下命令测试连接
   ```
   请列出所有可用的ASE MCP工具
   ```

## 可用工具

- `create_structure` - 创建原子结构
- `modify_structure` - 修改现有结构
- `calculate_properties` - 计算物理化学属性
- `optimize_structure` - 几何优化
- `preview_structure` - 预览结构
- `save_structure` - 保存结构文件
- `list_sessions` - 列出所有会话
- `get_session_info` - 获取会话信息
- `delete_session` - 删除会话
- `undo_operation` - 撤销操作
- `redo_operation` - 重做操作
- `get_structure_info` - 获取结构详细信息

## 使用示例

### 创建铜的FCC结构
```
请使用ASE创建一个2x2x2的铜FCC结构
```

### 修改结构
```
请将当前结构绕Z轴旋转45度
```

### 计算能量
```
请计算当前结构的能量
```

### 查看会话
```
请列出所有的ASE会话
```

## 故障排除

如果遇到连接问题：

1. 检查Python路径是否正确
2. 确认Redis服务正在运行
3. 检查防火墙设置
4. 查看Claude的错误日志

## 高级配置

### 使用虚拟环境
如果你使用Python虚拟环境：

```json
{
  "mcpServers": {
    "ase-mcp": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/ASE_MCP/server/main.py", "--mcp-only"],
      "cwd": "/path/to/ASE_MCP",
      "env": {
        "PYTHONPATH": "/path/to/ASE_MCP",
        "REDIS_URL": "redis://localhost:6379"
      }
    }
  }
}
```

### 自定义Redis配置
```json
{
  "mcpServers": {
    "ase-mcp": {
      "command": "python",
      "args": ["/path/to/ASE_MCP/server/main.py", "--mcp-only"],
      "cwd": "/path/to/ASE_MCP",
      "env": {
        "PYTHONPATH": "/path/to/ASE_MCP",
        "REDIS_URL": "redis://localhost:6380",
        "REDIS_PASSWORD": "your-password",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## 重启Claude

配置完成后，请重启Claude Desktop应用程序以加载新的MCP服务器配置。