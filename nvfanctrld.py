import argparse
import subprocess
import os
import signal
import time
import pynvml


def temp_to_speed(temp: int) -> int:
    """
    Modify this to change the fan speed based on the temperature
    """
    if temp < 40:
        return 30
    elif temp < 50:
        return 40
    elif temp < 55:
        return 50
    elif temp < 60:
        return 60
    else:
        return 65
    
def handle_exit(signal, frame):
    global xorg
    os.kill(xorg.pid, 15)
    xorg.wait()

    # 关 pynvml
    pynvml.nvmlShutdown()
    exit(0)

parser = argparse.ArgumentParser(description="nvfanctrld - Daemon to control the fan speed of an NVIDIA GPU on headless server")
parser.add_argument("-s", "--auto-start-time", type=int, help="Time to enable auto control (hour of the day)", metavar="HOUR")
parser.add_argument("-e", "--auto-end-time", type=int, help="Time to disable auto control (hour of the day)", metavar="HOUR")
parser.add_argument("-t", "--auto-interval", type=int, help="Interval to check the temperature (in seconds)", metavar="SECONDS")
args = parser.parse_args()

# Step 1: Start an X server in the background
command = [
    "/usr/bin/xinit",
    "--",
    ":0"
]
xorg = subprocess.Popen(command)
os.environ["DISPLAY"] = ":0"
pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)

# 用两个变量记录当前和上一个模式，这样只对状态变化敏感
previous_mode = "auto"
current_mode = "auto"
previous_speed = -1
# 初始状态设为自动模式
command = [
    "/usr/bin/nvidia-settings",
    "-a",
    "[gpu:0]/GPUFanControlState=0"
]
subprocess.run(command)

# 注册退出处理函数
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# Step 2: Loop to control the fan speed
while True:
    current_hour = time.localtime().tm_hour
    previous_mode = current_mode
    if (args.auto_start_time < args.auto_end_time and args.auto_start_time <= current_hour < args.auto_end_time) or \
            (args.auto_start_time > args.auto_end_time and (args.auto_start_time <= current_hour or current_hour < args.auto_end_time)):
        current_mode = "auto"
    else:
        current_mode = "manual"

    if current_mode == "auto" and previous_mode == "manual":
        # 将 Previous Speed 设为 -1，这样下一次循环会重新设置风扇速度
        previous_speed = -1
        command = [
            "/usr/bin/nvidia-settings",
            "-a",
            "[gpu:0]/GPUFanControlState=0"
        ]
        subprocess.run(command)
    elif current_mode == "manual":
        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        new_speed = temp_to_speed(temperature)
        if new_speed != previous_speed:
            command = [
                "/usr/bin/nvidia-settings",
                "-a",
                "[gpu:0]/GPUFanControlState=1",
                "-a",
                f"[fan:0]/GPUTargetFanSpeed={new_speed}"
            ]
            subprocess.run(command)
            previous_speed = new_speed

    time.sleep(args.auto_interval)

