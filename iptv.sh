#!/bin/bash

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用root权限运行此脚本"
        exit 1
    fi
}

# 检测系统类型
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        print_error "无法检测操作系统类型"
        exit 1
    fi
}

install_deps() {
    case $OS in
        "Ubuntu"|"Debian GNU/Linux")
            print_info "检测到 $OS $VER 系统"
            print_info "开始安装依赖..."
            
            # 更新包列表
            apt update
            
            # 安装 Python 相关包
            apt install -y python3 python3-pip python3-full python3-venv
            
            # 安装系统级依赖包
            apt install -y python3-requests python3-bs4 ca-certificates
            
            # 创建虚拟环境
            print_info "创建 Python 虚拟环境..."
            python3 -m venv /opt/iptv_env
            
            # 激活虚拟环境并安装包
            print_info "在虚拟环境中安装 Python 包..."
            /opt/iptv_env/bin/pip install requests beautifulsoup4
            ;;
            
        "CentOS Linux"|"Red Hat Enterprise Linux")
            print_info "检测到 $OS $VER 系统"
            print_info "开始安装依赖..."
            
            # 安装EPEL源
            yum install -y epel-release
            
            # 安装Python3和相关包
            yum install -y python3 python3-pip python3-devel python3-virtualenv
            
            # 安装依赖包
            yum install -y python3-requests python3-beautifulsoup4 ca-certificates
            
            # 创建虚拟环境
            print_info "创建 Python 虚拟环境..."
            python3 -m venv /opt/iptv_env
            
            # 激活虚拟环境并安装包
            print_info "在虚拟环境中安装 Python 包..."
            /opt/iptv_env/bin/pip install requests beautifulsoup4
            ;;
            
        *)
            print_error "不支持的操作系统: $OS"
            exit 1
            ;;
    esac
}

verify_install() {
    print_info "验证安装..."
    
    # 检查 Python3
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 安装失败"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "/opt/iptv_env" ]; then
        print_error "Python 虚拟环境创建失败"
        exit 1
    fi
    
    # 验证 Python 包
    if ! /opt/iptv_env/bin/python3 -c "import requests" 2>/dev/null; then
        print_error "requests 模块安装失败"
        exit 1
    fi
    
    if ! /opt/iptv_env/bin/python3 -c "import bs4" 2>/dev/null; then
        print_error "beautifulsoup4 模块安装失败"
        exit 1
    fi
    
    print_info "所有依赖安装成功！"
}

# 检查依赖是否已安装
check_deps() {
    print_info "检查依赖是否已安装..."
    
    # 检查 Python3 和虚拟环境
    if command -v python3 &> /dev/null && [ -d "/opt/iptv_env" ]; then
        # 验证虚拟环境中的包
        if /opt/iptv_env/bin/python3 -c "import requests" 2>/dev/null && \
           /opt/iptv_env/bin/python3 -c "import bs4" 2>/dev/null; then
            print_info "所有依赖已安装，跳过安装步骤"
            return 0
        fi
    fi
    return 1
}

# 主函数
main() {
    print_info "开始检查依赖..."
    check_root
    detect_os
    
    # 如果依赖已安装，则跳过安装步骤
    if ! check_deps; then
        print_info "开始安装依赖..."
        install_deps
        verify_install
    fi
    
    print_info "完成！"
    print_info "要使用Python虚拟环境，请执行以下命令："
    echo -e "${GREEN}    source /opt/iptv_env/bin/activate${NC}"
    echo -e "${GREEN}或者直接使用完整路径运行Python：${NC}"
    echo -e "${GREEN}    /opt/iptv_env/bin/python3 你的脚本.py${NC}"
}

# 运行主函数
main 
