import argparse
import subprocess
import os
import signal

parser = argparse.ArgumentParser(description="nvfanctrl - Control the fan speed of an NVIDIA GPU on headless server")
parser.add_argument("-a", "--auto", action="store_true", help="enable automatic fan control", default=False)
parser.add_argument("-m", "--manual", type=int, help="set the fan speed to a fixed value", metavar="PERCENT")
args = parser.parse_args()

if args.auto and args.manual:
    parser.error("cannot use both --auto and --manual at the same time")
if not args.auto and not args.manual:
    parser.error("must specify either --auto or --manual")

if args.manual and not 30 <= args.manual <= 100:
    parser.error("the fan speed must be between 30 and 100")

# Step 1: Start an X server in the background
command = [
    "/usr/bin/sudo",
    "/usr/bin/xinit",
    "--",
    ":0"
]
xorg = subprocess.Popen(command)

# Step 2: Set the fan speed
os.environ["DISPLAY"] = ":0"
if args.auto:
    command = [
        "/usr/bin/sudo",
        "/usr/bin/nvidia-settings",
        "-a",
        "[gpu:0]/GPUFanControlState=0"
    ]
    subprocess.run(command)
elif args.manual:
    command = [
        "/usr/bin/sudo",
        "/usr/bin/nvidia-settings",
        "-a",
        f"[gpu:0]/GPUFanControlState=1",
        "-a",
        f"[fan:0]/GPUTargetFanSpeed={args.manual}"
    ]
    subprocess.run(command)

# Step 3: Kill the X server
os.kill(xorg.pid, signal.SIGTERM)
xorg.wait()






