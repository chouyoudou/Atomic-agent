#!/bin/bash
# ASE MCP Server Interactive Startup Script

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

print_header() {
    echo -e "${PURPLE}"
    echo "🧬 ASE MCP Server - Atomic Simulation Environment"
    echo "=================================================="
    echo -e "${NC}"
}

check_command() {
    if command -v $1 >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        print_info "Killing processes on port $port: $pids"
        kill $pids 2>/dev/null || true
        sleep 2
    fi
}

check_dependencies() {
    print_info "Checking dependencies..."

    if ! check_command python3 && ! check_command python; then
        print_error "Python not found, please install Python 3.8+"
        return 1
    fi

    python_cmd="python3"
    if ! check_command python3; then
        python_cmd="python"
    fi

    if ! $python_cmd -c "import ase, fastapi, uvicorn" 2>/dev/null; then
        print_warning "Missing Python dependencies, installing..."
        pip install -r requirements.txt || {
            print_error "Failed to install Python dependencies"
            return 1
        }
    fi

    print_success "Dependencies check completed"
    return 0
}

start_services() {
    local mode=$1
    print_info "Starting mode: $mode"

    # Clean up ports
    for port in 8000 8001 3000; do
        if check_port $port; then
            print_warning "Port $port is occupied, cleaning up..."
            kill_port $port
        fi
    done

    python_cmd="python3"
    if ! check_command python3; then
        python_cmd="python"
    fi

    case $mode in
        "separated")
            print_info "Starting backend API service..."
            nohup $python_cmd server/main.py --api-only > /tmp/ase_mcp_backend.log 2>&1 &
            backend_pid=$!
            print_success "Backend started (PID: $backend_pid)"

            if check_command npm; then
                print_info "Starting frontend service..."
                cd client
                if [ ! -d "node_modules" ]; then
                    print_info "Installing frontend dependencies..."
                    npm install
                fi
                nohup npm start > /tmp/ase_mcp_frontend.log 2>&1 &
                frontend_pid=$!
                cd ..
                print_success "Frontend started (PID: $frontend_pid)"
                print_info "Frontend: http://localhost:3000"
            else
                print_warning "npm not found, backend only"
            fi
            print_info "API: http://localhost:8000/docs"
            ;;
        "integrated")
            print_info "Starting integrated service..."
            nohup $python_cmd server/main.py > /tmp/ase_mcp_backend.log 2>&1 &
            backend_pid=$!
            print_success "Integrated service started (PID: $backend_pid)"
            print_info "Access: http://localhost:8000"
            ;;
        "api-only")
            print_info "Starting API-only backend..."
            nohup $python_cmd server/main.py --api-only > /tmp/ase_mcp_backend.log 2>&1 &
            backend_pid=$!
            print_success "API service started (PID: $backend_pid)"
            print_info "API documentation: http://localhost:8000/docs"
            ;;
    esac

    print_info "Waiting for services to start..."
    sleep 5

    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_success "Services running normally!"
    else
        print_error "Service startup failed, check logs: tail -f /tmp/ase_mcp_backend.log"
    fi
}

show_menu() {
    echo -e "${CYAN}"
    echo "Please select startup mode:"
    echo "1) Separated mode (recommended for development)"
    echo "2) Integrated mode (simple deployment)"
    echo "3) API-only (no frontend)"
    echo "4) Run examples"
    echo "5) Check service status"
    echo "6) Stop all services"
    echo "0) Exit"
    echo -e "${NC}"
    read -p "Enter choice [0-6]: " choice
}

run_examples() {
    echo -e "${CYAN}"
    echo "Select example:"
    echo "1) Structure creation examples"
    echo "2) Structure modification examples"
    echo "3) Crystal transformation examples"
    echo "0) Return"
    echo -e "${NC}"
    read -p "Select [0-3]: " example_choice

    case $example_choice in
        1) python3 examples/api_examples/create_structures.py ;;
        2) python3 examples/api_examples/modify_structures.py ;;
        3) python3 examples/api_examples/transform_crystals.py ;;
        0) return ;;
        *) print_error "Invalid choice" ;;
    esac

    read -p "Press Enter to continue..." dummy
}

check_status() {
    print_info "Checking service status..."

    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_success "Backend service running normally (http://localhost:8000)"
    else
        print_warning "Backend service not running"
    fi

    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        print_success "Frontend service running normally (http://localhost:3000)"
    else
        print_warning "Frontend service not running"
    fi

    read -p "Press Enter to continue..." dummy
}

stop_services() {
    print_info "Stopping all services..."
    for port in 8000 8001 3000; do
        kill_port $port
    done
    print_success "All services stopped"
    read -p "Press Enter to continue..." dummy
}

main() {
    cd "$(dirname "$0")/.."
    print_header

    if ! check_dependencies; then
        exit 1
    fi

    while true; do
        show_menu
        case $choice in
            1) start_services "separated"; read -p "Press Enter to continue..." dummy ;;
            2) start_services "integrated"; read -p "Press Enter to continue..." dummy ;;
            3) start_services "api-only"; read -p "Press Enter to continue..." dummy ;;
            4) run_examples ;;
            5) check_status ;;
            6) stop_services ;;
            0) print_info "Goodbye!"; exit 0 ;;
            *) print_error "Invalid choice" ;;
        esac
    done
}

main "$@"