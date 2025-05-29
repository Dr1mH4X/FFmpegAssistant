import os
import re
import subprocess

# 获取当前工作目录
current_dir = os.getcwd()
print("Python工作目录：", current_dir)

# 拼接 ffmpeg.exe 的路径
ffmpeg_path = os.path.join(current_dir, "ffmpeg.exe")
print("FFmpeg路径：", ffmpeg_path)

# 创建 output 文件夹（如果不存在）
output_dir = os.path.join(current_dir, "output")
os.makedirs(output_dir, exist_ok=True)
print("输出目录：", output_dir)

# 检查文件是否存在（可选）
if os.path.exists(ffmpeg_path):
    print("✅ 找到 ffmpeg.exe")
else:
    print("❌ 未找到 ffmpeg.exe，请确认它是否存在于当前目录下")


class FFmpegAssistant:
    @staticmethod
    def convert_file(input_path, output_format):
        # 获取输入文件的目录和文件名
        input_dir = os.path.dirname(input_path)
        input_basename = os.path.basename(input_path)

        # 提取文件名（无扩展名）
        base_name = os.path.splitext(input_basename)[0]

        # 构造原始文件名并清理非法字符
        unsanitized_filename = f"{base_name}_converted.{output_format}"
        sanitized_filename = FFmpegAssistant.sanitize_filename(unsanitized_filename)

        # 输出路径为 output 文件夹下
        output_file = os.path.join(output_dir, sanitized_filename)

        # 获取编码配置
        try:
            params = FFmpegAssistant.get_encoding_params(output_format)
        except ValueError as e:
            print(f"❌ 错误：{e}")
            return

        # 构建 FFmpeg 命令
        command = [ffmpeg_path, "-i", input_path]

        # 添加视频编码参数
        if params["video_encoder"]:
            command += ["-c:v", params["video_encoder"]]

        # 添加音频编码参数
        if params["audio_encoder"]:
            command += ["-c:a", params["audio_encoder"]]

        # 添加额外参数
        if params["extra_params"]:
            command += params["extra_params"]

        # 输出文件
        command += [output_file]

        print("🎬 正在执行命令:", " ".join(command))

        try:
            result = subprocess.run(command, check=True)
            print(f"✅ 转换成功！输出文件为：{output_file}")
        except subprocess.CalledProcessError as e:
            print(f"❌ 转换失败，错误码：{e.returncode}")

    def get_encoding_params(output_format):
        profiles = {
            "mp4": {
                "video_encoder": "h264_nvenc",
                "audio_encoder": "aac",
                "use_gpu": True,
                "extra_params": ["-preset", "pmedium", "-b:v", "5M", "-b:a", "192k"]
            },
            "mkv": {
                "video_encoder": "hevc_nvenc",
                "audio_encoder": "copy",
                "use_gpu": True,
                "extra_params": ["-cq", "28"]
            },
            "avi": {
                "video_encoder": "libxvid",
                "audio_encoder": "libmp3lame",
                "use_gpu": False,
                "extra_params": []
            },
            "gif": {
                "video_encoder": None,
                "audio_encoder": None,
                "use_gpu": False,
                "extra_params": ["-vf", "fps=10,scale=320:-1:flags=lanczos", "-loop", "0"]
            }
            # 可以继续添加其他格式...
        }

        if output_format not in profiles:
            raise ValueError(f"不支持的格式：{output_format}")

        return profiles[output_format]
    
    @staticmethod
    def main():
        # 等待用户输入文件路径
        input_file = input("请输入要处理的文件路径：").strip()
        if not os.path.exists(input_file):
            print("❌ 输入的文件路径不存在，请检查后重试。")
            return

        # 等待用户选择导出格式
        output_format = input("请输入要导出的格式（如 mp4, wav, gif 等）：").strip().lower()

        supported_formats = {
            "mp4", "avi", "mkv", "mov", "flv", "webm",
            "mp3", "wav", "ogg", "aac", "flac", "m4a", "gif"
        }

        if output_format not in supported_formats:
            print("❌ 不支持的格式，请重新输入。")
            return

        # 开始转换
        FFmpegAssistant.convert_file(input_file, output_format)
    @staticmethod
    def sanitize_filename(filename, replacement="_"):
    # 定义非法字符集（Windows 下最严格）
        illegal_chars = r'[<>:"/\\|?*\x00-\x1F]'  # 包括控制字符
        cleaned = re.sub(illegal_chars, replacement, filename)
        
        # 避免以空格或点开头/结尾
        cleaned = cleaned.strip(" .")
        
        # 如果替换后为空，返回默认名称
        if not cleaned:
            cleaned = "unnamed_file"
        
        return cleaned



# 测试入口
if __name__ == "__main__":
    # 获取当前工作目录
    FFmpegAssistant.main()