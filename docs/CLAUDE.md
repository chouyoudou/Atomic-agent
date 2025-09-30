# ASE MCP Server - Claude MCP Configuration

This file contains configuration information for using the ASE MCP Server with Claude Desktop.

## Configuring Claude MCP

Add the following content to your Claude configuration file:

### macOS/Linux
Edit file: `~/.config/claude/mcp_settings.json`

### Windows
Edit file: `%APPDATA%/Claude/mcp_settings.json`

## Configuration Content

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

## Usage Instructions

1. **Replace Paths**: Replace `/path/to/ASE_MCP` with your actual project path

2. **Start Redis**: Ensure Redis service is running
   ```bash
   redis-server
   ```

3. **Test Connection**: Use the following command in Claude to test the connection
   ```
   Please list all available ASE MCP tools
   ```

## Available Tools

- `create_structure` - Create atomic structures
- `modify_structure` - Modify existing structures
- `calculate_properties` - Calculate physical and chemical properties
- `optimize_structure` - Perform geometry optimization
- `preview_structure` - Preview structures
- `save_structure` - Save structure files
- `list_sessions` - List all sessions
- `get_session_info` - Get session information
- `delete_session` - Delete sessions
- `undo_operation` - Undo operations
- `redo_operation` - Redo operations
- `get_structure_info` - Get detailed structure information

## Usage Examples

### Create Copper FCC Structure
```
Please create a 2x2x2 copper FCC structure using ASE
```

### Modify Structure
```
Please rotate the current structure 45 degrees around the Z-axis
```

### Calculate Energy
```
Please calculate the energy of the current structure
```

### View Sessions
```
Please list all ASE sessions
```

## Troubleshooting

If you encounter connection issues:

1. Check if the Python path is correct
2. Confirm Redis service is running
3. Check firewall settings
4. Review Claude's error logs

## Advanced Configuration

### Using Virtual Environment
If you are using a Python virtual environment:

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

### Custom Redis Configuration
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

## Restart Claude

After completing the configuration, please restart the Claude Desktop application to load the new MCP server configuration.