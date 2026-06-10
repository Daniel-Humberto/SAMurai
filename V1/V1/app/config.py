import os
import torch

# Read from environment variables, defaulting to tiny if not set
CKPT = os.environ.get("SAM2_CKPT", "/checkpoints/sam2.1_hiera_tiny.pt")
CFG = os.environ.get("SAM2_CFG", "configs/sam2.1/sam2.1_hiera_t.yaml")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
FPS_CAP = int(os.environ.get("FPS_CAP", 20))
PORT = int(os.environ.get("PORT", 7860))
