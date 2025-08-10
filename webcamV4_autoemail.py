from flask import Flask, render_template, send_file, redirect,Response
import cv2
from time import sleep, time
from gpiozero import Servo, RotaryEncoder,LED, Button, DistanceSensor,LineSensor
from gpiozero.pins.pigpio import PiGPIOFactory
import threading
# import RPi.GPIO as GPIO      # Optional if using RPi.GPIO

# from picamera2 import Picamera2  # Optional for camera
# import os
#from picamera2 import Picamera2                                          

#Automation process code: this code only contain necessary code for the automation process
#
from pyngrok import ngrok
import smtplib
from email.mime.text import MIMEText
import subprocess
import numpy as np
subprocess.Popen(["gnome-terminal", "--", "bash", "-c","sudo pigpiod;exec bash"])

EMAIL_SENT=False

timeout_set=5
latest_frame = None
start_time= time()


camera = cv2.VideoCapture(0)  # 0 = default USB webcam

#to improve streaming efficiency
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  # If supported
camera.set(cv2.CAP_PROP_FPS, 20)  # Optional
#start_time=time()
def update_camera():
    global latest_frame
    print("timee out")
    start_time= time()
    #while time() - start_time < timeout_set:
    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        latest_frame = frame
        sleep(0.03)  # ~10 FPS


threading.Thread(target=update_camera, daemon=True).start()

PWM=PiGPIOFactory()
#cam= Picamera2
Motor1=Servo(19,min_pulse_width=0.0004,max_pulse_width=0.0024,pin_factory=PWM)
Motor2=Servo(22,min_pulse_width=0.0005,max_pulse_width=0.0025,pin_factory=PWM)
led=LED(26)

Motor1.value=0
Motor2.value=0.0
motor1_pos=0
motor2_pos=0.0
move_step=0.05
right_limit=-0.8
down_limit=-0.5
up_limit=0.7
app = Flask(__name__)


# === Email Function ===
def send_email(public_url):
    sender_email = "liujprof@gmail.com"
    sender_password = "ipwjqixqrmxcihuw"
    recipient_email = "cnliuchanghong@gmail.com"

    msg = MIMEText(f"Your app is live at: {public_url}")
    msg['Subject'] = "Flask App URL"
    msg['From'] = sender_email
    msg['To'] = recipient_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)


def send_email_alert(public_url):
    sender_email = "liujprof@gmail.com"
    sender_password = "ipwjqixqrmxcihuw"
    recipient_email = "cnliuchanghong@gmail.com"

    msg = MIMEText(f"Motion IS Detected")
    msg['Subject'] = "Motion Alart"
    msg['From'] = sender_email
    msg['To'] = recipient_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)


# Initialize your devices here
# motor = Motor(forward=17, backward=18)

@app.route('/')
def index():
    return render_template('index1.html')

# @app.route('/LiveStream')
# def LiveStream():
#     return render_template('LiveStream.html')
    
#threading.Thread(target=update_camera, daemon=True).start()    
@app.route('/Live')
def Live():
    video_feed()               
    return render_template('LiveStream.html')

@app.route('/LiveStream')
def video_feed():
    #                                                                                                                                                                                                                            update_camera()
    return Response(gen_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    global EMAIL_SENT,latest_frame,start_time
    ret, latest_frame = camera.read()
    #_, prev = camera.read()
    prev_gray = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2GRAY)

    while True:
        success, frame = camera.read()
        if not success:
            break
        if latest_frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, gray)
        ret, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        movement = np.sum(thresh)

        # Simple motion threshold
        if movement > 1_000_000 and not EMAIL_SENT:
            print("Motion detected!")
            EMAIL_SENT = True
            #timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"/home/mae363/Desktop/photo_timestamp.jpg"
            cv2.imwrite(filename, frame)
            send_email_alert(filename)

        prev_gray = gray.copy()

        # stream frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



