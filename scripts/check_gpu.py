#!/usr/bin/env python
"""
GPU Detection Script - Check if CUDA/GPU is available for PyTorch models
"""
import sys

def check_gpu_availability():
    """Check GPU/CUDA availability for PyTorch and TensorFlow"""
    print("=" * 60)
    print("GPU Availability Check")
    print("=" * 60)
    print()
    
    # Check PyTorch
    try:
        import torch
        print("[OK] PyTorch is installed")
        print(f"  Version: {torch.__version__}")
        
        if torch.cuda.is_available():
            print("[OK] CUDA is available!")
            print(f"  CUDA Version: {torch.version.cuda}")
            print(f"  GPU Device: {torch.cuda.get_device_name(0)}")
            print(f"  Number of GPUs: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"    GPU {i}: {torch.cuda.get_device_name(i)}")
        else:
            print("[X] CUDA is NOT available")
            print("  PyTorch will use CPU")
            print()
            print("To enable GPU support, install PyTorch with CUDA:")
            if sys.platform == 'win32':
                print("  Visit: https://pytorch.org/get-started/locally/")
                print("  Select: Windows, CUDA (your version), Pip")
                print("  Example for CUDA 11.8:")
                print("    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
                print("  Example for CUDA 12.1:")
                print("    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
            else:
                print("  Visit: https://pytorch.org/get-started/locally/")
        print()
    except ImportError:
        print("[X] PyTorch is NOT installed")
        print("  Install with: pip install torch")
        print()
    
    # Check sentence-transformers (uses PyTorch)
    try:
        from sentence_transformers import SentenceTransformer
        print("[OK] sentence-transformers is installed")
    except ImportError:
        print("[X] sentence-transformers is NOT installed")
        print("  Install with: pip install sentence-transformers")
        print()
    
    # Check transformers
    try:
        import transformers
        print(f"[OK] transformers is installed (version: {transformers.__version__})")
    except ImportError:
        print("[X] transformers is NOT installed")
        print("  Install with: pip install transformers")
        print()
    
    print("=" * 60)
    print()
    
    # Summary
    try:
        import torch
        if torch.cuda.is_available():
            print("[OK] RESULT: GPU will be used for models")
            return True
        else:
            print("[WARNING] RESULT: CPU will be used (GPU not available)")
            return False
    except ImportError:
        print("[WARNING] RESULT: Cannot determine (PyTorch not installed)")
        return False

if __name__ == '__main__':
    check_gpu_availability()
