from django.shortcuts import render, redirect
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse

from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required

from .forms import *
from .models import Student, Attendence
from .filters import AttendenceFilter

# from django.views.decorators import gzip

from .recognizer import Recognizer
from datetime import date, datetime
import cv2
import threading
import json
from .utils import create_student_user
import random
import string
import pandas as pd
from io import BytesIO

# Global variables for camera control
camera = None
camera_lock = threading.Lock()

class VideoCamera:
    def __init__(self):
        self.video = None
        self.recognizer = None
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.video = cv2.VideoCapture(0)
            self.is_running = True

    def stop(self):
        self.is_running = False
        if self.video:
            self.video.release()
            self.video = None

    def get_frame(self):
        if not self.video or not self.is_running:
            return None
        
        ret, frame = self.video.read()
        if not ret:
            return None
        
        if self.recognizer:
            # Process frame with recognizer
            frame = self.recognizer.process_frame(frame)
        
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

    def start_recognition(self, details):
        self.recognizer = Recognizer(details)

    def stop_recognition(self):
        recognized_students = []
        details = None
        if self.recognizer:
            recognized_students = self.recognizer.get_recognized_students()
            details = self.recognizer.get_details()
        self.recognizer = None
        return recognized_students, details

def get_camera():
    global camera
    if camera is None:
        with camera_lock:
            if camera is None:  # Double-check pattern
                camera = VideoCamera()
    return camera

def gen(camera):
    while camera.is_running:
        frame = camera.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@login_required(login_url='login')
def video_feed(request):
    camera = get_camera()
    return StreamingHttpResponse(gen(camera),
                    content_type='multipart/x-mixed-replace; boundary=frame')

@login_required(login_url='login')
def start_attendance(request):
    if request.method == 'POST':
        camera = get_camera()
        details = {
            'faculty': request.user.faculty,
            'branch': request.POST.get('branch'),
            'year': request.POST.get('year'),
            'section': request.POST.get('section'),
            'period': request.POST.get('period')
        }
        camera.start()
        camera.start_recognition(details)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Invalid request method'})

@login_required(login_url='login')
def stop_attendance(request):
    if request.method == 'POST':
        camera = get_camera()
        recognized_students, details = camera.stop_recognition()
        
        if details:
            students = Student.objects.filter(
                branch=details['branch'],
                year=details['year'],
                section=details['section']
            )
            
            for student in students:
                attendance = Attendence(
                    Faculty_Name=details['faculty'],
                    Student_ID=str(student.registration_id),
                    period=details['period'],
                    branch=details['branch'],
                    year=details['year'],
                    section=details['section'],
                    status='Present' if str(student.registration_id) in recognized_students else 'Absent'
                )
                attendance.save()
                
        camera.stop()
        return JsonResponse({'recognized_students': recognized_students})
    return JsonResponse({'error': 'Invalid request method'})

@login_required(login_url='login')
def home(request):
    studentForm = CreateStudentForm()

    if request.method == 'POST':
        studentForm = CreateStudentForm(data=request.POST, files=request.FILES)
        stat = False 
        try:
            student = Student.objects.get(registration_id=request.POST['registration_id'])
            stat = True
        except Student.DoesNotExist:
            stat = False
        
        if studentForm.is_valid() and (stat == False):
            try:
                # Generate a random password
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                
                # Create student with user account
                student = create_student_user(
                    registration_id=studentForm.cleaned_data.get('registration_id'),
                    firstname=studentForm.cleaned_data.get('firstname'),
                    lastname=studentForm.cleaned_data.get('lastname'),
                    password=password,
                    branch=studentForm.cleaned_data.get('branch'),
                    year=studentForm.cleaned_data.get('year'),
                    section=studentForm.cleaned_data.get('section'),
                    profile_pic=request.FILES.get('profile_pic')
                )
                
                name = student.firstname + " " + student.lastname
                messages.success(request, f'Student {name} was successfully added. Their login credentials are: Username: {student.registration_id}, Password: {password}')
                return redirect('home')
            except Exception as e:
                messages.error(request, f'Error creating student: {str(e)}')
                return redirect('home')
        else:
            messages.error(request, 'Student with Registration Id '+request.POST['registration_id']+' already exists.')
            return redirect('home')

    context = {'studentForm':studentForm}
    return render(request, 'attendence_sys/home.html', context)


def loginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Check if user is a student or faculty
            if hasattr(user, 'student'):
                return redirect('student_dashboard')
            elif hasattr(user, 'faculty'):
                return redirect('home')
            else:
                return redirect('home')
        else:
            messages.info(request, 'Username or Password is incorrect')

    context = {}
    return render(request, 'attendence_sys/login.html', context)

@login_required(login_url = 'login')
def logoutUser(request):
    logout(request)
    return redirect('login')

@login_required(login_url = 'login')
def updateStudentRedirect(request):
    context = {}
    if request.method == 'POST':
        try:
            reg_id = request.POST['reg_id']
            branch = request.POST['branch']
            student = Student.objects.get(registration_id = reg_id, branch = branch)
            updateStudentForm = CreateStudentForm(instance=student)
            context = {'form':updateStudentForm, 'prev_reg_id':reg_id, 'student':student}
        except:
            messages.error(request, 'Student Not Found')
            return redirect('home')
    return render(request, 'attendence_sys/student_update.html', context)

