# How to Run MAGI-1 Project

MAGI-1 is an autoregressive video generation model that can generate videos from text prompts, images, or other videos. This guide will help you set up and run the project.

## What is MAGI-1?

MAGI-1 is a state-of-the-art video generation model that:
- Generates videos autoregressively by predicting chunks of frames
- Supports text-to-video (T2V), image-to-video (I2V), and video-to-video (V2V) generation
- Available in 24B and 4.5B parameter variants
- Offers distilled and quantized versions for faster inference

## Prerequisites

- **Hardware Requirements:**
  - **4.5B Model**: RTX 4090 × 1 (minimum 24GB GPU memory)
  - **24B Model**: H100/H800 × 8 (or RTX 4090 × 8 with adjusted config)
- **Software**: Docker (recommended) or Python 3.10.12 with CUDA support

## Quick Start

### Method 1: Docker (Recommended)

1. **Pull and run the Docker container:**
```bash
docker pull sandai/magi:latest

docker run -it --gpus all --privileged --shm-size=32g --name magi --net=host --ipc=host --ulimit memlock=-1 --ulimit stack=6710886 sandai/magi:latest /bin/bash
```

2. **Download the model weights** (inside the container):
```bash
# You'll need to download the model weights from Hugging Face
# Links are provided in the README.md Model Zoo section
```

### Method 2: Source Installation

1. **Create environment:**
```bash
conda create -n magi python==3.10.12
conda activate magi
```

2. **Install dependencies:**
```bash
# Install PyTorch
conda install pytorch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 pytorch-cuda=12.4 -c pytorch -c nvidia

# Install other dependencies
pip install -r requirements.txt

# Install ffmpeg
conda install -c conda-forge ffmpeg=4.4
```

3. **Optional: Install MagiAttention (for H100/H800 GPUs):**
```bash
git clone git@github.com:SandAI-org/MagiAttention.git
cd MagiAttention
git submodule update --init --recursive
pip install --no-build-isolation .
```

## Running the Model

### Available Models

| Model | GPU Requirements | Config File |
|-------|------------------|-------------|
| MAGI-1-4.5B | RTX 4090 × 1 | `example/4.5B/4.5B_base_config.json` |
| MAGI-1-24B | H100/H800 × 8 | `example/24B/24B_base_config.json` |
| MAGI-1-24B-distill | H100/H800 × 8 | `example/24B/24B_distill_config.json` |
| MAGI-1-24B-distill+quant | H100/H800 × 4 or RTX 4090 × 8 | `example/24B/24B_distill_quant_config.json` |

### Basic Usage

1. **Run 4.5B model (recommended for most users):**
```bash
bash example/4.5B/run.sh
```

2. **Run 24B model:**
```bash
bash example/24B/run.sh
```

### Generation Modes

#### Text-to-Video (T2V)
```bash
python3 inference/pipeline/entry.py \
    --config_file example/4.5B/4.5B_base_config.json \
    --mode t2v \
    --prompt "A cat playing with a ball of yarn" \
    --output_path output_video.mp4
```

#### Image-to-Video (I2V)
```bash
python3 inference/pipeline/entry.py \
    --config_file example/4.5B/4.5B_base_config.json \
    --mode i2v \
    --prompt "The image comes to life with gentle movement" \
    --image_path path/to/your/image.jpg \
    --output_path output_video.mp4
```

#### Video-to-Video (V2V)
```bash
python3 inference/pipeline/entry.py \
    --config_file example/4.5B/4.5B_base_config.json \
    --mode v2v \
    --prompt "Continue the video with dramatic action" \
    --prefix_video_path path/to/your/video.mp4 \
    --output_path output_video.mp4
```

## Configuration Options

Key parameters you can modify in the config files:

| Parameter | Description | Default (4.5B) |
|-----------|-------------|----------------|
| `seed` | Random seed for reproducibility | 1234 |
| `video_size_h` | Video height | 720 |
| `video_size_w` | Video width | 720 |
| `num_frames` | Video duration in frames | 96 |
| `fps` | Frames per second | 24 |
| `cfg_number` | Guidance scale (3 for base, 1 for distill) | 3 |
| `num_steps` | Denoising steps | 64 |

## Memory Optimization Tips

### For RTX 4090 with 24B model:
Edit the config file to set:
```json
"pp_size": 2,
"cp_size": 4
```

### For lower memory usage:
- Use the 4.5B model instead of 24B
- Reduce `video_size_h` and `video_size_w`
- Reduce `num_frames` for shorter videos
- Use distilled or quantized models

## Troubleshooting

### Common Issues:

1. **Out of Memory**: Reduce video resolution or use a smaller model
2. **Model weights not found**: Ensure you've downloaded the weights to the correct path
3. **CUDA errors**: Make sure CUDA drivers are properly installed
4. **Slow inference**: Consider using distilled models or enabling optimizations

### Environment Variables:
The run scripts set these important variables:
```bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export OFFLOAD_T5_CACHE=true
export OFFLOAD_VAE_CACHE=true
```

## Expected Output

- Generated videos will be saved to the specified `--output_path`
- Default output is typically saved to `example/assets/output_t2v.mp4`
- Generation time varies based on:
  - Model size (4.5B vs 24B)
  - Video length and resolution
  - Hardware capabilities
  - Whether using distilled models

## Model Downloads

You need to download the following components:
1. **T5 Text Encoder**: `./downloads/t5_pretrained`
2. **VAE**: `./downloads/vae`
3. **Main Model**: `./downloads/4.5B_base` or `./downloads/24B_base`

Download links are available in the [Hugging Face repository](https://huggingface.co/sand-ai/MAGI-1).

## Web界面选项

除了命令行版本，我还为您创建了两种Web界面：

### 方案1：Gradio界面（推荐）
```bash
# 安装Gradio
bash install_web_interface.sh

# 运行Web界面
python3 web_interface.py
```

### 方案2：Flask界面（轻量级）
```bash
# 安装Flask
bash install_flask_interface.sh

# 运行Web界面
python3 simple_web_interface.py
```

两种界面都会在 `http://localhost:7860` 启动，提供：
- 🎯 直观的模型选择和加载
- 📝 友好的参数调整界面
- 🎬 三种生成模式（T2V/I2V/V2V）
- 📊 实时生成状态显示
- 📥 便捷的视频下载功能

## Next Steps

Once you have the model running:
- Experiment with different prompts and modes
- Adjust video resolution and length based on your hardware
- Try the distilled models for faster inference
- Explore the controllable generation features for advanced use cases
- Use the Web interface for easier parameter adjustment and file management