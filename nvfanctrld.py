import argparse
import subprocess
import os
import signal
import time
import pynvml

recipes = [
    {
        "begin_hour": 10,
        "end_hour": 23,
        "mode": "manual",
        "base": 30,
        "steps": [
            (40, 40),
            (50, 50),
            (55, 60),
            (60, 65),
        ]
    },
    {
        "begin_hour": 23,
        "end_hour": 1,
        "mode": "manual",
        "base": 30,
        "steps": [
            (40, 40),
            (50, 50),
            (55, 60),
            (60, 65),
            (65, 75),
        ]
    },
    {
        "begin_hour": 1,
        "end_hour": 8,
        "mode": "auto"
    },
    {
        "begin_hour": 8,
        "end_hour": 10,
        "mode": "manual",
        "base": 30,
        "steps": [
            (40, 40),
            (50, 50),
            (55, 60),
            (60, 65),
            (65, 70),
        ]
    }
]


def temp_to_speed(recipe: dict, temp: int) -> int:
    if recipe["mode"] != "manual":
        raise Exception("Mode error")
    result = recipe["base"]
    for start_point, speed in recipe["steps"]:
        if temp >= start_point:
            result = speed

    return result

def is_time_match(h: int, r: tuple) -> bool:
    begin, end = r
    if (begin < end and begin <= h < end) or (begin > end and ((begin <= h) or (h < end))):
        return True
    return False

def run_cmd(cmd: list):
    try:
        subprocess.run(cmd)
    except Exception as e:
        print(f"Error occured while executing {' '.join(cmd)}: {str(e)}")

    
def handle_exit(signal, frame):
    global xorg
    os.kill(xorg.pid, 15)
    xorg.wait()

    # 关 pynvml
    pynvml.nvmlShutdown()
    exit(0)

parser = argparse.ArgumentParser(description="nvfanctrld - Daemon to control the fan speed of an NVIDIA GPU on headless server")
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
run_cmd(command)

# 注册退出处理函数
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# Step 2: Loop to control the fan speed
while True:
    current_hour = time.localtime().tm_hour
    previous_mode = current_mode

    current_recipe = None
    for recipe in recipes:
        rtime = (recipe["begin_hour"], recipe["end_hour"])
        if is_time_match(current_hour, rtime):
            current_recipe = recipe
            break

    current_mode = current_recipe["mode"]

    if current_mode == "auto" and previous_mode == "manual":
        previous_speed = -1
        command = [
            "/usr/bin/nvidia-settings",
            "-a",
            "[gpu:0]/GPUFanControlState=0"
        ]
        run_cmd(command)
    elif current_mode == "manual":
        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        new_speed = temp_to_speed(current_recipe, temperature)
        if new_speed != previous_speed:
            command = [
                "/usr/bin/nvidia-settings",
                "-a",
                "[gpu:0]/GPUFanControlState=1",
                "-a",
                f"[fan:0]/GPUTargetFanSpeed={new_speed}"
            ]
            run_cmd(command)
            previous_speed = new_speed

    time.sleep(args.auto_interval)

