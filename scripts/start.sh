#!/bin/bash

# ASE MCP Server 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python版本
check_python() {
    log_info "检查Python版本..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_success "Python版本: $PYTHON_VERSION"
    else
        log_error "Python3未安装"
        exit 1
    fi
}

# 检查端口是否可用
check_port() {
    local port=$1
    local service_name=${2:-"服务"}

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        log_warning "$service_name 端口 $port 已被占用"
        read -p "是否杀死占用端口 $port 的进程? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            local pids=$(lsof -ti:$port)
            for pid in $pids; do
                kill -9 $pid 2>/dev/null && log_success "已杀死进程 $pid"
            done
        else
            log_error "$service_name 无法启动，端口 $port 被占用"
            return 1
        fi
    fi
    return 0
}

# 检查Redis连接
check_redis() {
    log_info "检查Redis连接..."
    REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}

    if command -v redis-cli &> /dev/null; then
        if redis-cli -u "$REDIS_URL" ping &> /dev/null; then
            log_success "Redis连接正常: $REDIS_URL"
        else
            log_warning "Redis连接失败，将尝试启动..."
            if command -v redis-server &> /dev/null; then
                redis-server --daemonize yes
                sleep 2
                log_success "Redis已启动"
            else
                log_warning "Redis未安装，将使用内存模拟模式"
            fi
        fi
    else
        log_warning "redis-cli未找到，将使用内存模拟模式"
    fi
}

# 安装依赖
install_dependencies() {
    log_info "安装Python依赖..."

    # 检查虚拟环境
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        log_warning "未检测到虚拟环境，建议创建虚拟环境"
        read -p "是否创建虚拟环境? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 -m venv venv
            source venv/bin/activate
            log_success "虚拟环境已创建并激活"
        fi
    fi

    # 安装Python依赖
    pip install -r requirements.txt
    log_success "Python依赖安装完成"

    # 安装前端依赖（如果存在）
    if [[ -d "client" && -f "client/package.json" ]]; then
        log_info "安装前端依赖..."
        cd client
        npm install
        cd ..
        log_success "前端依赖安装完成"
    fi
}

# 启动服务
start_server() {
    local mode=${1:-"full"}

    log_info "启动ASE MCP服务器..."

    # 设置环境变量
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    export REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}
    export WEB_HOST=${WEB_HOST:-"0.0.0.0"}
    export WEB_PORT=${WEB_PORT:-"8000"}
    export WEBSOCKET_PORT=${WEBSOCKET_PORT:-"8001"}

    case $mode in
        "mcp-only")
            log_info "启动MCP服务器（仅MCP模式）"
            cd server
            python main.py --mcp-only
            ;;
        "web-only")
            log_info "启动Web服务器（仅Web模式）"
            export ENABLE_MCP=false
            cd server
            python main.py
            ;;
        "full")
            log_info "启动完整服务器（MCP + Web）"
            cd server
            python main.py
            ;;
        *)
            log_error "未知的启动模式: $mode"
            show_help
            exit 1
            ;;
    esac
}

# 构建Docker镜像
build_docker() {
    log_info "构建Docker镜像..."

    # 构建服务器镜像
    docker build -f Dockerfile.server -t ase-mcp-server .
    log_success "服务器镜像构建完成"

    # 构建客户端镜像（如果存在）
    if [[ -f "Dockerfile.client" ]]; then
        docker build -f Dockerfile.client -t ase-mcp-client .
        log_success "客户端镜像构建完成"
    fi
}

# 启动Docker服务
start_docker() {
    log_info "启动Docker服务..."

    if [[ -f "docker-compose.yml" ]]; then
        docker-compose up -d
        log_success "Docker服务已启动"
        log_info "Web界面: http://localhost:3000"
        log_info "API文档: http://localhost:8000/docs"
        log_info "WebSocket: ws://localhost:8001"
    else
        log_error "docker-compose.yml未找到"
        exit 1
    fi
}

# 停止Docker服务
stop_docker() {
    log_info "停止Docker服务..."

    if [[ -f "docker-compose.yml" ]]; then
        docker-compose down
        log_success "Docker服务已停止"
    else
        log_error "docker-compose.yml未找到"
        exit 1
    fi
}

# 运行测试
run_tests() {
    log_info "运行测试..."

    export PYTHONPATH="${PYTHONPATH}:$(pwd)"

    if command -v pytest &> /dev/null; then
        pytest tests/ -v
        log_success "测试完成"
    else
        log_error "pytest未安装"
        exit 1
    fi
}

# 显示帮助
show_help() {
    echo "ASE MCP Server 启动脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  install     安装依赖"
    echo "  start       启动服务器（默认：完整模式）"
    echo "  mcp-only    启动MCP服务器（仅MCP模式）"
    echo "  web-only    启动Web服务器（仅Web模式）"
    echo "  docker-build 构建Docker镜像"
    echo "  docker-start 启动Docker服务"
    echo "  docker-stop  停止Docker服务"
    echo "  test        运行测试"
    echo "  help        显示此帮助"
    echo ""
    echo "环境变量:"
    echo "  REDIS_URL      Redis连接URL (默认: redis://localhost:6379)"
    echo "  WEB_HOST       Web服务器地址 (默认: 0.0.0.0)"
    echo "  WEB_PORT       Web服务器端口 (默认: 8000)"
    echo "  WEBSOCKET_PORT WebSocket端口 (默认: 8001)"
    echo ""
    echo "示例:"
    echo "  $0 install           # 安装依赖"
    echo "  $0 start             # 启动完整服务器"
    echo "  $0 mcp-only          # 仅启动MCP服务器"
    echo "  $0 docker-start      # 使用Docker启动"
}

# 主逻辑
main() {
    local command=${1:-"help"}

    case $command in
        "install")
            check_python
            install_dependencies
            ;;
        "start")
            check_python
            check_redis
            check_port ${WEB_PORT:-8000} "Web服务器"
            check_port ${WEBSOCKET_PORT:-8001} "WebSocket服务器"
            start_server "full"
            ;;
        "mcp-only")
            check_python
            check_redis
            start_server "mcp-only"
            ;;
        "web-only")
            check_python
            check_redis
            start_server "web-only"
            ;;
        "docker-build")
            build_docker
            ;;
        "docker-start")
            start_docker
            ;;
        "docker-stop")
            stop_docker
            ;;
        "test")
            check_python
            run_tests
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 检查是否在项目根目录
if [[ ! -f "requirements.txt" ]]; then
    log_error "请在项目根目录运行此脚本"
    exit 1
fi

# 运行主函数
main "$@"