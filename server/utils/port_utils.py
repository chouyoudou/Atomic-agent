"""
端口工具函数
"""

import socket
import logging

logger = logging.getLogger(__name__)


def find_free_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """
    查找可用的端口

    Args:
        start_port: 起始端口
        max_attempts: 最大尝试次数

    Returns:
        可用的端口号
    """
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port):
            return port

    raise RuntimeError(f"无法在 {start_port}-{start_port + max_attempts} 范围内找到可用端口")


def is_port_available(port: int, host: str = "localhost") -> bool:
    """
    检查端口是否可用

    Args:
        port: 端口号
        host: 主机地址

    Returns:
        端口是否可用
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = sock.bind((host, port))
            return True
    except socket.error:
        return False


def kill_process_on_port(port: int):
    """
    杀死占用端口的进程

    Args:
        port: 端口号
    """
    import subprocess
    import os

    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if f':{port}' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            subprocess.run(f'taskkill /PID {pid} /F', shell=True)
                            logger.info(f"已杀死占用端口 {port} 的进程 {pid}")
        else:  # Unix-like
            result = subprocess.run(
                f'lsof -ti:{port}',
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(f'kill -9 {pid}', shell=True)
                        logger.info(f"已杀死占用端口 {port} 的进程 {pid}")
    except Exception as e:
        logger.error(f"杀死端口 {port} 上的进程失败: {e}")


def get_port_info(port: int) -> dict:
    """
    获取端口信息

    Args:
        port: 端口号

    Returns:
        端口信息字典
    """
    import subprocess
    import os

    info = {
        'port': port,
        'available': is_port_available(port),
        'processes': []
    }

    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, capture_output=True, text=True
            )
        else:  # Unix-like
            result = subprocess.run(
                f'lsof -i:{port}',
                shell=True, capture_output=True, text=True
            )

        if result.stdout:
            info['processes'] = result.stdout.strip().split('\n')
    except Exception as e:
        logger.error(f"获取端口 {port} 信息失败: {e}")

    return info