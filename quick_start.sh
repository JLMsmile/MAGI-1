#!/bin/bash
# MAGI-1 快速启动脚本

echo "🎬 MAGI-1 视频生成器 - 快速启动"
echo "=================================="
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python 3.10+"
    exit 1
fi

# 选择界面类型
echo "请选择要启动的界面："
echo "1) Gradio Web界面 (推荐) - 功能丰富，界面美观"
echo "2) Flask Web界面 (轻量级) - 简单快速，占用资源少"
echo "3) 命令行模式 - 直接运行示例"
echo ""
read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🚀 启动Gradio Web界面..."
        
        # 检查Gradio是否安装
        if ! python3 -c "import gradio" 2>/dev/null; then
            echo "📦 正在安装Gradio依赖..."
            bash install_web_interface.sh
        fi
        
        echo "🌐 正在启动Web服务..."
        python3 web_interface.py
        ;;
        
    2)
        echo ""
        echo "🚀 启动Flask Web界面..."
        
        # 检查Flask是否安装
        if ! python3 -c "import flask" 2>/dev/null; then
            echo "📦 正在安装Flask依赖..."
            bash install_flask_interface.sh
        fi
        
        echo "🌐 正在启动Web服务..."
        python3 simple_web_interface.py
        ;;
        
    3)
        echo ""
        echo "🚀 启动命令行模式..."
        echo "请选择要运行的模型："
        echo "1) 4.5B 模型 (推荐)"
        echo "2) 24B 模型"
        echo ""
        read -p "请输入选择 (1-2): " model_choice
        
        case $model_choice in
            1)
                echo "🎬 运行4.5B模型示例..."
                bash example/4.5B/run.sh
                ;;
            2)
                echo "🎬 运行24B模型示例..."
                bash example/24B/run.sh
                ;;
            *)
                echo "❌ 无效选择"
                exit 1
                ;;
        esac
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac