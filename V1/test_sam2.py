import sys
sys.path.insert(0, "/app/sam2")
import numpy as np
import torch
import traceback
from app.model import Segmenter
from app.config import DEVICE
from app.model import DTYPE


class TestSegmenter(Segmenter):
    def predict(
        self,
        pts: np.ndarray | None,
        lbls: np.ndarray | None,
        prev_mask: np.ndarray | None = None,
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        if (pts is None or len(pts) == 0) and prev_mask is None:
            return None, None
        try:
            kwargs: dict = dict(
                multimask_output=True,
            )
            if pts is not None and len(pts) > 0:
                kwargs["point_coords"] = pts
                kwargs["point_labels"] = lbls
            if prev_mask is not None:
                kwargs["mask_input"] = prev_mask[None]
                if pts is None or len(pts) == 0:
                    kwargs["multimask_output"] = False

            with torch.inference_mode(), torch.autocast(DEVICE, dtype=DTYPE):
                masks, scores, low_res = self._predictor.predict(**kwargs)

            if isinstance(masks, torch.Tensor):
                masks = masks.cpu().numpy()
            if isinstance(scores, torch.Tensor):
                scores = scores.cpu().numpy()
            if isinstance(low_res, torch.Tensor):
                low_res = low_res.cpu().numpy()

            # Cast masks to boolean to ensure they can be used for array indexing in NumPy
            masks = masks.astype(bool)

            if kwargs["multimask_output"]:
                best = int(np.argmax(scores))
                return masks[best], low_res[best]
            else:
                return masks[0], low_res[0]

        except Exception as e:
            msg = f"[SAM2 error] {e}"
            print(msg)
            traceback.print_exc()
            self._last_error = str(e)
            return None, None

try:
    segmenter = TestSegmenter()
    # Create dummy images
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[100:200, 100:200, :] = 255 # white square

    img2 = np.zeros((480, 640, 3), dtype=np.uint8)
    img2[110:210, 110:210, :] = 255 # shifted square

    # 1. Segment with points only
    segmenter.set_image(img)
    pts = np.array([[150, 150]], dtype=np.float32)
    lbls = np.array([1], dtype=np.int32)
    print("Test 1: Predicting first frame with points only...")
    mask, low_res = segmenter.predict(pts, lbls)
    print("Test 1 Result: Mask type:", type(mask), "dtype:", mask.dtype if mask is not None else None)
    if mask is not None:
        print("Unique values in mask:", np.unique(mask)[:20])

    
    # Try indexing
    colored = np.zeros_like(img)
    try:
        colored[mask] = [0, 255, 0]
        print("Test 1 Indexing: SUCCESS")
    except Exception as e:
        print("Test 1 Indexing: FAILED with error:", e)

    # 2. Track with prev_mask only
    segmenter.set_image(img2)
    print("Test 2: Predicting second frame with prev_mask only...")
    mask2, low_res2 = segmenter.predict(None, None, prev_mask=low_res)
    print("Test 2 Result: Mask shape:", mask2.shape if mask2 is not None else None, 
          "Low res shape:", low_res2.shape if low_res2 is not None else None)
    try:
        colored[mask2] = [0, 255, 0]
        print("Test 2 Indexing: SUCCESS")
    except Exception as e:
        print("Test 2 Indexing: FAILED with error:", e)


    # 3. Correct with points AND prev_mask
    print("Test 3: Predicting second frame with points AND prev_mask...")
    pts2 = np.array([[160, 160]], dtype=np.float32)
    lbls2 = np.array([1], dtype=np.int32)
    mask3, low_res3 = segmenter.predict(pts2, lbls2, prev_mask=low_res)
    print("Test 3 Result: Mask shape:", mask3.shape if mask3 is not None else None, 
          "Low res shape:", low_res3.shape if low_res3 is not None else None)

except Exception as e:
    traceback.print_exc()
