# -*- coding: utf-8 -*-
import os
import sys

# ==================== 【PyInstaller 修复 stdin】 ====================
if getattr(sys, "frozen", False) and sys.stdin is None:
    sys.stdin = open(os.devnull, "r")
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

import re
import subprocess

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CardWidget,
    CheckBox,
    ComboBox,
    LineEdit,
    MessageBox,
    ProgressBar,
    PushButton,
    TextEdit,
    Theme,
    setTheme,
)


# ConversionThread 类保持不变
class ConversionThread(QThread):
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    completed_signal = pyqtSignal(str)
    failed_signal = pyqtSignal(str)

    def __init__(self, cmd, output_file, duration):
        super().__init__()
        self.cmd = cmd
        self.output_file = output_file
        self.duration = duration

    def run(self):
        try:
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            for line in iter(process.stdout.readline, ""):
                if process.poll() is not None:
                    break
                line = line.strip()
                if line.startswith("out_time_ms="):
                    try:
                        time_ms = int(line.split("=")[1])
                        if self.duration > 0:
                            progress = min(
                                (time_ms / 1000000) / self.duration * 100, 100
                            )
                            self.progress_signal.emit(int(progress))
                    except:
                        pass
                if any(
                    keyword in line.lower()
                    for keyword in ["error", "warning", "frame=", "time=", "bitrate="]
                ):
                    self.log_signal.emit(f"📋 {line}")

            return_code = process.wait()
            if return_code == 0:
                self.completed_signal.emit(self.output_file)
            else:
                self.failed_signal.emit("转换过程中出现错误")
        except Exception as e:
            self.failed_signal.emit(str(e))


class FFmpegFluentApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_window()
        self.setup_directories()
        self.init_variables()
        self.create_layout()

    def setup_window(self):
        self.setWindowTitle("FFmpeg Assistant GUI")
        self.setGeometry(100, 100, 880, 900)
        self.setMinimumSize(800, 680)
        setTheme(Theme.LIGHT)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

    def init_variables(self):
        self.input_path = ""
        self.output_format = "mp4"
        self.use_gpu = True
        self.conversion_thread = None
        self.log_buffer = []
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.flush_log_buffer)
        self.log_timer.setInterval(100)
        # 帧率、分辨率的默认值
        self.frame_rate = "Same as source"
        self.resolution = "Same as source"
        # 删除了音频码率的变量初始化

    def setup_directories(self):
        self.current_dir = os.getcwd()
        self.output_dir = os.path.join(self.current_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

        self.ffmpeg_path = self.find_ffmpeg()
        if not self.ffmpeg_path:
            MessageBox(
                "错误",
                "未找到 FFmpeg。请确保 FFmpeg 已安装并在 PATH 中，或放置在应用目录下。",
                self,
            ).exec_()
            sys.exit(1)

    def find_ffmpeg(self):
        local_ffmpeg = os.path.join(self.current_dir, "ffmpeg.exe")
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
        try:
            subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            return "ffmpeg"
        except:
            return None

    def create_layout(self):
        self.create_app_header()
        self.create_input_section()
        self.create_output_settings_section()
        self.create_action_bar()
        self.create_progress_section()

    def create_app_header(self):
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 32)

        title_label = QLabel("FFmpeg Assistant GUI")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("快速转换音频、视频文件格式，支持硬件加速和批量处理")
        subtitle_label.setStyleSheet("font-size: 12px; color: #424242;")
        header_layout.addWidget(subtitle_label)

        self.main_layout.addWidget(header_widget)

    def create_input_section(self):
        input_card = CardWidget()
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(16, 16, 16, 16)

        section_title = QLabel("选择输入文件")
        section_title.setStyleSheet("font-size: 15px;")
        input_layout.addWidget(section_title)

        file_container = QWidget()
        file_layout = QHBoxLayout(file_container)
        file_layout.setContentsMargins(0, 0, 0, 12)

        self.file_entry = LineEdit()
        self.file_entry.setPlaceholderText("选择要转换的媒体文件...")
        file_layout.addWidget(self.file_entry)

        browse_button = PushButton("浏览文件")
        browse_button.clicked.connect(self.select_input_file)
        file_layout.addWidget(browse_button)

        input_layout.addWidget(file_container)

        format_hint = QLabel(
            "⚡ 支持所有主流格式：MP4, AVI, MKV, MOV, WMV, FLV, MP3, WAV, FLAC, M4A 等"
        )
        format_hint.setStyleSheet("font-size: 11px; color: #616161;")
        input_layout.addWidget(format_hint)

        self.main_layout.addWidget(input_card)

    def create_output_settings_section(self):
        settings_card = CardWidget()
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(16, 16, 16, 16)

        section_title = QLabel("输出设置")
        section_title.setStyleSheet("font-size: 15px;")
        settings_layout.addWidget(section_title)

        settings_grid = QWidget()
        grid_layout = QHBoxLayout(settings_grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        format_frame = QWidget()
        format_layout = QVBoxLayout(format_frame)
        format_label = QLabel("输出格式")
        format_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        format_layout.addWidget(format_label)

        self.format_combo = ComboBox()
        formats = [
            "mp4",
            "mkv",
            "avi",
            "mov",
            "webm",
            "gif",
            "mp3",
            "wav",
            "flac",
            "m4a",
            "aac",
            "ogg",
            "wmv",
            "flv",
            "mpeg",
            "ts",
            "vob",
            "opus",
            "wma",
            "ac3",
        ]
        self.format_combo.addItems(formats)
        self.format_combo.setCurrentText("mp4")
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo)

        format_desc = QLabel("选择目标文件格式")
        format_desc.setStyleSheet("font-size: 11px; color: #616161;")
        format_layout.addWidget(format_desc)
        grid_layout.addWidget(format_frame)

        advanced_frame = QWidget()
        advanced_layout = QVBoxLayout(advanced_frame)
        advanced_label = QLabel("高级选项")
        advanced_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        advanced_layout.addWidget(advanced_label)

        self.gpu_checkbox = CheckBox("启用 GPU 硬件加速")
        self.gpu_checkbox.setChecked(True)
        self.gpu_checkbox.stateChanged.connect(
            lambda state: setattr(self, "use_gpu", state == Qt.Checked)
        )
        advanced_layout.addWidget(self.gpu_checkbox)

        gpu_desc = QLabel("🚀 使用 NVIDIA/AMD GPU 加速转换（如果支持）")
        gpu_desc.setStyleSheet("font-size: 11px; color: #616161;")
        advanced_layout.addWidget(gpu_desc)
        grid_layout.addWidget(advanced_frame)

        settings_layout.addWidget(settings_grid)

        # 新增选项区域
        options_frame = QWidget()
        options_layout = QGridLayout(options_frame)

        # 帧率选项
        frame_rate_label = QLabel("帧率:")
        self.frame_rate_combo = ComboBox()
        self.frame_rate_combo.addItems(["Same as source", "15", "25", "30", "60"])
        self.frame_rate_combo.setCurrentText("Same as source")
        self.frame_rate_combo.currentTextChanged.connect(
            lambda text: setattr(self, "frame_rate", text)
        )
        options_layout.addWidget(frame_rate_label, 0, 0)
        options_layout.addWidget(self.frame_rate_combo, 0, 1)

        # 分辨率选项
        resolution_label = QLabel("分辨率:")
        self.resolution_combo = ComboBox()
        self.resolution_combo.addItems(
            ["Same as source", "1920x1080", "1280x720", "854x480", "640x360"]
        )
        self.resolution_combo.setCurrentText("Same as source")
        self.resolution_combo.currentTextChanged.connect(
            lambda text: setattr(self, "resolution", text)
        )
        options_layout.addWidget(resolution_label, 1, 0)
        options_layout.addWidget(self.resolution_combo, 1, 1)

        settings_layout.addWidget(options_frame)
        self.main_layout.addWidget(settings_card)

        self.on_format_changed("mp4")

    def create_action_bar(self):
        action_card = CardWidget()
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(16, 16, 16, 16)

        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)

        self.convert_button = PushButton("🎬 开始转换")
        self.convert_button.clicked.connect(self.start_conversion)
        button_layout.addWidget(self.convert_button)

        self.stop_button = PushButton("⏹ 停止")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_conversion)
        button_layout.addWidget(self.stop_button)

        button_layout.addStretch()

        folder_button = PushButton("📁 输出文件夹")
        folder_button.clicked.connect(self.open_output_folder)
        button_layout.addWidget(folder_button)

        help_button = PushButton("❓ 帮助")
        help_button.clicked.connect(self.show_help)
        button_layout.addWidget(help_button)

        action_layout.addWidget(button_container)
        self.main_layout.addWidget(action_card)

    def create_progress_section(self):
        progress_card = CardWidget()
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(16, 16, 16, 16)

        section_title = QLabel("转换进度")
        section_title.setStyleSheet("font-size: 15px;")
        progress_layout.addWidget(section_title)

        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        self.status_label = QLabel("等待开始转换...")
        self.status_label.setStyleSheet("font-size: 12px; color: #424242;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.progress_label = QLabel("0%")
        self.progress_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #0078D4;"
        )
        status_layout.addWidget(self.progress_label)
        progress_layout.addWidget(status_container)

        log_label = QLabel("转换日志")
        log_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        progress_layout.addWidget(log_label)

        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        progress_layout.addWidget(self.log_text)

        self.main_layout.addWidget(progress_card)

    def select_input_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter(
            "Media files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.mp3 *.wav *.flac *.m4a *.ogg *.opus *.wma *.ac3 *.mpeg *.ts *.vob)"
        )
        if file_dialog.exec_():
            files = file_dialog.selectedFiles()
            if files:
                self.input_path = files[0]
                self.file_entry.setText(self.input_path)
                self.log_message(f"✅ 已选择文件: {os.path.basename(self.input_path)}")

    def on_format_changed(self, format_text):
        self.output_format = format_text
        unsupported_gpu_formats = [
            "gif",
            "mp3",
            "wav",
            "flac",
            "m4a",
            "aac",
            "ogg",
            "opus",
            "wma",
            "ac3",
        ]
        audio_formats = [
            "mp3",
            "wav",
            "flac",
            "m4a",
            "aac",
            "ogg",
            "opus",
            "wma",
            "ac3",
        ]

        if format_text in unsupported_gpu_formats:
            self.gpu_checkbox.setEnabled(False)
            self.gpu_checkbox.setChecked(False)
            self.use_gpu = False
            self.log_message(f"⚠️ 格式 {format_text} 不支持 GPU 加速，已禁用")
        else:
            self.gpu_checkbox.setEnabled(True)
            self.gpu_checkbox.setChecked(True)
            self.use_gpu = True
            self.log_message(f"✅ 格式 {format_text} 支持 GPU 加速")

        # 动态控制帧率和分辨率选项
        if format_text in audio_formats:
            self.frame_rate_combo.setEnabled(False)
            self.resolution_combo.setEnabled(False)
        else:
            self.frame_rate_combo.setEnabled(True)
            self.resolution_combo.setEnabled(True)

    def start_conversion(self):
        if not self.input_path:
            MessageBox("警告", "请先选择要转换的输入文件！", self).exec_()
            return
        if not os.path.exists(self.input_path):
            MessageBox("错误", "输入文件不存在！", self).exec_()
            return

        base_name = os.path.splitext(os.path.basename(self.input_path))[0]
        output_file = os.path.join(
            self.output_dir, f"{base_name}_converted.{self.output_format}"
        )

        cmd = self.build_ffmpeg_command(self.input_path, output_file)
        duration = self.get_video_duration(self.input_path)

        self.convert_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self.status_label.setText("正在转换...")
        self.log_text.clear()

        self.log_message(f"🚀 开始转换: {os.path.basename(self.input_path)}")
        self.log_message(f"📁 输出文件: {os.path.basename(output_file)}")
        self.log_message(f"⚙️ 命令: {' '.join(cmd)}")

        self.conversion_thread = ConversionThread(cmd, output_file, duration)
        self.conversion_thread.progress_signal.connect(self.update_progress)
        self.conversion_thread.log_signal.connect(self.log_message)
        self.conversion_thread.completed_signal.connect(self.conversion_completed)
        self.conversion_thread.failed_signal.connect(self.conversion_failed)
        self.conversion_thread.start()

    def build_ffmpeg_command(self, input_file, output_file):
        cmd = [self.ffmpeg_path, "-i", input_file]
        video_formats = [
            "mp4",
            "mkv",
            "avi",
            "mov",
            "webm",
            "wmv",
            "flv",
            "mpeg",
            "ts",
            "vob",
            "gif",
        ]
        audio_formats = [
            "mp3",
            "wav",
            "flac",
            "m4a",
            "aac",
            "ogg",
            "opus",
            "wma",
            "ac3",
        ]

        if self.output_format in video_formats:
            # 视频编码
            if self.use_gpu:
                cmd.extend(["-c:v", "h264_nvenc"])
                self.log_message("🎮 启用 GPU 硬件加速")
            else:
                if self.output_format == "webm":
                    cmd.extend(["-c:v", "libvpx-vp9"])
                elif self.output_format == "mpeg":
                    cmd.extend(["-c:v", "mpeg2video"])
                elif self.output_format == "gif":
                    cmd.extend(["-c:v", "gif"])
                else:
                    cmd.extend(["-c:v", "libx264"])
            # 音频编码 (使用默认 AAC 128k)
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
            # 帧率和分辨率
            if self.frame_rate != "Same as source":
                cmd.extend(["-r", self.frame_rate])
            if self.resolution != "Same as source":
                cmd.extend(["-s", self.resolution])
        elif self.output_format in audio_formats:
            # 音频编码
            if self.output_format == "mp3":
                cmd.extend(["-c:a", "mp3", "-b:a", "192k"])  # mp3 默认 192k
            elif self.output_format == "flac":
                cmd.extend(["-c:a", "flac"])  # 无损格式，不需要码率
            elif self.output_format == "ogg":
                cmd.extend(["-c:a", "libvorbis", "-b:a", "128k"])  # ogg 默认 128k
            elif self.output_format == "opus":
                cmd.extend(["-c:a", "opus", "-b:a", "128k"])  # opus 默认 128k
            elif self.output_format == "wma":
                cmd.extend(["-c:a", "wmav2", "-b:a", "128k"])  # wma 默认 128k
            elif self.output_format == "ac3":
                cmd.extend(["-c:a", "ac3", "-b:a", "128k"])  # ac3 默认 128k
            else:  # wav, m4a, aac (默认aac 128k)
                cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        cmd.extend(["-progress", "pipe:1", "-nostats", "-y", output_file])
        return cmd

    def get_video_duration(self, file_path):
        try:
            cmd = [self.ffmpeg_path, "-i", file_path, "-f", "null", "-"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            for line in result.stderr.split("\n"):
                if "Duration:" in line:
                    duration_str = line.split("Duration:")[1].split(",")[0].strip()
                    parts = duration_str.split(":")
                    if len(parts) == 3:
                        hours, minutes, seconds = map(float, parts)
                        return hours * 3600 + minutes * 60 + seconds
        except:
            pass
        return 0

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"{progress}%")

    def conversion_completed(self, output_file):
        self.progress_bar.setValue(100)
        self.status_label.setText(f"✅ 转换完成！输出: {os.path.basename(output_file)}")
        self.status_label.setStyleSheet("font-size: 12px; color: #0B6A0B;")
        self.convert_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log_message("🎉 转换成功完成！")

        if MessageBox(
            "转换完成",
            f"文件转换完成！\n\n输出文件: {os.path.basename(output_file)}\n\n是否打开输出文件夹？",
            self,
        ).exec_():
            self.open_output_folder()

    def conversion_failed(self, error_message):
        self.status_label.setText(f"❌ 转换失败: {error_message}")
        self.status_label.setStyleSheet("font-size: 12px; color: #C50E20;")
        self.convert_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log_message(f"💥 转换失败: {error_message}")

    def stop_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.terminate()
            self.log_message("⏹ 用户停止了转换")
        self.convert_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("转换已停止")

    def open_output_folder(self):
        try:
            if os.name == "nt":
                os.startfile(self.output_dir)
            elif os.name == "posix":
                subprocess.run(
                    [
                        "open" if sys.platform == "darwin" else "xdg-open",
                        self.output_dir,
                    ]
                )
        except Exception as e:
            MessageBox("错误", f"无法打开文件夹: {str(e)}", self).exec_()

    def show_help(self):
        help_text = """
FFmpeg Assistant - 使用指南

🎬 功能特性:
• 支持所有主流音视频格式转换
• 硬件 GPU 加速（NVIDIA/AMD）
• 实时进度显示和日志输出
• 简洁的 Fluent 2 设计界面
• 支持帧率、分辨率调整

📋 使用步骤:
1. 点击"浏览文件"选择要转换的媒体文件
2. 选择目标输出格式
3. 根据需要调整帧率、分辨率
4. 可选择启用 GPU 硬件加速
5. 点击"开始转换"开始处理
6. 转换完成后可直接打开输出文件夹

⚡ 性能提示:
• 启用 GPU 加速可显著提升转换速度
• 大文件转换时请耐心等待
• 支持在转换过程中随时停止

🔧 技术支持:
基于 FFmpeg 开源项目构建
支持所有 FFmpeg 兼容的格式和编解码器

版本: 1.0.0
"""
        MessageBox("帮助", help_text, self).exec_()

    def log_message(self, message):
        import datetime

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_buffer.append(f"[{timestamp}] {message}")
        if not self.log_timer.isActive():
            self.log_timer.start()

    def flush_log_buffer(self):
        if self.log_buffer:
            self.log_text.append("\n".join(self.log_buffer))
            self.log_buffer.clear()
        self.log_timer.stop()


if __name__ == "__main__":
    os.environ["QT_OPENGL"] = "desktop"
    app = QApplication(sys.argv)
    window = FFmpegFluentApp()
    window.show()
    sys.exit(app.exec_())
