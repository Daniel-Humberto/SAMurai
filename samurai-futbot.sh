#!/usr/bin/env bash

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_CMD="docker compose"

log_info() { echo -e "${BLUE}[ℹ]${NC} $1"; }
log_success() { echo -e "${GREEN}[✔]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✘]${NC} $1"; exit 1; }
log_error_no_exit() { echo -e "${RED}[✘]${NC} $1"; }

echo_centered() {
    local text="$1"
    local cols
    cols=$(tput cols 2>/dev/null || echo 80)
    
    # Strip ANSI escape sequences using sed
    local clean
    clean=$(echo -e "$text" | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g')
    local len=${#clean}
    
    if (( len >= cols )); then
        echo -e "$text"
    else
        local padding=$(( (cols - len) / 2 ))
        printf "%${padding}s" ""
        echo -e "$text"
    fi
}

ensure_env() {
    if [[ ! -f "$ROOT_DIR/.env" ]]; then
        log_warning "No existe .env. Se copiara desde .env.example."
        cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    fi
}

get_service_status() {
    local svc=$1
    if docker ps --format '{{.Names}}' | grep -q "^${svc}$"; then
        echo -e "${GREEN}ONLINE${NC}"
    else
        echo -e "${RED}OFFLINE${NC}"
    fi
}

check_prerequisites() {
    log_info "Verificando Docker y NVIDIA Container Toolkit..."

    if ! command -v docker >/dev/null 2>&1; then
        log_warning "Docker no esta instalado. Instalando..."
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sudo sh /tmp/get-docker.sh
        rm -f /tmp/get-docker.sh
        sudo usermod -aG docker "$USER"
        log_success "Docker instalado."
    else
        log_success "Docker detectado."
    fi

    if ! dpkg -l 2>/dev/null | grep -q nvidia-container-toolkit; then
        log_warning "NVIDIA Container Toolkit no detectado. Instalando..."
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
        sudo apt-get update
        sudo apt-get install -y nvidia-container-toolkit
        sudo nvidia-ctk runtime configure --runtime=docker
        sudo systemctl restart docker
        log_success "NVIDIA Container Toolkit configurado."
    else
        log_success "NVIDIA Container Toolkit detectado."
    fi

    ensure_env
}

env_setup() {
    ensure_env
    log_info "Archivo .env listo en $ROOT_DIR/.env"
    log_info "Edita API keys y credenciales antes de levantar la plataforma."
}

build_stack() {
    ensure_env
    log_info "Construyendo imagenes de frontend y backend..."
    (cd "$ROOT_DIR" && $COMPOSE_CMD build)
    log_success "Build completado."
}

refresh_frontend() {
    ensure_env
    log_info "Reconstruyendo imagen de frontend (nextjs-frontend)..."
    (cd "$ROOT_DIR" && $COMPOSE_CMD build nextjs-frontend)
    log_info "Recreando contenedor de frontend..."
    (cd "$ROOT_DIR" && $COMPOSE_CMD up -d nextjs-frontend)
    log_success "Frontend actualizado con éxito."
}

up_stack() {
    ensure_env
    log_info "Levantando SAMurAI FutBotMX..."
    (cd "$ROOT_DIR" && $COMPOSE_CMD up -d)
    log_success "Servicios en linea."
}

down_stack() {
    log_info "Deteniendo servicios..."
    (cd "$ROOT_DIR" && $COMPOSE_CMD down)
    log_success "Servicios detenidos."
}

restart_stack() {
    down_stack
    up_stack
}

show_logs() {
    local svc="${1:-}"
    if [[ -n "$svc" ]]; then
        (cd "$ROOT_DIR" && $COMPOSE_CMD logs -f "$svc")
    else
        (cd "$ROOT_DIR" && $COMPOSE_CMD logs -f)
    fi
}

show_status() {
    log_info "Estado de contenedores:"
    (cd "$ROOT_DIR" && $COMPOSE_CMD ps)
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo
        log_info "Uso de GPU:"
        nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv
    fi
}

download_models() {
    ensure_env
    mkdir -p "$ROOT_DIR/backend/python-ai-core/models/sam"
    mkdir -p "$ROOT_DIR/backend/python-ai-core/models/yolo"
    mkdir -p "$ROOT_DIR/backend/python-ai-core/models/piper"
    log_info "Directorios de modelos preparados."
    cat <<'MODELS'
Modelos sugeridos:
  - SAM tiny:  backend/python-ai-core/models/sam/sam2.1_hiera_tiny.pt
  - SAM small: backend/python-ai-core/models/sam/sam2.1_hiera_small.pt
  - YOLOv8n:   backend/python-ai-core/models/yolo/yolov8n.pt
  - Piper:     backend/python-ai-core/models/piper/<voz>.onnx

Descarga pendiente de integrar con URLs/versiones definitivas del proyecto.
MODELS
}

reset_db() {
    read -r -p "Esto eliminara datos de PostgreSQL. Escribe RESET para continuar: " confirm
    [[ "$confirm" == "RESET" ]] || log_error "Operacion cancelada."
    (cd "$ROOT_DIR" && $COMPOSE_CMD down -v)
    (cd "$ROOT_DIR" && $COMPOSE_CMD up -d postgres redis)
    log_success "Volumenes reiniciados."
}

clean_all() {
    read -r -p "Esto detendra servicios y eliminara contenedores/volumenes locales. Escribe CLEAN para continuar: " confirm
    [[ "$confirm" == "CLEAN" ]] || log_error "Operacion cancelada."
    (cd "$ROOT_DIR" && $COMPOSE_CMD down -v --remove-orphans)
    log_success "Workspace Docker limpiado."
}

mitosis() {
    local parent_dir=$(dirname "$ROOT_DIR")
    local highest_ver=1
    for d in "$parent_dir"/V[0-9]*; do
        if [[ -d "$d" ]]; then
            local base=$(basename "$d")
            local num=${base#V}
            if [[ "$num" =~ ^[0-9]+$ ]] && (( num > highest_ver )); then
                highest_ver=$num
            fi
        fi
    done
    local next_ver=$((highest_ver + 1))
    local default_name="V$next_ver"

    echo -e "\n${BLUE}[ 🧬 MITOSIS - CLONACIÓN LIMPIA ]${NC}"
    echo "Esta función creará una copia limpia del proyecto para versionamiento."
    read -r -p "Nombre de la nueva versión (Default: $default_name): " new_name
    new_name="${new_name:-$default_name}"

    local dest_dir="$parent_dir/$new_name"
    if [[ -d "$dest_dir" ]]; then
        log_error_no_exit "El directorio de destino ya existe: $dest_dir"
        return 1
    fi

    log_info "Copiando proyecto limpio a $dest_dir..."
    mkdir -p "$dest_dir"

    local clean_excludes=(
        "node_modules"
        ".next"
        "__pycache__"
        ".venv"
        "venv"
        ".git"
        ".env"
        "out"
        "dist"
        ".obsidian"
        ".pytest_cache"
        ".mypy_cache"
        ".coverage"
        "htmlcov"
        "backend/python-ai-core/data/uploads"
        "backend/python-ai-core/data/reports"
        "backend/python-ai-core/models"
        "frontend/nextjs-frontend/.next"
        "*.log"
        "*.pid"
        "*.sock"
    )

    if command -v rsync >/dev/null 2>&1; then
        local rsync_args=(-a)
        for pattern in "${clean_excludes[@]}"; do
            rsync_args+=("--exclude=$pattern")
        done
        rsync "${rsync_args[@]}" "$ROOT_DIR/" "$dest_dir/"
    else
        local tar_args=()
        for pattern in "${clean_excludes[@]}"; do
            tar_args+=("--exclude=$pattern")
        done
        tar "${tar_args[@]}" -cf - -C "$ROOT_DIR" . | tar -xf - -C "$dest_dir"
    fi

    if [[ -d "$dest_dir" ]]; then
        if [[ -f "$dest_dir/.env.example" && ! -f "$dest_dir/.env" ]]; then
            cp "$dest_dir/.env.example" "$dest_dir/.env"
        fi
        log_success "Mitosis completada con éxito."
        log_info "Nueva versión creada en: $dest_dir"
        log_info "Se excluyeron dependencias, artefactos, modelos y datos generados para asegurar un clon limpio y reproducible."
        log_info "Siguiente flujo recomendado: cd $dest_dir && ./samurai-futbot.sh build && ./samurai-futbot.sh up"
    else
        log_error_no_exit "Ocurrió un error al copiar los archivos."
    fi
}

print_mini_banner() {
    echo_centered "${CYAN}SAMurAI FutBotMX${NC} · ${BLUE}Computer Vision & Robotics Tool${NC}"
    echo
}

show_banner() {
    clear
    local border="========================================================================"
    echo_centered "${BLUE}${border}${NC}"
    echo_centered "${CYAN}     ███████╗ █████╗ ███╗   ███╗██╗   ██╗██████╗  █████╗ ██╗  ${NC}"
    echo_centered "${CYAN}     ██╔════╝██╔══██╗████╗ ████║██║   ██║██╔══██╗██╔══██╗██║  ${NC}"
    echo_centered "${CYAN}     ███████╗███████║██╔████╔██║██║   ██║██████╔╝███████║██║  ${NC}"
    echo_centered "${CYAN}     ╚════██║██╔══██║██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║██║  ${NC}"
    echo_centered "${CYAN}     ███████║██║  ██║██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║██║  ${NC}"
    echo_centered "${CYAN}     ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ${NC}"
    echo_centered "${BLUE}${border}${NC}"
    echo_centered "  ${GREEN}[ YOLOv8n ]${NC} · ${GREEN}[ SAM 2.1 ]${NC} · ${GREEN}[ ByteTrack ]${NC} · ${GREEN}[ FastAPI ]${NC} · ${GREEN}[ Next.js ]${NC}"
    echo_centered "${BLUE}${border}${NC}"
    echo_centered "         ${CYAN}侍  -  F I E L D   I N T E L L I G E N C E${NC}  ·  v1.0"
    echo_centered "${BLUE}${border}${NC}"
}

show_help() {
    print_mini_banner
    cat <<'HELP'
Uso: ./samurai-futbot.sh [comando]

Comandos:
  install      Instala Docker/NVIDIA Toolkit y prepara .env
  build        Reconstruye frontend y backend
  frontend     Reconstruye y actualiza solo el frontend
  up           Levanta la plataforma
  down         Detiene la plataforma
  restart      Reinicia la plataforma
  logs [svc]   Sigue logs de todos o de un servicio
  status       Muestra docker compose ps y uso de GPU
  models       Prepara checkpoints y voces locales
  env-setup    Copia .env.example a .env si hace falta
  reset-db     Reinicia PostgreSQL/Redis con confirmacion
  clean        Elimina stack y volumenes con confirmacion
  mitosis      Crea una copia limpia y clonada para versionar (V2, V3, etc.)
HELP
}

press_enter() {
    echo
    read -r -p "Presiona [Enter] para volver al menú principal..."
}

show_logs_interactive() {
    echo -e "\n${BLUE}[ Ver Logs ]${NC}"
    echo "1) Todos los servicios"
    echo "2) nextjs-frontend"
    echo "3) python-ai-core"
    echo "4) postgres"
    echo "5) redis"
    echo "6) qdrant"
    echo "0) Cancelar"
    echo
    read -r -p "Selecciona una opción [0-6]: " log_choice
    case "$log_choice" in
        1) show_logs "" ;;
        2) show_logs "nextjs-frontend" ;;
        3) show_logs "python-ai-core" ;;
        4) show_logs "postgres" ;;
        5) show_logs "redis" ;;
        6) show_logs "qdrant" ;;
        0) echo "Operación cancelada." ;;
        *) echo "Opción inválida, mostrando todos los logs..." ; show_logs "" ;;
    esac
}