@login_required(login_url = 'login')
def updateStudent(request):
    if request.method == 'POST':
        context = {}
        try:
            student = Student.objects.get(registration_id = request.POST['prev_reg_id'])
            updateStudentForm = CreateStudentForm(data = request.POST, files=request.FILES, instance = student)
            if updateStudentForm.is_valid():
                updateStudentForm.save()
                messages.success(request, 'Updation Success')
                return redirect('home')
        except:
            messages.error(request, 'Updation Unsucessfull')
            return redirect('home')
    return render(request, 'attendence_sys/student_update.html', context)


@login_required(login_url='login')
def takeAttendence(request):
    if request.method == 'POST':
        details = {
            'branch': request.POST['branch'],
            'year': request.POST['year'],
            'section': request.POST['section'],
            'period': request.POST['period'],
            'faculty': request.user.faculty
        }
        
        if Attendence.objects.filter(date=str(date.today()),
                                  branch=details['branch'],
                                  year=details['year'],
                                  section=details['section'],
                                  period=details['period']).count() != 0:
            messages.error(request, "Attendance already recorded.")
            return redirect('home')
        
        students = Student.objects.filter(branch=details['branch'],
                                       year=details['year'],
                                       section=details['section'])
        
        context = {
            "students": students,
            "details": details,
            "ta": True
        }
        return render(request, 'attendence_sys/attendence.html', context)
    
    context = {}
    return render(request, 'attendence_sys/home.html', context)

def searchAttendence(request):
    attendences = Attendence.objects.all()
    myFilter = AttendenceFilter(request.GET, queryset=attendences)
    attendences = myFilter.qs
    context = {'myFilter':myFilter, 'attendences': attendences, 'ta':False}
    return render(request, 'attendence_sys/attendence.html', context)


@login_required(login_url='login')
def facultyProfile(request):
    if not hasattr(request.user, 'faculty'):
        return redirect('student_dashboard')
    
    faculty = request.user.faculty
    form = FacultyForm(instance=faculty)
    context = {'form': form}
    return render(request, 'attendence_sys/facultyForm.html', context)

@login_required(login_url='login')
def student_dashboard(request):
    if not hasattr(request.user, 'student'):
        return redirect('login')
    
    student = request.user.student
    attendance_records = Attendence.objects.filter(
        Student_ID=student.registration_id
    ).order_by('-date')
    
    context = {
        'student': student,
        'attendance_records': attendance_records
    }
    return render(request, 'attendence_sys/student_dashboard.html', context)

@login_required(login_url='login')
def change_password(request):
    if not hasattr(request.user, 'student'):
        return redirect('login')
        
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('student_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'attendence_sys/change_password.html', {
        'form': form
    })

@login_required(login_url='login')
def student_account(request):
    if not hasattr(request.user, 'student'):
        return redirect('home')
    
    student = request.user.student
    context = {
        'student': student,
    }
    return render(request, 'attendence_sys/student_account.html', context)

@login_required(login_url='login')
def generate_attendance_report(request):
    if request.method == 'POST':
        branch = request.POST.get('branch')
        year = request.POST.get('year')
        section = request.POST.get('section')
        
        # Get attendance records for the specified criteria
        attendance_records = Attendence.objects.filter(
            branch=branch,
            year=year,
            section=section
        ).order_by('date', 'Student_ID', 'period')
        
        # Create a DataFrame from the attendance records
        data = []
        current_student = None
        current_date = None
        student_data = {}
        
        for record in attendance_records:
            if current_student != record.Student_ID or current_date != record.date:
                if student_data:
                    data.append(student_data)
                current_student = record.Student_ID
                current_date = record.date
                student_data = {
                    'Date': record.date,
                    'Student ID': record.Student_ID,
                    'Faculty': record.Faculty_Name
                }
            
            # Add period-wise attendance
            student_data[f'Period {record.period}'] = record.status
        
        if student_data:
            data.append(student_data)
        
        df = pd.DataFrame(data)
        
        # Reorder columns to have periods in order
        columns = ['Date', 'Student ID', 'Faculty']
        for i in range(1, 8):
            period_col = f'Period {i}'
            if period_col in df.columns:
                columns.append(period_col)
        
        df = df[columns]
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Attendance Report', index=False)
            
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Attendance Report']
            
            # Add some formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Write the column headers with the defined format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 15)  # Set column width
        
        # Set up the response
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=attendance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
    
    return JsonResponse({'error': 'Invalid request method'})



# class VideoCamera(object):
#     def __init__(self):
#         self.video = cv2.VideoCapture(0)
#     def __del__(self):
#         self.video.release()

#     def get_frame(self):
#         ret,image = self.video.read()
#         ret,jpeg = cv2.imencode('.jpg',image)
#         return jpeg.tobytes()


# def gen(camera):
#     while True:
#         frame = camera.get_frame()
#         yield(b'--frame\r\n'
#         b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


# @gzip.gzip_page
# def videoFeed(request):
#     try:
#         return StreamingHttpResponse(gen(VideoCamera()),content_type="multipart/x-mixed-replace;boundary=frame")
#     except:
#         print("aborted")

# def getVideo(request):
#     return render(request, 'attendence_sys/videoFeed.html')