from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name = 'home'),
    path('login/', views.loginPage, name='login'),
    path('logout/', views.logoutUser, name='logout'),
    path('searchattendence/', views.searchAttendence, name='searchattendence'),
    path('account/', views.facultyProfile, name='account'),

    path('updateStudentRedirect/', views.updateStudentRedirect, name='updateStudentRedirect'),
    path('updateStudent/', views.updateStudent, name='updateStudent'),
    path('takeAttendence/', views.takeAttendence, name='takeAttendence'),
    path('video_feed/', views.video_feed, name='video_feed'),
    path('start_attendance/', views.start_attendance, name='start_attendance'),
    path('stop_attendance/', views.stop_attendance, name='stop_attendance'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('change-password/', views.change_password, name='change_password'),
    path('generate-report/', views.generate_attendance_report, name='generate_report'),
]