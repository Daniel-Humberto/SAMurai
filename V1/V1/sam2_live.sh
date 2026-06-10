#!/bin/bash
# ============================================================
#  SAM 2 LIVE v2 — Arquitectura modular mejorada
#  Copa FutBotMX · SAMurai
#  Uso: bash sam2_live.sh
# ============================================================

set -e

CONTAINER_NAME="sam2-live-v2"
IMAGE_NAME="sam2-live-v2:latest"
WORKSPACE="$HOME/sam2-live-v2"
PORT=7860
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Cargar configuración del modelo si existe, de lo contrario establecer valores por defecto
load_model_config() {
  if [ -f "$WORKSPACE/sam2_env.sh" ]; then
    source "$WORKSPACE/sam2_env.sh"
  else
    SAM2_MODEL_SIZE="tiny"
    CHECKPOINT="sam2.1_hiera_tiny.pt"
    CFG="configs/sam2.1/sam2.1_hiera_t.yaml"
    CKPT_URL="https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt"
  fi
}

load_model_config

G="\033[0;32m"; C="\033[0;36m"; Y="\033[0;33m"; R="\033[0;31m"; B="\033[1;37m"; NC="\033[0m"
info()  { echo -e "${G}[SAM2-LIVE]${NC} $1"; }
warn()  { echo -e "${Y}[WARN]${NC} $1"; }
error() { echo -e "${R}[ERROR]${NC} $1"; exit 1; }

select_model_profile() {
  clear 2>/dev/null || true
  echo -e "${C}============================================================"
  echo -e "  SELECCIÓN DE PERFIL DE GPU / VRAM (SAM 2.1)"
  echo -e "============================================================${NC}"
  echo "  Selecciona el modelo basado en la VRAM de tu tarjeta gráfica:"
  echo ""
  echo "  1) Tiny  [sam2.1_hiera_t]  (~2-4 GB VRAM) -> Súper Rápido, ideal para GPUs de entrada/laptop"
  echo "  2) Small [sam2.1_hiera_s]  (~4-6 GB VRAM) -> Excelente equilibrio velocidad/precisión"
  echo "  3) Base+ [sam2.1_hiera_b+] (~6-8 GB VRAM) -> Mayor precisión, recomendado para gama media"
  echo "  4) Large [sam2.1_hiera_l]  (>8 GB VRAM)   -> Máxima fidelidad de contornos, consume más VRAM"
  echo ""
  read -rp "  Selecciona una opción [1-4] (por defecto 1): " M_OPT
  
  case "$M_OPT" in
    2)
      M_SIZE="small"
      CHECKPOINT="sam2.1_hiera_small.pt"
      CFG="configs/sam2.1/sam2.1_hiera_s.yaml"
      CKPT_URL="https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt"
      ;;
    3)
      M_SIZE="base"
      CHECKPOINT="sam2.1_hiera_base_plus.pt"
      CFG="configs/sam2.1/sam2.1_hiera_b+.yaml"
      CKPT_URL="https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt"
      ;;
    4)
      M_SIZE="large"
      CHECKPOINT="sam2.1_hiera_large.pt"
      CFG="configs/sam2.1/sam2.1_hiera_l.yaml"
      CKPT_URL="https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt"
      ;;
    *)
      M_SIZE="tiny"
      CHECKPOINT="sam2.1_hiera_tiny.pt"
      CFG="configs/sam2.1/sam2.1_hiera_t.yaml"
      CKPT_URL="https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt"
      ;;
  esac

  mkdir -p "$WORKSPACE"
  cat <<EOF > "$WORKSPACE/sam2_env.sh"
# Configuración del modelo SAM 2.1 para Copa FutBotMX
SAM2_MODEL_SIZE="$M_SIZE"
CHECKPOINT="$CHECKPOINT"
CFG="$CFG"
CKPT_URL="$CKPT_URL"
EOF
  info "Configuración guardada en: $WORKSPACE/sam2_env.sh"
  info "Modelo seleccionado: $CHECKPOINT"
  sleep 1.5
}

ensure_model_profile() {
  if [ ! -f "$WORKSPACE/sam2_env.sh" ]; then
    select_model_profile
  else
    source "$WORKSPACE/sam2_env.sh"
  fi
}

