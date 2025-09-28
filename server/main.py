#!/usr/bin/env python3
"""
ASE MCP Server 主启动文件
集成MCP服务器和WebSocket服务器
"""

import asyncio
import logging
import os
import signal
import sys
import argparse
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import uvicorn
from contextlib import asynccontextmanager

from core.session_manager import SessionManager
from handlers.websocket_handler import WebSocketServer
from web_server import ASEWebServer
from mcp_server import ASEMCPServer
from utils.logging_config import setup_default_logging, ase_logger
from utils.metrics import performance_monitor, metrics_collector, ASEMetrics

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ase_mcp.log')
    ]
)
logger = logging.getLogger(__name__)


class ASEMCPApplication:
    """ASE MCP应用程序主类"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        web_host: str = "0.0.0.0",
        web_port: int = 8000,
        websocket_port: int = 8001,
        enable_mcp: bool = True,
        enable_web: bool = True,
        serve_static: bool = True,
        allowed_origins: list = None
    ):
        self.redis_url = redis_url
        self.web_host = web_host
        self.web_port = web_port
        self.websocket_port = websocket_port
        self.enable_mcp = enable_mcp
        self.enable_web = enable_web
        self.serve_static = serve_static
        self.allowed_origins = allowed_origins or ["*"]

        # 核心组件
        self.session_manager = SessionManager(redis_url)
        self.websocket_server: Optional[WebSocketServer] = None
        self.web_server: Optional[ASEWebServer] = None
        self.mcp_server: Optional[ASEMCPServer] = None

        # 运行状态
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def initialize(self):
        """初始化所有组件"""
        logger.info("初始化ASE MCP应用程序...")

        try:
            # 启动性能监控
            await performance_monitor.start()
            logger.info("性能监控启动完成")

            # 初始化会话管理器
            await self.session_manager.initialize()
            logger.info("会话管理器初始化完成")
            ASEMetrics.record_session_activity('system_start')

            # 初始化WebSocket服务器
            if self.enable_web:
                self.websocket_server = WebSocketServer(
                    self.session_manager,
                    self.web_host,
                    self.websocket_port
                )
                await self.websocket_server.start()
                logger.info(f"WebSocket服务器启动: {self.web_host}:{self.websocket_port}")

            # 初始化Web服务器
            if self.enable_web:
                self.web_server = ASEWebServer(
                    redis_url=self.redis_url,
                    host=self.web_host,
                    port=self.web_port,
                    websocket_port=self.websocket_port,
                    session_manager=self.session_manager,
                    websocket_server=self.websocket_server,
                    serve_static=self.serve_static,
                    allowed_origins=self.allowed_origins
                )
                # 标记为使用外部服务
                self.web_server._external_services = True
                logger.info(f"Web服务器准备启动: {self.web_host}:{self.web_port}")

            # 初始化MCP服务器
            if self.enable_mcp:
                self.mcp_server = ASEMCPServer(self.redis_url)
                await self.mcp_server.initialize()
                logger.info("MCP服务器初始化完成")

            logger.info("所有组件初始化完成")

        except Exception as e:
            logger.error(f"初始化失败: {e}")
            raise

    async def start(self):
        """启动应用程序"""
        await self.initialize()
        self.running = True

        tasks = []

        try:
            # 启动Web服务器
            if self.enable_web and self.web_server:
                web_task = asyncio.create_task(self.web_server.run())
                tasks.append(web_task)
                logger.info("Web服务器已启动")

            # 启动MCP服务器
            if self.enable_mcp and self.mcp_server:
                mcp_task = asyncio.create_task(self.mcp_server.run())
                tasks.append(mcp_task)
                logger.info("MCP服务器已启动")

            # 启动定期清理任务
            cleanup_task = asyncio.create_task(self._periodic_cleanup())
            tasks.append(cleanup_task)

            logger.info("ASE MCP应用程序启动完成")

            # 等待所有任务完成
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"应用程序运行错误: {e}")
            raise
        finally:
            await self.shutdown()

    async def shutdown(self):
        """关闭应用程序"""
        if not self.running:
            return

        logger.info("正在关闭ASE MCP应用程序...")
        self.running = False

        try:
            # 关闭WebSocket服务器
            if self.websocket_server:
                await self.websocket_server.stop()
                logger.info("WebSocket服务器已关闭")

            # 关闭会话管理器
            await self.session_manager.close()
            logger.info("会话管理器已关闭")

            # 关闭线程池
            self.executor.shutdown(wait=True)
            logger.info("线程池已关闭")

        except Exception as e:
            logger.error(f"关闭过程中出错: {e}")

        logger.info("ASE MCP应用程序已关闭")

    async def _periodic_cleanup(self):
        """定期清理过期会话"""
        while self.running:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                if self.running:
                    expired_count = await self.session_manager.cleanup_expired_sessions()
                    if expired_count > 0:
                        logger.info(f"清理了 {expired_count} 个过期会话")
            except Exception as e:
                logger.error(f"定期清理失败: {e}")

    def get_status(self) -> dict:
        """获取应用程序状态"""
        return {
            "running": self.running,
            "components": {
                "session_manager": self.session_manager is not None,
                "websocket_server": self.websocket_server is not None,
                "web_server": self.web_server is not None,
                "mcp_server": self.mcp_server is not None
            },
            "connections": {
                "websocket_clients": len(self.websocket_server.get_manager().connections) if self.websocket_server else 0,
                "active_sessions": len(self.websocket_server.get_manager().session_subscribers) if self.websocket_server else 0
            }
        }


def setup_signal_handlers(app: ASEMCPApplication):
    """设置信号处理器"""
    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，正在关闭应用程序...")
        asyncio.create_task(app.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="ASE MCP Server - 原子模拟环境MCP服务器")
    parser.add_argument("--api-only", action="store_true",
                       help="仅运行API服务器，不提供前端静态文件")
    parser.add_argument("--mcp-only", action="store_true",
                       help="仅运行MCP服务器，用于CLI模式")
    parser.add_argument("--no-websocket", action="store_true",
                       help="禁用WebSocket服务器")
    parser.add_argument("--allowed-origins", nargs="*",
                       default=["*"], help="允许的CORS源，支持多个")
    parser.add_argument("--redis-url", default="redis://localhost:6379",
                       help="Redis连接URL")
    parser.add_argument("--host", default="0.0.0.0",
                       help="Web服务器监听地址")
    parser.add_argument("--port", type=int, default=8000,
                       help="Web服务器端口")
    parser.add_argument("--websocket-port", type=int, default=8001,
                       help="WebSocket服务器端口")
    return parser.parse_args()


async def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()

    # 从环境变量获取配置，命令行参数优先
    redis_url = os.getenv("REDIS_URL", args.redis_url)
    web_host = os.getenv("WEB_HOST", args.host)
    web_port = int(os.getenv("WEB_PORT", args.port))
    websocket_port = int(os.getenv("WEBSOCKET_PORT", args.websocket_port))
    enable_mcp = os.getenv("ENABLE_MCP", "true").lower() == "true"
    enable_web = os.getenv("ENABLE_WEB", "true").lower() == "true"

    # API-only模式禁用静态文件服务
    serve_static = not args.api_only and os.getenv("SERVE_STATIC", "true").lower() == "true"
    allowed_origins = args.allowed_origins

    # 打印启动信息
    logger.info("=" * 60)
    logger.info("ASE MCP Server - 原子模拟环境MCP服务器")
    logger.info("=" * 60)
    logger.info(f"Redis URL: {redis_url}")
    logger.info(f"Web服务器: {web_host}:{web_port}")
    logger.info(f"WebSocket服务器: {web_host}:{websocket_port}")
    logger.info(f"启用MCP服务器: {enable_mcp}")
    logger.info(f"启用Web服务器: {enable_web}")
    logger.info(f"静态文件服务: {serve_static}")
    logger.info(f"允许的CORS源: {allowed_origins}")
    logger.info("=" * 60)

    # 创建应用程序实例
    app = ASEMCPApplication(
        redis_url=redis_url,
        web_host=web_host,
        web_port=web_port,
        websocket_port=websocket_port,
        enable_mcp=enable_mcp,
        enable_web=enable_web,
        serve_static=serve_static,
        allowed_origins=allowed_origins
    )

    # 设置信号处理器
    setup_signal_handlers(app)

    try:
        # 启动应用程序
        await app.start()
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭...")
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}")
        sys.exit(1)


def run_mcp_only():
    """仅运行MCP服务器(用于CLI模式)"""
    import sys
    import os

    # 配置日志为仅输出到stderr，避免干扰MCP通信
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    async def run_mcp():
        mcp_server = ASEMCPServer(redis_url)
        await mcp_server.run()

    try:
        asyncio.run(run_mcp())
    except KeyboardInterrupt:
        logger.info("MCP服务器停止")
    except Exception as e:
        logger.error(f"MCP服务器运行错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 简单检查MCP模式（在parse_args之前）
    if len(sys.argv) > 1 and sys.argv[1] == "--mcp-only":
        run_mcp_only()
    else:
        # 运行完整应用程序（包含命令行参数解析）
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("应用程序被用户中断")
        except Exception as e:
            logger.error(f"应用程序运行错误: {e}")
            sys.exit(1)