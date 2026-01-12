# GPU Setup Guide

## Summary

Your models are now configured to use GPU acceleration when available. Here's what was done:

## ✅ What Was Fixed

1. **Removed CPU-forcing settings**: Removed `CUDA_VISIBLE_DEVICES = '-1'` that was forcing CPU usage
2. **Added GPU detection**: Both Intent Classifier and Semantic Search now automatically detect and use GPU
3. **Installed CUDA-enabled PyTorch**: Upgraded from CPU-only PyTorch to PyTorch 2.5.1 with CUDA 12.1 support
4. **Enhanced logging**: Added device status reporting in startup summary

## 🖥️ Your GPU Configuration

- **GPU**: NVIDIA GeForce GTX 1650
- **CUDA Version**: 12.1
- **PyTorch Version**: 2.5.1+cu121 (CUDA-enabled)

## 📋 Models That Use GPU

1. **Intent Classifier** (`src/nlp_intent_classifier.py`)
   - Uses transformers library (BART-large-mnli for zero-shot classification)
   - Automatically detects and uses GPU if available

2. **Semantic Search** (`src/nlp_semantic_search.py`)
   - Uses sentence-transformers (all-MiniLM-L6-v2)
   - Automatically detects and uses GPU if available

## 🔍 How to Verify GPU Usage

Run the GPU check script:
```powershell
.\venv\Scripts\python.exe check_gpu.py
```

When you start the server, you should now see in the startup summary:
```
✓ Intent Classifier (device: cuda)
✓ Semantic search (device: cuda)
✓ GPU Available: NVIDIA GeForce GTX 1650
```

## ⚠️ If GPU Still Shows as CPU

1. **Check NVIDIA drivers**: Ensure you have the latest NVIDIA drivers installed
2. **Verify CUDA**: Run `nvidia-smi` in command prompt to see if CUDA is detected
3. **Check PyTorch**: Run `python check_gpu.py` to verify PyTorch can see your GPU

## 🚀 Performance Notes

- GPU will significantly speed up model inference, especially for:
  - Intent classification (transformer models)
  - Semantic search embeddings
- If GPU is not available, models automatically fall back to CPU
- First model load may take longer as models are moved to GPU memory

## 📝 Files Modified

- `src/query_preprocessing.py` - Removed CPU-forcing environment variable
- `src/query_preprocessing_v2.py` - Removed CPU-forcing environment variable
- `src/nlp_intent_classifier.py` - Added GPU device logging
- `src/nlp_semantic_search.py` - Added GPU device detection and configuration
- `django_app/views.py` - Added GPU status to startup summary

## 🔧 Troubleshooting

If you see "Device set to use cpu":
1. Make sure you're using the virtual environment: `.\venv\Scripts\python.exe`
2. Verify PyTorch CUDA support: `python check_gpu.py`
3. Check that NVIDIA drivers are up to date
4. Restart your server after GPU installation
