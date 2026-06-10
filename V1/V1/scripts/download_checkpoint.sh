#!/bin/bash
# Downloads SAM2 checkpoint if not present
set -e

CHECKPOINT="${1:-sam2.1_hiera_tiny.pt}"
DEST="${2:-/checkpoints}"
URL="${3:-https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt}"

if [ -f "$DEST/$CHECKPOINT" ]; then
    echo "Checkpoint ya existe: $DEST/$CHECKPOINT"
    exit 0
fi

mkdir -p "$DEST"
echo "Descargando $CHECKPOINT..."
wget -q --show-progress -O "$DEST/$CHECKPOINT" "$URL"
echo "Descarga completa."