# def gen_frames():
#     global latest_frame,start_time
#     
# 
#     #while time() - start_time < timeout_set:
#     while True:
#         if latest_frame is None:
#             continue
#         # Encode frame as JPEG
#         ret, latest_frame = camera.read()
#         ret, jpeg = cv2.imencode('.jpg', latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 50]) #0 #(worst quality, max compression) to 100 (best quality, large file)
#         if not ret:
#             continue
#         frame_bytes = jpeg.tobytes()
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# --- Test ---
@app.route('/test', methods=['POST'])
def test():
    # Call your custom Python function
    result = test_function()
    return render_template('index1.html', result=result)

def test_function():
    # Replace this with any logic you want
    print("Web User Testing LED will blink")
    led.blink(0.2,0.2,3)
    return "Hello from Dr. L's Pi!"
    
    
# --- Motor Control Routes ---
@app.route('/forward')
def forward():
    m_left()
    return redirect('/')
    
    
def m_left():
    global motor1_pos
    
    motor1_pos=motor1_pos+move_step
    print(motor1_pos)
    if motor1_pos>0.9:
        Motor1.value=0.9
        motor1_pos=0.9
    else: Motor1.value=motor1_pos
@app.route('/reverse')
def reverse():
    m_right()
    return redirect('/')
    
def m_right():
    global motor1_pos
    
    motor1_pos=motor1_pos-move_step
    print(motor1_pos)
    if motor1_pos<right_limit:
        Motor1.value=right_limit
        motor1_pos=right_limit
    else: Motor1.value=motor1_pos

@app.route('/up')
def up():
    m_up()
    return redirect('/')
    
    
def m_up():

    global motor2_pos
    print(motor2_pos)
    motor2_pos=motor2_pos+move_step
    if motor2_pos>up_limit:
        Motor2.value=up_limit
        motor2_pos=up_limit
    else:  Motor2.value=motor2_pos



@app.route('/down')
def down():
    m_down()
    return redirect('/')
    
def m_down():
    global motor2_pos
    print(motor2_pos)
    motor2_pos=motor2_pos-move_step
    if motor2_pos<down_limit:
        Motor2.value=down_limit
        motor2_pos=down_limit
    else:  Motor2.value=motor2_pos
    
    
@app.route('/stop')
def stop():
    m_center()
    return redirect('/')
def m_center():
    Motor1.mid()
    Motor2.mid()




##Cat Spray Code
#GPIO16 maybe broken, constant on and off

button=Button(16)
knob=RotaryEncoder(6,5)
Spray_Relay=LED(17)
Spray_Relay.off()
#DisSensor=DistanceSensor(echo=27,trigger=21,max_distance=4)
#MoSensor=LineSensor(24)
minrange=80
maxrange=100
intensity=0.08
totalcount=0
count_motion=0
count_vision=0
count_distance=0
switch=1
#encoder DT05  SW16 CLK 06
#factory=


num=0
MaxRecord=6
I_V=None

public_url = ngrok.connect(5000)
print(f" * Ngrok tunnel available at: {public_url}")
send_email(public_url)

# --- Start the server ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=False,threaded=True)
     # Start ngrok tunnel
   #public_url = ngrok.connect(5000)
    #print(f" * Ngrok tunnel available at: {public_url}")

 
 # Send email or text
    

#    
#     
# while True:
#     print(DisSensor.distance*100)
#     measure=DisSensor.distance*100
#     if measure<=minrange:
#         Attack()
#     
#     MoSensor.when_line=Attack_Motion
#     sleep(1)
#     button.when_pressed=Attact_Human
#   #  print(knob.steps)
#        # success, img = cap.read()
#         #result, objectInfo = getObjects(img,0.4,0.4, objects=['cat','person'])#'person','cat'
#         #print(result,objectInfo)
#        # print(objectInfo)
#         #if len(objectInfo)==2:
#           #  print(objectInfo[1])
#        #   #      Attact_Human()
#            #     print("human detected")
#         #cv2.imshow("Output",img)
#         #cv2.waitKey(1)
#     
# 






