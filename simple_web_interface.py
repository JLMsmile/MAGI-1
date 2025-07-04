#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGI-1 简单Web界面
基于Flask的MAGI-1视频生成Web界面
"""

import os
import sys
import json
import uuid
import tempfile
from datetime import datetime
from pathlib import Path
import threading
import queue

# 添加项目路径
MAGI_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MAGI_ROOT)

# Flask相关导入
try:
    from flask import Flask, render_template, request, jsonify, send_file, url_for
    from werkzeug.utils import secure_filename
except ImportError:
    print("❌ 请安装Flask: pip install flask")
    sys.exit(1)

# MAGI-1相关导入
try:
    from inference.pipeline import MagiPipeline
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保MAGI-1依赖已正确安装")
    sys.exit(1)


class MagiWebApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'magi-web-interface'
        
        # 配置文件路径
        self.config_paths = {
            "4.5B Base": "example/4.5B/4.5B_base_config.json",
            "24B Base": "example/24B/24B_base_config.json",
            "24B Distill": "example/24B/24B_distill_config.json",
            "24B Distill+Quant": "example/24B/24B_distill_quant_config.json"
        }
        
        # 当前加载的模型
        self.current_pipeline = None
        self.current_model_name = None
        
        # 输出和上传目录
        self.output_dir = Path("outputs")
        self.upload_dir = Path("uploads")
        self.output_dir.mkdir(exist_ok=True)
        self.upload_dir.mkdir(exist_ok=True)
        
        # 生成状态
        self.generation_status = {"status": "idle", "message": "等待生成..."}
        self.generation_queue = queue.Queue()
        
        self.setup_routes()
    
    def setup_routes(self):
        """设置Flask路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            return render_template('index.html', models=list(self.config_paths.keys()))
        
        @self.app.route('/load_model', methods=['POST'])
        def load_model():
            """加载模型"""
            try:
                model_name = request.json.get('model_name')
                
                if model_name == self.current_model_name:
                    return jsonify({"success": True, "message": f"模型 {model_name} 已加载"})
                
                config_path = self.config_paths.get(model_name)
                if not config_path or not os.path.exists(config_path):
                    return jsonify({"success": False, "message": f"配置文件不存在: {config_path}"})
                
                # 加载模型
                self.current_pipeline = MagiPipeline(config_path)
                self.current_model_name = model_name
                
                return jsonify({"success": True, "message": f"模型 {model_name} 加载成功!"})
                
            except Exception as e:
                return jsonify({"success": False, "message": f"模型加载失败: {str(e)}"})
        
        @self.app.route('/generate', methods=['POST'])
        def generate():
            """生成视频"""
            try:
                if not self.current_pipeline:
                    return jsonify({"success": False, "message": "请先加载模型!"})
                
                # 获取参数
                data = request.form
                files = request.files
                
                mode = data.get('mode', 't2v')
                prompt = data.get('prompt', '').strip()
                
                if not prompt:
                    return jsonify({"success": False, "message": "请输入文本描述!"})
                
                # 更新配置
                self._update_pipeline_config(data)
                
                # 生成唯一文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                output_filename = f"magi_{mode}_{timestamp}_{unique_id}.mp4"
                output_path = self.output_dir / output_filename
                
                # 异步生成视频
                thread = threading.Thread(
                    target=self._generate_video_thread,
                    args=(mode, prompt, files, output_path)
                )
                thread.start()
                
                return jsonify({
                    "success": True, 
                    "message": "开始生成视频...",
                    "output_filename": output_filename
                })
                
            except Exception as e:
                return jsonify({"success": False, "message": f"生成失败: {str(e)}"})
        
        @self.app.route('/status')
        def get_status():
            """获取生成状态"""
            return jsonify(self.generation_status)
        
        @self.app.route('/download/<filename>')
        def download_video(filename):
            """下载生成的视频"""
            file_path = self.output_dir / filename
            if file_path.exists():
                return send_file(file_path, as_attachment=True)
            else:
                return jsonify({"error": "文件不存在"}), 404
    
    def _update_pipeline_config(self, data):
        """更新pipeline配置"""
        config = self.current_pipeline.config.runtime_config
        config.video_size_w = int(data.get('width', 720))
        config.video_size_h = int(data.get('height', 720))
        config.num_frames = int(data.get('frames', 96))
        config.fps = int(data.get('fps', 24))
        config.cfg_number = float(data.get('cfg_scale', 3.0))
        config.seed = int(data.get('seed', 1234))
    
    def _generate_video_thread(self, mode, prompt, files, output_path):
        """在后台线程中生成视频"""
        try:
            self.generation_status = {"status": "generating", "message": "正在生成视频..."}
            
            if mode == 't2v':
                self.current_pipeline.run_text_to_video(
                    prompt=prompt, 
                    output_path=str(output_path)
                )
            elif mode == 'i2v':
                if 'image' not in files:
                    raise ValueError("I2V模式需要上传图像!")
                
                # 保存临时图像
                image_file = files['image']
                temp_image_path = self._save_uploaded_file(image_file, '.jpg')
                
                self.current_pipeline.run_image_to_video(
                    prompt=prompt,
                    image_path=temp_image_path,
                    output_path=str(output_path)
                )
            elif mode == 'v2v':
                if 'video' not in files:
                    raise ValueError("V2V模式需要上传视频!")
                
                # 保存临时视频
                video_file = files['video']
                temp_video_path = self._save_uploaded_file(video_file, '.mp4')
                
                self.current_pipeline.run_video_to_video(
                    prompt=prompt,
                    prefix_video_path=temp_video_path,
                    output_path=str(output_path)
                )
            
            self.generation_status = {
                "status": "completed", 
                "message": f"视频生成完成! 文件: {output_path.name}"
            }
            
        except Exception as e:
            self.generation_status = {
                "status": "error", 
                "message": f"生成失败: {str(e)}"
            }
    
    def _save_uploaded_file(self, file, suffix):
        """保存上传的文件"""
        filename = secure_filename(file.filename)
        temp_filename = f"upload_{uuid.uuid4().hex}{suffix}"
        temp_path = self.upload_dir / temp_filename
        file.save(temp_path)
        return str(temp_path)
    
    def create_html_template(self):
        """创建HTML模板"""
        template_dir = Path("templates")
        template_dir.mkdir(exist_ok=True)
        
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MAGI-1 视频生成器</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .content { padding: 30px; }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            border-radius: 15px;
            border: 2px solid #f0f0f0;
        }
        .section h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }
        .form-control {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-control:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover { transform: translateY(-2px); }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .status {
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            font-weight: 500;
        }
        .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .status.info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .row { display: flex; gap: 20px; align-items: flex-end; }
        .col { flex: 1; }
        .video-preview {
            width: 100%;
            max-width: 500px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .hidden { display: none; }
        .progress {
            width: 100%;
            height: 6px;
            background: #f0f0f0;
            border-radius: 3px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 MAGI-1 视频生成器</h1>
            <p>基于MAGI-1的高质量视频生成工具</p>
        </div>
        
        <div class="content">
            <!-- 模型加载区域 -->
            <div class="section">
                <h3>🔧 模型配置</h3>
                <div class="row">
                    <div class="col">
                        <div class="form-group">
                            <label>选择模型</label>
                            <select id="modelSelect" class="form-control">
                                {% for model in models %}
                                <option value="{{ model }}">{{ model }}</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                    <div class="col">
                        <button id="loadModelBtn" class="btn">🔄 加载模型</button>
                    </div>
                </div>
                <div id="modelStatus" class="status info">⏳ 未加载模型</div>
            </div>
            
            <!-- 生成参数 -->
            <div class="section">
                <h3>⚙️ 生成参数</h3>
                <div class="row">
                    <div class="col">
                        <div class="form-group">
                            <label>宽度</label>
                            <input type="number" id="width" class="form-control" value="720" min="256" max="1024" step="64">
                        </div>
                    </div>
                    <div class="col">
                        <div class="form-group">
                            <label>高度</label>
                            <input type="number" id="height" class="form-control" value="720" min="256" max="1024" step="64">
                        </div>
                    </div>
                    <div class="col">
                        <div class="form-group">
                            <label>帧数</label>
                            <input type="number" id="frames" class="form-control" value="96" min="24" max="240" step="24">
                        </div>
                    </div>
                    <div class="col">
                        <div class="form-group">
                            <label>帧率</label>
                            <input type="number" id="fps" class="form-control" value="24" min="8" max="30">
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col">
                        <div class="form-group">
                            <label>引导强度</label>
                            <input type="number" id="cfgScale" class="form-control" value="3" min="1" max="10" step="0.5">
                        </div>
                    </div>
                    <div class="col">
                        <div class="form-group">
                            <label>随机种子</label>
                            <input type="number" id="seed" class="form-control" value="1234">
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 生成区域 -->
            <div class="section">
                <h3>🎬 视频生成</h3>
                <form id="generateForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>生成模式</label>
                        <select id="mode" class="form-control">
                            <option value="t2v">文本生成视频 (T2V)</option>
                            <option value="i2v">图像生成视频 (I2V)</option>
                            <option value="v2v">视频续写 (V2V)</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>文本描述</label>
                        <textarea id="prompt" class="form-control" rows="4" 
                                placeholder="详细描述你想要生成的视频内容...&#10;例如：一只可爱的小猫在花园里追蝴蝶，阳光明媚，画面唯美"></textarea>
                    </div>
                    
                    <div class="form-group hidden" id="imageGroup">
                        <label>上传图像</label>
                        <input type="file" id="image" class="form-control" accept="image/*">
                    </div>
                    
                    <div class="form-group hidden" id="videoGroup">
                        <label>上传视频</label>
                        <input type="file" id="video" class="form-control" accept="video/*">
                    </div>
                    
                    <button type="submit" id="generateBtn" class="btn">🎬 开始生成</button>
                </form>
                
                <div id="generateStatus" class="status info">等待开始生成...</div>
                <div class="progress hidden" id="progressBar">
                    <div class="progress-bar" style="width: 0%"></div>
                </div>
                
                <video id="outputVideo" class="video-preview hidden" controls></video>
                <div id="downloadLink" class="hidden">
                    <a href="#" class="btn" download>📥 下载视频</a>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 模式切换
        document.getElementById('mode').addEventListener('change', function() {
            const mode = this.value;
            document.getElementById('imageGroup').classList.toggle('hidden', mode !== 'i2v');
            document.getElementById('videoGroup').classList.toggle('hidden', mode !== 'v2v');
        });
        
        // 加载模型
        document.getElementById('loadModelBtn').addEventListener('click', async function() {
            const modelName = document.getElementById('modelSelect').value;
            const btn = this;
            const status = document.getElementById('modelStatus');
            
            btn.disabled = true;
            btn.textContent = '🔄 加载中...';
            status.textContent = '正在加载模型...';
            status.className = 'status info';
            
            try {
                const response = await fetch('/load_model', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model_name: modelName })
                });
                
                const result = await response.json();
                status.textContent = result.message;
                status.className = result.success ? 'status success' : 'status error';
                
            } catch (error) {
                status.textContent = '加载失败: ' + error.message;
                status.className = 'status error';
            } finally {
                btn.disabled = false;
                btn.textContent = '🔄 加载模型';
            }
        });
        
        // 生成视频
        document.getElementById('generateForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            const prompt = document.getElementById('prompt').value.trim();
            
            if (!prompt) {
                alert('请输入文本描述!');
                return;
            }
            
            // 添加所有参数
            formData.append('mode', document.getElementById('mode').value);
            formData.append('prompt', prompt);
            formData.append('width', document.getElementById('width').value);
            formData.append('height', document.getElementById('height').value);
            formData.append('frames', document.getElementById('frames').value);
            formData.append('fps', document.getElementById('fps').value);
            formData.append('cfg_scale', document.getElementById('cfgScale').value);
            formData.append('seed', document.getElementById('seed').value);
            
            // 添加文件
            const mode = document.getElementById('mode').value;
            if (mode === 'i2v') {
                const imageFile = document.getElementById('image').files[0];
                if (imageFile) formData.append('image', imageFile);
            } else if (mode === 'v2v') {
                const videoFile = document.getElementById('video').files[0];
                if (videoFile) formData.append('video', videoFile);
            }
            
            const btn = document.getElementById('generateBtn');
            const status = document.getElementById('generateStatus');
            const progress = document.getElementById('progressBar');
            
            btn.disabled = true;
            btn.textContent = '🎬 生成中...';
            status.textContent = '正在准备生成...';
            status.className = 'status info';
            progress.classList.remove('hidden');
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    status.textContent = result.message;
                    status.className = 'status info';
                    
                    // 轮询状态
                    const filename = result.output_filename;
                    pollStatus(filename);
                } else {
                    status.textContent = result.message;
                    status.className = 'status error';
                    btn.disabled = false;
                    btn.textContent = '🎬 开始生成';
                    progress.classList.add('hidden');
                }
                
            } catch (error) {
                status.textContent = '生成失败: ' + error.message;
                status.className = 'status error';
                btn.disabled = false;
                btn.textContent = '🎬 开始生成';
                progress.classList.add('hidden');
            }
        });
        
        // 轮询生成状态
        async function pollStatus(filename) {
            const status = document.getElementById('generateStatus');
            const btn = document.getElementById('generateBtn');
            const progress = document.getElementById('progressBar');
            
            try {
                const response = await fetch('/status');
                const result = await response.json();
                
                status.textContent = result.message;
                
                if (result.status === 'completed') {
                    status.className = 'status success';
                    btn.disabled = false;
                    btn.textContent = '🎬 开始生成';
                    progress.classList.add('hidden');
                    
                    // 显示视频
                    const video = document.getElementById('outputVideo');
                    const downloadLink = document.getElementById('downloadLink');
                    
                    video.src = '/download/' + filename;
                    video.classList.remove('hidden');
                    
                    downloadLink.querySelector('a').href = '/download/' + filename;
                    downloadLink.classList.remove('hidden');
                    
                } else if (result.status === 'error') {
                    status.className = 'status error';
                    btn.disabled = false;
                    btn.textContent = '🎬 开始生成';
                    progress.classList.add('hidden');
                } else {
                    // 继续轮询
                    setTimeout(() => pollStatus(filename), 2000);
                }
                
            } catch (error) {
                console.error('轮询状态失败:', error);
                setTimeout(() => pollStatus(filename), 5000);
            }
        }
    </script>
</body>
</html>
        """
        
        with open(template_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def run(self, host='0.0.0.0', port=7860, debug=True):
        """运行Web应用"""
        self.create_html_template()
        print(f"🌐 启动MAGI-1 Web界面...")
        print(f"📱 访问地址: http://localhost:{port}")
        print(f"🔧 使用说明:")
        print(f"   1. 首先选择并加载模型")
        print(f"   2. 输入文本描述")
        print(f"   3. 根据需要调整参数")
        print(f"   4. 点击开始生成")
        
        self.app.run(host=host, port=port, debug=debug)


def main():
    """主函数"""
    web_app = MagiWebApp()
    web_app.run()


if __name__ == "__main__":
    main()