interactive_menu() {
    while true; do
        show_banner
        
        local cols
        cols=$(tput cols 2>/dev/null || echo 80)
        local menu_width=44
        local pad=0
        if (( cols > menu_width )); then
            pad=$(( (cols - menu_width) / 2 ))
        fi
        local indent
        indent=$(printf "%${pad}s" "")

        echo -e "${indent}${BLUE}[ Estado de Servicios ]${NC}"
        echo -e "${indent}· Frontend: $(get_service_status "nextjs-frontend")"
        echo -e "${indent}· AI Core:  $(get_service_status "python-ai-core")"
        echo -e "${indent}· Database: $(get_service_status "postgres")"
        echo
        echo -e "${indent}${YELLOW}[ ⚙️  ADMINISTRAR STACK ]${NC}"
        echo -e "${indent}  1) Levantar Plataforma (up)"
        echo -e "${indent}  2) Detener Plataforma (down)"
        echo -e "${indent}  3) Reiniciar Plataforma (restart)"
        echo -e "${indent}  4) Reconstruir Imágenes (build)"
        echo -e "${indent}  5) Actualizar Frontend (frontend)"
        echo -e "${indent}  6) Ver Logs de Servicios (logs)"
        echo -e "${indent}  7) Estado Detallado (status)"
        echo
        echo -e "${indent}${YELLOW}[ 📁 CONFIGURACIÓN & DATOS ]${NC}"
        echo -e "${indent}  8) Descargar/Preparar Modelos (models)"
        echo -e "${indent}  9) Configurar Entorno (env-setup)"
        echo -e "${indent} 10) Resetear Base de Datos (reset-db)"
        echo -e "${indent} 11) Limpieza Total (clean)"
        echo -e "${indent} 12) Clonación de Proyecto (mitosis)"
        echo
        echo -e "${indent}${YELLOW}[ 🚀 INSTALACIÓN ]${NC}"
        echo -e "${indent} 13) Instalar Dependencias (install)"
        echo
        echo -e "${indent}  0) Salir"
        echo
        read -r -p "${indent}Selecciona una opción [0-13]: " choice
        case "$choice" in
            1) up_stack; press_enter ;;
            2) down_stack; press_enter ;;
            3) restart_stack; press_enter ;;
            4) build_stack; press_enter ;;
            5) refresh_frontend; press_enter ;;
            6) show_logs_interactive; press_enter ;;
            7) show_status; press_enter ;;
            8) download_models; press_enter ;;
            9) env_setup; press_enter ;;
            10) reset_db; press_enter ;;
            11) clean_all; press_enter ;;
            12) mitosis; press_enter ;;
            13) check_prerequisites; press_enter ;;
            0) echo; echo_centered "${GREEN}Sayōnara! (さようなら)${NC}"; echo; exit 0 ;;
            *) echo_centered "${RED}[✘] Opción inválida.${NC}"; sleep 1 ;;
        esac
    done
}

cmd="${1:-}"
case "$cmd" in
    "") interactive_menu ;;
    install) print_mini_banner; check_prerequisites ;;
    build) print_mini_banner; build_stack ;;
    frontend) print_mini_banner; refresh_frontend ;;
    up) print_mini_banner; up_stack ;;
    down) print_mini_banner; down_stack ;;
    restart) print_mini_banner; restart_stack ;;
    logs) shift; print_mini_banner; show_logs "${1:-}" ;;
    status) print_mini_banner; show_status ;;
    models) print_mini_banner; download_models ;;
    env-setup) print_mini_banner; env_setup ;;
    reset-db) print_mini_banner; reset_db ;;
    clean) print_mini_banner; clean_all ;;
    mitosis) print_mini_banner; mitosis ;;
    *) show_help; exit 1 ;;
esac
