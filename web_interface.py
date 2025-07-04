#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGI-1 Web Interface
基于Gradio的MAGI-1视频生成Web界面
"""

import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
import gradio as gr
import json

# 添加项目路径到Python路径
MAGI_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MAGI_ROOT)

try:
    from inference.pipeline import MagiPipeline
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保MAGI-1依赖已正确安装")
    sys.exit(1)


class MagiWebInterface:
    def __init__(self):
        self.pipeline_4_5b = None
        self.pipeline_24b = None
        self.current_model = None
        
        # 预设配置文件路径
        self.config_paths = {
            "4.5B Base": "example/4.5B/4.5B_base_config.json",
            "24B Base": "example/24B/24B_base_config.json", 
            "24B Distill": "example/24B/24B_distill_config.json",
            "24B Distill+Quant": "example/24B/24B_distill_quant_config.json"
        }
        
        # 输出目录
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
    
    def load_model(self, model_name, progress=gr.Progress()):
        """加载指定模型"""
        try:
            config_path = self.config_paths.get(model_name)
            if not config_path or not os.path.exists(config_path):
                return f"❌ 配置文件不存在: {config_path}"
            
            progress(0.1, desc="正在初始化模型...")
            
            # 检查是否已加载相同模型
            if self.current_model == model_name:
                return f"✅ 模型 {model_name} 已加载"
            
            progress(0.3, desc="正在加载模型权重...")
            
            # 加载新模型
            pipeline = MagiPipeline(config_path)
            
            if "4.5B" in model_name:
                self.pipeline_4_5b = pipeline
            else:
                self.pipeline_24b = pipeline
                
            self.current_model = model_name
            
            progress(1.0, desc="模型加载完成!")
            return f"✅ 模型 {model_name} 加载成功!"
            
        except Exception as e:
            return f"❌ 模型加载失败: {str(e)}"
    
    def get_current_pipeline(self):
        """获取当前活跃的pipeline"""
        if self.current_model and "4.5B" in self.current_model:
            return self.pipeline_4_5b
        else:
            return self.pipeline_24b
    
    def generate_video(self, mode, prompt, image, video, model_name, 
                      video_width, video_height, num_frames, fps, 
                      cfg_scale, seed, progress=gr.Progress()):
        """生成视频的主函数"""
        try:
            # 检查模型是否已加载
            if not self.current_model:
                return None, "❌ 请先加载模型!"
            
            if not prompt.strip():
                return None, "❌ 请输入文本描述!"
            
            progress(0.1, desc="正在准备生成参数...")
            
            # 获取当前pipeline
            pipeline = self.get_current_pipeline()
            if not pipeline:
                return None, f"❌ 模型 {self.current_model} 未正确加载!"
            
            # 更新配置参数
            self._update_config(pipeline, video_width, video_height, num_frames, fps, cfg_scale, seed)
            
            # 生成唯一的输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            output_filename = f"magi_{mode}_{timestamp}_{unique_id}.mp4"
            output_path = self.output_dir / output_filename
            
            progress(0.2, desc="正在生成视频...")
            
            # 根据模式调用相应的生成函数
            if mode == "文本生成视频 (T2V)":
                progress(0.3, desc="正在从文本生成视频...")
                pipeline.run_text_to_video(prompt=prompt, output_path=str(output_path))
                
            elif mode == "图像生成视频 (I2V)":
                if image is None:
                    return None, "❌ I2V模式需要上传图像!"
                
                progress(0.3, desc="正在从图像生成视频...")
                # 保存临时图像文件
                temp_image = self._save_temp_file(image, suffix=".jpg")
                pipeline.run_image_to_video(
                    prompt=prompt, 
                    image_path=temp_image, 
                    output_path=str(output_path)
                )
                
            elif mode == "视频续写 (V2V)":
                if video is None:
                    return None, "❌ V2V模式需要上传视频!"
                
                progress(0.3, desc="正在续写视频...")
                # 保存临时视频文件
                temp_video = self._save_temp_file(video, suffix=".mp4")
                pipeline.run_video_to_video(
                    prompt=prompt,
                    prefix_video_path=temp_video,
                    output_path=str(output_path)
                )
            
            progress(1.0, desc="视频生成完成!")
            
            if output_path.exists():
                return str(output_path), f"✅ 视频生成成功! 保存至: {output_filename}"
            else:
                return None, "❌ 视频生成失败，输出文件未找到"
                
        except Exception as e:
            return None, f"❌ 生成过程中出错: {str(e)}"
    
    def _update_config(self, pipeline, width, height, frames, fps, cfg, seed):
        """更新模型配置参数"""
        config = pipeline.config.runtime_config
        config.video_size_w = width
        config.video_size_h = height
        config.num_frames = frames
        config.fps = fps
        config.cfg_number = cfg
        config.seed = seed
    
    def _save_temp_file(self, file_path, suffix):
        """保存临时文件"""
        temp_dir = tempfile.gettempdir()
        temp_filename = f"magi_temp_{uuid.uuid4().hex}{suffix}"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        # 复制文件
        import shutil
        shutil.copy2(file_path, temp_path)
        return temp_path
    
    def create_interface(self):
        """创建Gradio界面"""
        
        # CSS样式
        css = """
        .gradio-container {
            max-width: 1200px !important;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .model-info {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .status-box {
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        """
        
        with gr.Blocks(css=css, title="MAGI-1 视频生成器", theme=gr.themes.Soft()) as interface:
            
            # 标题和介绍
            gr.HTML("""
            <div class="header">
                <h1>🎬 MAGI-1 视频生成器</h1>
                <p style="font-size: 18px; color: #666;">
                    基于MAGI-1的高质量视频生成工具<br>
                    支持文本生成视频、图像生成视频、视频续写三种模式
                </p>
            </div>
            """)
            
            # 模型信息面板
            with gr.Row():
                gr.HTML("""
                <div class="model-info">
                    <h3>🚀 模型特性</h3>
                    <ul>
                        <li><strong>4.5B模型</strong>: 适合RTX 4090等消费级显卡 (24GB+显存)</li>
                        <li><strong>24B模型</strong>: 适合H100/H800等专业显卡 (需要更多显存)</li>
                        <li><strong>多种模式</strong>: T2V文本生成视频、I2V图像生成视频、V2V视频续写</li>
                        <li><strong>高质量输出</strong>: 支持最高720p分辨率，24fps流畅播放</li>
                    </ul>
                </div>
                """)
            
            with gr.Row():
                # 左侧：模型选择和加载
                with gr.Column(scale=1):
                    gr.Markdown("### 🔧 模型配置")
                    
                    model_choice = gr.Dropdown(
                        choices=list(self.config_paths.keys()),
                        value="4.5B Base",
                        label="选择模型",
                        info="推荐大多数用户使用4.5B Base模型"
                    )
                    
                    load_btn = gr.Button("🔄 加载模型", variant="primary", size="lg")
                    model_status = gr.Textbox(
                        label="模型状态", 
                        value="⏳ 未加载模型",
                        interactive=False
                    )
                
                # 右侧：生成参数
                with gr.Column(scale=1):
                    gr.Markdown("### ⚙️ 生成参数")
                    
                    with gr.Row():
                        video_width = gr.Slider(256, 1024, value=720, step=64, label="宽度")
                        video_height = gr.Slider(256, 1024, value=720, step=64, label="高度")
                    
                    with gr.Row():
                        num_frames = gr.Slider(24, 240, value=96, step=24, label="帧数", info="更多帧=更长视频")
                        fps = gr.Slider(8, 30, value=24, step=2, label="帧率")
                    
                    with gr.Row():
                        cfg_scale = gr.Slider(1, 10, value=3, step=0.5, label="引导强度", info="控制提示词遵循度")
                        seed = gr.Number(value=1234, label="随机种子", info="相同种子产生相同结果")
            
            gr.Markdown("---")
            
            # 主要生成区域
            with gr.Row():
                # 左侧：输入控制
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 输入设置")
                    
                    mode = gr.Radio(
                        choices=["文本生成视频 (T2V)", "图像生成视频 (I2V)", "视频续写 (V2V)"],
                        value="文本生成视频 (T2V)",
                        label="生成模式"
                    )
                    
                    prompt = gr.Textbox(
                        label="文本描述",
                        placeholder="详细描述你想要生成的视频内容...\n例如：一只可爱的小猫在花园里追蝴蝶，阳光明媚，画面唯美",
                        lines=4,
                        max_lines=6
                    )
                    
                    # 条件输入（根据模式显示）
                    image_input = gr.File(
                        label="上传图像 (I2V模式)",
                        file_types=["image"],
                        visible=False
                    )
                    
                    video_input = gr.File(
                        label="上传视频 (V2V模式)", 
                        file_types=["video"],
                        visible=False
                    )
                    
                    generate_btn = gr.Button("🎬 开始生成", variant="primary", size="lg")
                
                # 右侧：输出显示
                with gr.Column(scale=1):
                    gr.Markdown("### 🎥 生成结果")
                    
                    output_video = gr.Video(
                        label="生成的视频",
                        height=400
                    )
                    
                    generation_status = gr.Textbox(
                        label="生成状态",
                        value="等待开始生成...",
                        interactive=False
                    )
            
            # 示例和帮助
            gr.Markdown("---")
            with gr.Accordion("💡 使用示例和提示", open=False):
                gr.Markdown("""
                ### 文本提示示例：
                - **自然场景**: "一片宁静的湖泊，微风轻抚水面，远山如黛，白云悠悠"
                - **动物视频**: "一只金毛犬在海边奔跑，浪花飞溅，夕阳西下"
                - **科幻场景**: "未来城市夜景，霓虹灯闪烁，飞车穿梭在高楼之间"
                - **抽象艺术**: "色彩斑斓的粒子在空中舞动，形成美丽的图案"
                
                ### 使用技巧：
                1. **详细描述**: 提供越详细的描述，生成效果越好
                2. **风格描述**: 可以添加"电影级"、"4K"、"唯美"等修饰词
                3. **动作描述**: 明确描述想要的动作和变化
                4. **参数调整**: 根据显卡性能调整分辨率和帧数
                """)
            
            # 事件绑定
            
            # 模型加载
            load_btn.click(
                fn=self.load_model,
                inputs=[model_choice],
                outputs=[model_status]
            )
            
            # 模式切换时更新界面
            def update_inputs(mode_value):
                return {
                    image_input: gr.update(visible="I2V" in mode_value),
                    video_input: gr.update(visible="V2V" in mode_value)
                }
            
            mode.change(
                fn=update_inputs,
                inputs=[mode],
                outputs=[image_input, video_input]
            )
            
            # 视频生成
            generate_btn.click(
                fn=self.generate_video,
                inputs=[
                    mode, prompt, image_input, video_input, model_choice,
                    video_width, video_height, num_frames, fps, cfg_scale, seed
                ],
                outputs=[output_video, generation_status]
            )
        
        return interface


def main():
    """主函数"""
    print("🚀 启动MAGI-1 Web界面...")
    
    # 检查依赖
    try:
        import gradio
        print("✅ Gradio已安装")
    except ImportError:
        print("❌ 请安装Gradio: pip install gradio")
        return
    
    # 创建Web界面
    web_interface = MagiWebInterface()
    interface = web_interface.create_interface()
    
    # 启动服务
    print("🌐 启动Web服务...")
    interface.launch(
        server_name="0.0.0.0",  # 允许外部访问
        server_port=7860,       # 端口
        share=False,            # 不使用Gradio公共链接
        debug=True,             # 开启调试模式
        show_error=True         # 显示错误信息
    )


if __name__ == "__main__":
    main()