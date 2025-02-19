from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm
from django.http import StreamingHttpResponse
import cv2

# Đăng ký
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

# Đăng nhập
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('video')  # Chuyển đến trang video
        else:
            messages.error(request, "Sai tên đăng nhập hoặc mật khẩu.")
    
    return render(request, "login.html")

# Đăng xuất
def logout_view(request):
    logout(request)
    return redirect('login')

# Xử lý video streaming
def generate_frames():
    ip = "172.20.10.3:8080"
    cap = cv2.VideoCapture(f'http://{ip}/video')
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            _, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Gửi video stream
@login_required
def video_feed(request):
    return StreamingHttpResponse(generate_frames(), content_type="multipart/x-mixed-replace; boundary=frame")

# Trang video hiển thị user + stream
@login_required
def video_page(request):
    return render(request, "video.html")  # Render trang video.html
