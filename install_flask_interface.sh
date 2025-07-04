#!/bin/bash
# MAGI-1 Flask Web界面安装脚本

echo "🚀 开始安装MAGI-1 Flask Web界面依赖..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python 3.10+"
    exit 1
fi

echo "✅ 检测到Python环境"

# 安装Flask
echo "📦 正在安装Flask和相关依赖..."
pip install flask==2.3.3 werkzeug==2.3.7

# 检查是否安装成功
if python3 -c "import flask, werkzeug" 2>/dev/null; then
    echo "✅ Flask安装成功"
else
    echo "❌ Flask安装失败"
    exit 1
fi

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p outputs uploads templates

echo "🎉 安装完成！"
echo ""
echo "使用方法："
echo "1. 确保已下载MAGI-1模型权重"
echo "2. 运行: python3 simple_web_interface.py"
echo "3. 在浏览器中打开: http://localhost:7860"
echo ""
echo "注意事项："
echo "- 首次使用需要先加载模型（可能需要几分钟）"
echo "- 确保有足够的GPU显存（4.5B模型需要24GB+）"
echo "- 生成视频需要较长时间，请耐心等待"
echo "- Web界面会自动创建HTML模板文件"