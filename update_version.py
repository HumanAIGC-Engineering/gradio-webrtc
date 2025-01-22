import subprocess
import os
import glob
import shutil


# 移除 gradio_webrtc 包
subprocess.run(['pip', 'uninstall', '-y', 'gradio_webrtc'])

# 删除已有的 dist 目录
if os.path.exists('dist'):
    shutil.rmtree('dist')

# 执行 gradio cc install
subprocess.run(['gradio', 'cc', 'install'])

# 执行 gradio cc build --no-generate-docs
subprocess.run(['gradio', 'cc', 'build', '--no-generate-docs'])

# 查找 dist 目录下的 .whl 文件
whl_files = glob.glob('dist/*.whl')

if whl_files:
    whl_file = whl_files[0]
    # 安装 .whl 文件
    subprocess.run(['pip', 'install', whl_file])
else:
    print("没有找到 .whl 文件")