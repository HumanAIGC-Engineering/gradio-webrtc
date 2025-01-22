import subprocess
import os
import glob
import shutil
import argparse

def check_node_installed():
    try:
        # 尝试运行 `node -v` 命令
        subprocess.check_output(['node', '-v'])
        print("Node.js is installed.")
        return True
    except subprocess.CalledProcessError:
        print("Node.js is not installed or not found in PATH.")
        return False
    except FileNotFoundError:
        print("Node.js is not installed or not found in PATH.")
        return False

def install_wheel(whl_file, force_reinstall=False):
    if force_reinstall:
        subprocess.run(['pip', 'install', '--force-reinstall', whl_file])
        print(f"Force reinstallation of {whl_file} successful.")
    else:
        subprocess.run(['pip', 'install', whl_file])
        print(f"Installation of {whl_file} successful.")

def main(force_reinstall):
    # 获取当前脚本所在的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 切换到当前脚本所在的目录
    os.chdir(script_dir)

    # 查找 dist 目录下的 .whl 文件
    whl_files = glob.glob('dist/*.whl')

    if not check_node_installed() or whl_files is None or len(whl_files) == 0:
        # 移除 gradio_webrtc 包
        subprocess.run(['pip', 'uninstall', '-y', 'gradio_webrtc'])

        # 删除已有的 dist 目录
        if os.path.exists('dist'):
            shutil.rmtree('dist')

        # 执行 gradio cc install
        subprocess.run(['gradio', 'cc', 'install'])

        # 执行 gradio cc build --no-generate-docs
        subprocess.run(['gradio', 'cc', 'build', '--no-generate-docs'])

    if whl_files:
        whl_file = whl_files[0]
        # 安装 .whl 文件
        install_wheel(whl_file, force_reinstall)
    else:
        print("没有找到 .whl 文件")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Update and install gradio-webrtc package.")
    parser.add_argument('--force-reinstall', action='store_true', help='Force reinstall the .whl file')
    args = parser.parse_args()

    main(args.force_reinstall)