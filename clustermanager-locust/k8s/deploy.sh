#!/bin/bash

# Locust Manager Kubernetes部署脚本
# 使用方法: ./deploy.sh [install|upgrade|uninstall]

set -e

NAMESPACE="locust-manager"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色输出
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

# 检查kubectl是否可用
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl命令未找到，请先安装kubectl"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "无法连接到Kubernetes集群，请检查kubeconfig配置"
        exit 1
    fi
    
    log_info "Kubernetes集群连接正常"
}

# 检查必要的配置
check_config() {
    log_info "检查配置文件..."
    
    local required_files=(
        "namespace.yaml"
        "rbac.yaml"
        "storage.yaml"
        "deployment.yaml"
        "service.yaml"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$SCRIPT_DIR/$file" ]]; then
            log_error "配置文件 $file 不存在"
            exit 1
        fi
    done
    
    log_success "所有配置文件检查完成"
}

# 安装函数
install() {
    log_info "开始安装Locust Manager..."
    
    # 创建命名空间和配置
    log_info "创建命名空间和基础配置..."
    kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
    
    # 等待命名空间创建完成
    kubectl wait --for=condition=Active namespace/$NAMESPACE --timeout=60s
    
    # 创建RBAC
    log_info "创建RBAC配置..."
    kubectl apply -f "$SCRIPT_DIR/rbac.yaml"
    
    # 创建存储
    log_info "创建存储配置..."
    kubectl apply -f "$SCRIPT_DIR/storage.yaml"
    
    # 等待PVC绑定
    log_info "等待PVC绑定..."
    kubectl wait --for=condition=Bound pvc/locust-manager-uploads-pvc -n $NAMESPACE --timeout=300s || log_warning "uploads PVC绑定超时"
    kubectl wait --for=condition=Bound pvc/locust-manager-scripts-pvc -n $NAMESPACE --timeout=300s || log_warning "scripts PVC绑定超时"
    kubectl wait --for=condition=Bound pvc/locust-manager-logs-pvc -n $NAMESPACE --timeout=300s || log_warning "logs PVC绑定超时"
    
    # 部署应用
    log_info "部署应用..."
    kubectl apply -f "$SCRIPT_DIR/deployment.yaml"
    
    # 创建服务
    log_info "创建服务..."
    kubectl apply -f "$SCRIPT_DIR/service.yaml"
    
    # 等待部署完成
    log_info "等待部署完成..."
    kubectl rollout status deployment/locust-manager -n $NAMESPACE --timeout=600s
    
    # 显示部署状态
    show_status
    
    log_success "Locust Manager安装完成！"
}

# 升级函数
upgrade() {
    log_info "开始升级Locust Manager..."
    
    # 更新配置
    log_info "更新配置..."
    kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
    kubectl apply -f "$SCRIPT_DIR/rbac.yaml"
    
    # 更新部署
    log_info "更新部署..."
    kubectl apply -f "$SCRIPT_DIR/deployment.yaml"
    kubectl apply -f "$SCRIPT_DIR/service.yaml"
    
    # 等待滚动更新完成
    log_info "等待滚动更新完成..."
    kubectl rollout status deployment/locust-manager -n $NAMESPACE --timeout=600s
    
    # 显示部署状态
    show_status
    
    log_success "Locust Manager升级完成！"
}

# 卸载函数
uninstall() {
    log_warning "开始卸载Locust Manager..."
    
    read -p "确定要卸载Locust Manager吗？这将删除所有相关资源 (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "取消卸载"
        exit 0
    fi
    
    # 删除部署和服务
    log_info "删除部署和服务..."
    kubectl delete -f "$SCRIPT_DIR/service.yaml" --ignore-not-found=true
    kubectl delete -f "$SCRIPT_DIR/deployment.yaml" --ignore-not-found=true
    
    # 等待Pod终止
    log_info "等待Pod终止..."
    kubectl wait --for=delete pod -l app=locust-manager -n $NAMESPACE --timeout=300s || true
    
    # 删除存储（可选，保留数据）
    read -p "是否删除存储卷？这将永久删除所有数据 (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "删除存储..."
        kubectl delete -f "$SCRIPT_DIR/storage.yaml" --ignore-not-found=true
    else
        log_info "保留存储卷"
    fi
    
    # 删除RBAC
    log_info "删除RBAC配置..."
    kubectl delete -f "$SCRIPT_DIR/rbac.yaml" --ignore-not-found=true
    
    # 删除命名空间
    log_info "删除命名空间..."
    kubectl delete namespace $NAMESPACE --ignore-not-found=true
    
    log_success "Locust Manager卸载完成！"
}

# 显示状态
show_status() {
    log_info "部署状态："
    echo
    
    # 显示Pod状态
    echo "Pods:"
    kubectl get pods -n $NAMESPACE -o wide
    echo
    
    # 显示服务状态
    echo "Services:"
    kubectl get svc -n $NAMESPACE
    echo
    
    # 显示PVC状态
    echo "PersistentVolumeClaims:"
    kubectl get pvc -n $NAMESPACE
    echo
    
    # 显示Ingress状态（如果存在）
    if kubectl get ingress -n $NAMESPACE &> /dev/null; then
        echo "Ingress:"
        kubectl get ingress -n $NAMESPACE
        echo
    fi
    
    # 显示访问信息
    log_info "访问信息："
    
    # NodePort访问
    local nodeport=$(kubectl get svc locust-manager-nodeport -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
    if [[ -n "$nodeport" ]]; then
        echo "NodePort访问: http://<节点IP>:$nodeport"
    fi
    
    # Ingress访问
    local ingress_host=$(kubectl get ingress locust-manager-ingress -n $NAMESPACE -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo "")
    if [[ -n "$ingress_host" ]]; then
        echo "Ingress访问: http://$ingress_host"
    fi
    
    # 端口转发访问
    echo "端口转发访问: kubectl port-forward -n $NAMESPACE svc/locust-manager-service 8080:80"
    echo "然后访问: http://localhost:8080"
}

# 显示日志
show_logs() {
    log_info "显示应用日志..."
    kubectl logs -f deployment/locust-manager -n $NAMESPACE
}

# 显示帮助
show_help() {
    echo "Locust Manager Kubernetes部署脚本"
    echo
    echo "使用方法:"
    echo "  $0 install    - 安装Locust Manager"
    echo "  $0 upgrade    - 升级Locust Manager"
    echo "  $0 uninstall  - 卸载Locust Manager"
    echo "  $0 status     - 显示部署状态"
    echo "  $0 logs       - 显示应用日志"
    echo "  $0 help       - 显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0 install"
    echo "  $0 status"
    echo "  $0 logs"
}

# 主函数
main() {
    case "${1:-help}" in
        install)
            check_kubectl
            check_config
            install
            ;;
        upgrade)
            check_kubectl
            check_config
            upgrade
            ;;
        uninstall)
            check_kubectl
            uninstall
            ;;
        status)
            check_kubectl
            show_status
            ;;
        logs)
            check_kubectl
            show_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"