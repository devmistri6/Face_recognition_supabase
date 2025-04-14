from django.contrib.auth.models import User
from .models import Student

def create_student_user(registration_id, firstname, lastname, password, branch, year, section, profile_pic=None):
    # Create User account
    user = User.objects.create_user(
        username=registration_id,
        password=password,
        first_name=firstname,
        last_name=lastname
    )
    
    # Create Student profile
    student = Student.objects.create(
        user=user,
        firstname=firstname,
        lastname=lastname,
        registration_id=registration_id,
        branch=branch,
        year=year,
        section=section,
        profile_pic=profile_pic
    )
    return student 