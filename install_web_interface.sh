#!/bin/bash
# MAGI-1 Web界面安装脚本

echo "🚀 开始安装MAGI-1 Web界面依赖..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python 3.10+"
    exit 1
fi

echo "✅ 检测到Python环境"

# 安装Gradio
echo "📦 正在安装Gradio..."
pip install gradio==4.44.0

# 检查是否安装成功
if python3 -c "import gradio" 2>/dev/null; then
    echo "✅ Gradio安装成功"
else
    echo "❌ Gradio安装失败"
    exit 1
fi

# 创建输出目录
echo "📁 创建输出目录..."
mkdir -p outputs

echo "🎉 安装完成！"
echo ""
echo "使用方法："
echo "1. 确保已下载MAGI-1模型权重"
echo "2. 运行: python3 web_interface.py"
echo "3. 在浏览器中打开: http://localhost:7860"
echo ""
echo "注意事项："
echo "- 首次使用需要先加载模型（可能需要几分钟）"
echo "- 确保有足够的GPU显存（4.5B模型需要24GB+）"
echo "- 生成视频需要较长时间，请耐心等待"