menu() {
  clear 2>/dev/null || true

  # Cargar configuración actual para mostrarla en el menú
  load_model_config

  echo -e "${C}"
  echo "  ███████╗ █████╗ ███╗   ███╗██████╗      ██╗     ██╗██╗   ██╗███████╗"
  echo "  ██╔════╝██╔══██╗████╗ ████║╚════██╗    ██╔╝     ██║██║   ██║██╔════╝"
  echo "  ███████╗███████║██╔████╔██║ █████╔╝   ██╔╝      ██║██║   ██║█████╗  "
  echo "  ╚════██║██╔══██║██║╚██╔╝██║██╔═══╝   ██╔╝       ██║╚██╗ ██╔╝██╔══╝  "
  echo "  ███████║██║  ██║██║ ╚═╝ ██║███████╗ ██╔╝        ██║ ╚████╔╝ ███████╗"
  echo "  ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚═╝         ╚═╝  ╚═══╝  ╚══════╝"
  echo -e "${NC}"
  echo -e "  ${B}Copa FutBotMX · SAMurai · V2 Modular${NC}"
  echo -e "  Modelo Activo: ${Y}${CHECKPOINT}${NC} (${SAM2_MODEL_SIZE})"
  echo ""
  echo "  1) 🚀 Build & Launch"
  echo "  2) ▶️  Start GUI"
  echo "  3) 🔁 Rebuild"
  echo "  4) 🛑 Stop"
  echo "  5) 🧹 Clean"
  echo "  6) ⚙️  Cambiar Perfil de VRAM / Modelo"
  echo "  q) Salir"
  echo ""
  read -rp "  Opcion: " OPT
  case "$OPT" in
    1) ensure_model_profile; cmd_build_launch ;;
    2) ensure_model_profile; cmd_launch       ;;
    3) ensure_model_profile; cmd_rebuild      ;;
    4) cmd_stop         ;;
    5) cmd_clean        ;;
    6) select_model_profile; menu ;;
    q) exit 0           ;;
    *) warn "Opcion invalida"; sleep 1; menu ;;
  esac
}

prepare_workspace() {
  mkdir -p "$WORKSPACE"/{checkpoints,inputs,outputs}

  if [ ! -f "$WORKSPACE/checkpoints/$CHECKPOINT" ]; then
    info "Descargando checkpoint SAM2..."
    wget -q --show-progress -O "$WORKSPACE/checkpoints/$CHECKPOINT" "$CKPT_URL"
  fi

  info "Copiando archivos de la app..."
  cp -r "$SCRIPT_DIR/app"     "$WORKSPACE/app"
  cp -r "$SCRIPT_DIR/static"  "$WORKSPACE/static"
  cp    "$SCRIPT_DIR/Dockerfile"       "$WORKSPACE/Dockerfile"
  cp    "$SCRIPT_DIR/requirements.txt" "$WORKSPACE/requirements.txt"
  cp -r "$SCRIPT_DIR/scripts" "$WORKSPACE/scripts"
  chmod +x "$WORKSPACE/scripts/download_checkpoint.sh"
}

cmd_build_launch() {
  prepare_workspace
  info "Construyendo imagen Docker..."
  docker build -t "$IMAGE_NAME" "$WORKSPACE"
  cmd_launch
}

cmd_launch() {
  cmd_stop 2>/dev/null || true

  VIDEO_FLAGS=""
  for i in 0 1 2; do
    if [ -e "/dev/video$i" ]; then
      VIDEO_FLAGS="$VIDEO_FLAGS --device=/dev/video$i"
    fi
  done

  CONTAINER_CKPT="/checkpoints/$CHECKPOINT"

  info "Iniciando SAM2 Live v2 con el modelo: $CHECKPOINT..."
  docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --gpus all \
    $VIDEO_FLAGS \
    -e SAM2_CKPT="$CONTAINER_CKPT" \
    -e SAM2_CFG="$CFG" \
    -v "$WORKSPACE/checkpoints:/checkpoints:ro" \
    -v "$WORKSPACE/inputs:/inputs:ro" \
    -v "$WORKSPACE/outputs:/outputs" \
    -p "$PORT:7860" \
    "$IMAGE_NAME"

  info "Esperando que cargue el modelo (~15s)..."
  sleep 15

  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo ""
    echo -e "  ${G}╔══════════════════════════════════════════╗${NC}"
    echo -e "  ${G}║  SAM2 LIVE v2 corriendo!                 ║${NC}"
    echo -e "  ${G}║                                          ║${NC}"
    echo -e "  ${G}║  http://localhost:${PORT}                  ║${NC}"
    echo -e "  ${G}║                                          ║${NC}"
    echo -e "  ${G}║  Click izquierdo => incluir objeto       ║${NC}"
    echo -e "  ${G}║  Click derecho   => excluir zona         ║${NC}"
    echo -e "  ${G}║  Tecla C         => limpiar puntos       ║${NC}"
    echo -e "  ${G}╚══════════════════════════════════════════╝${NC}"
    echo ""
    if command -v xdg-open &>/dev/null; then
      xdg-open "http://localhost:$PORT" 2>/dev/null &
    fi
  else
    warn "Error al iniciar container. Logs:"
    docker logs "$CONTAINER_NAME"
  fi
  menu
}

cmd_rebuild() {
  prepare_workspace
  info "Rebuild imagen..."
  docker build -t "$IMAGE_NAME" "$WORKSPACE"
  menu
}

cmd_stop() {
  docker stop "$CONTAINER_NAME" 2>/dev/null && \
  docker rm   "$CONTAINER_NAME" 2>/dev/null && \
  info "Container detenido." || true
}

cmd_clean() {
  warn "Se eliminara container, imagen y workspace."
  read -rp "Seguro? (s/N): " C
  if [[ "$C" == "s" || "$C" == "S" ]]; then
    cmd_stop 2>/dev/null || true
    docker rmi "$IMAGE_NAME" 2>/dev/null || true
    rm -rf "$WORKSPACE"
    info "Limpieza completa."
  fi
  sleep 1; menu
}

command -v docker &>/dev/null || error "Docker no instalado."
command -v wget   &>/dev/null || error "wget no instalado."

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker start "$CONTAINER_NAME" &>/dev/null
  fi
fi

menu
