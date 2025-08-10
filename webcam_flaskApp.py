import asyncio
import threading
import websockets
import json

import cv2
from flask import Flask, Response, send_from_directory
from gpiozero import Servo, LED
from gpiozero.pins.pigpio import PiGPIOFactory
from picamzero import Camera


# --- Setup hardware ---
PWM = PiGPIOFactory()
Motor1 = Servo(19, min_pulse_width=0.0005, max_pulse_width=0.0025, pin_factory=PWM)
led = LED(26)
cam = Camera()

# --- Camera setup (OpenCV for MJPEG stream) ---
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

# --- Flask App (for index.html and /video_feed) ---
app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')  # serve static file in same folder

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- WebSocket Command Handler ---
async def ws_handler(websocket):
    print("WebSocket client connected")
    try:
        async for message in websocket:
            print(f"Received: {message}")
            await handle_command(message)
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket client disconnected")

async def handle_command(message):
    try:
        data = json.loads(message)
        action = data.get("action")

        if action == "pan_left":
            Motor1.min()
        elif action == "pan_right":
            Motor1.max()
        elif action == "center":
            Motor1.mid()
        elif action == "capture":
            cam.start_preview()
            cam.take_photo("/home/desktop/photo.jpg")
            cam.stop_preview()
        elif action == "blink_led":
            led.blink(0.2, 0.2, 3)
        else:
            print(f"Unknown action: {action}")

    except Exception as e:
        print(f"Error handling command: {e}")

# --- Run Flask and WebSocket together ---
def start_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

async def start_websocket():
    print("Starting WebSocket server...")
    async with websockets.serve(ws_handler, "0.0.0.0", 6789):
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()

    asyncio.run(start_websocket())


