from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm
from django.http import StreamingHttpResponse
import cv2
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ultralytics import YOLO
import logging

#log-ultralytics-ERROR
logging.getLogger("ultralytics").setLevel(logging.ERROR)
model = YOLO("yolo11n.pt")
#PHẦN XỬ LÝ TÀI KHOẢN
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('login')
        else:
            messages.error(request, "Đăng ký thất bại. Vui lòng kiểm tra lại thông tin.")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('video')
        else:
            messages.error(request, "Sai tên đăng nhập hoặc mật khẩu.")
    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect('login')

#PHẦN GỬI EMAIL THÔNG BÁO
def send_email_notification(receiver_email, subject, body):
    sender_email = "keimaac473@gmail.com"      
    sender_password = "nhgt ccyy xtru odqc"  
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
    except Exception as e:
        print("Email sending error:", e)

#PHẦN STREAM VIDEO VỚI XỬ LÝ AI
import requests
ESP32_IP = "http://192.169.3.251"
def generate_frames(user_email):
    cap = cv2.VideoCapture(0)
    #ip = "192.169.1.134:8080"
    #cap = cv2.VideoCapture(f'http://{ip}/video')
    person_detected_previous = False
    last_email_time = 0
    email_cooldown = 60
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        results = model(frame)
        detected_person = False
        
        for r in results:
            boxes = r.boxes
            if boxes is not None and len(boxes) > 0:
                for i, box in enumerate(boxes.xyxy):
                    if int(boxes.cls[i].item()) == 0:  #'person' id = 0
                        detected_person = True
                        x1, y1, x2, y2 = map(int, box.tolist())
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, "Person", (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        # Gửi email khi chuyển từ trạng thái không có người sang có người
        if detected_person and not person_detected_previous:
            current_time = time.time()
            if current_time - last_email_time > email_cooldown:
                subject = "Cảnh báo: Phát hiện người"
                body = "Hệ thống camera an ninh của bạn vừa phát hiện có người trong khung hình."
                send_email_notification(user_email, subject, body)
                last_email_time = current_time
            try:
                requests.get(f"{ESP32_IP}/person_detected")
            except:
                print("Lỗi kết nối ESP32!")
        elif not detected_person and person_detected_previous:
            try:
                requests.get(f"{ESP32_IP}/led_off")
            except:
                print("Lỗi kết nối ESP32!")
        
        person_detected_previous = detected_person
        
        ret, buffer = cv2.imencode(".jpg", frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@login_required
def video_feed(request):
    user_email = request.user.email
    return StreamingHttpResponse(generate_frames(user_email),
                                 content_type="multipart/x-mixed-replace; boundary=frame")
@login_required
def video_page(request):
    return render(request, "video.html")