#!/usr/bin/env python3
"""
Automated Model Downloader & Offline Manager
Downloads INT8 quantized CTranslate2 models for offline STT and Translation:
1. NLLB-200 INT8 Translation Model (Meta NLLB-200 quantized)
2. Faster-Whisper STT Model
"""

import os
import sys

def download_nllb_model(target_dir: str = "models/nllb-200-int8") -> bool:
    """Downloads CTranslate2 NLLB-200 INT8 model weights from HuggingFace."""
    print(f"[ModelDownloader] Checking NLLB-200 INT8 translation model at {target_dir}...")
    if os.path.exists(target_dir) and os.path.exists(os.path.join(target_dir, "model.bin")):
        print(f"[ModelDownloader] NLLB-200 INT8 model already present at {target_dir}.")
        return True

    os.makedirs(target_dir, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download
        print("[ModelDownloader] Downloading NLLB-200 INT8 model snapshot...")
        snapshot_download(
            repo_id="ctranslate2-4u/nllb-200-distilled-600M-int8",
            local_dir=target_dir,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot", "*.onnx"],
        )
        print(f"[ModelDownloader] Successfully downloaded NLLB-200 model to {target_dir}")
        return True
    except Exception as err:
        print(f"[ModelDownloader] Model download error (falling back to lightweight engine): {err}")
        return False

def download_whisper_model(model_size: str = "tiny") -> bool:
    """Pre-caches Faster-Whisper STT model."""
    print(f"[ModelDownloader] Checking Faster-Whisper '{model_size}' model...")
    try:
        from faster_whisper import WhisperModel
        # Instant initialization downloads model to huggingface cache if missing
        WhisperModel(model_size, device="cpu", compute_type="int8")
        print(f"[ModelDownloader] Faster-Whisper '{model_size}' model ready.")
        return True
    except Exception as err:
        print(f"[ModelDownloader] Whisper download notice: {err}")
        return False

if __name__ == "__main__":
    print("=== Personal Voice Translation Model Manager ===")
    nllb_ok = download_nllb_model()
    whisper_ok = download_whisper_model("tiny")
    if nllb_ok and whisper_ok:
        print("=== All neural model weights ready for 100% offline local execution ===")
        sys.exit(0)
    else:
        print("=== Model download complete (system will use fallback if weights incomplete) ===")
        sys.exit(0)
