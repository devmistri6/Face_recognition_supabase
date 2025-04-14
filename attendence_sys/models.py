from django.db import models
from django.contrib.auth.models import User
from .supabase_upload import upload_to_supabase

class Faculty(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    firstname = models.CharField(max_length=200, null=True, blank=True)
    lastname = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=200, null=True)
    profile_pic = models.ImageField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.profile_pic and not str(self.profile_pic).startswith("faculty/"):
            ext = self.profile_pic.name.split('.')[-1]
            filename = f"{self.firstname}{self.lastname}.{ext}".replace(" ", "")
            supabase_path = upload_to_supabase(self.profile_pic, "faculty", filename)
            if supabase_path:
                self.profile_pic.name = supabase_path
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.firstname} {self.lastname}"

class Student(models.Model):
    BRANCH = (
        ('CSE', 'CSE'),
        ('IT', 'IT'),
        ('ECE', 'ECE'),
        ('CHEM', 'CHEM'),
        ('MECH', 'MECH'),
        ('EEE', 'EEE'),
    )
    YEAR = (
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
    )
    SECTION = (
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
    )

    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    firstname = models.CharField(max_length=200, null=True, blank=True)
    lastname = models.CharField(max_length=200, null=True, blank=True)
    registration_id = models.CharField(max_length=200, null=True)
    branch = models.CharField(max_length=100, null=True, choices=BRANCH)
    year = models.CharField(max_length=100, null=True, choices=YEAR)
    section = models.CharField(max_length=100, null=True, choices=SECTION)
    profile_pic = models.ImageField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.profile_pic and not str(self.profile_pic).startswith("students/"):
            ext = self.profile_pic.name.split('.')[-1]
            filename = f"{self.registration_id}.{ext}"
            folder = f"students/{self.branch}/{self.year}/{self.section}"
            supabase_path = upload_to_supabase(self.profile_pic, folder, filename)
            if supabase_path:
                self.profile_pic.name = supabase_path
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.firstname} {self.lastname}"

class Attendence(models.Model):
    Faculty_Name = models.CharField(max_length=200, null=True, blank=True)
    Student_ID = models.CharField(max_length=200, null=True, blank=True)
    date = models.DateField(auto_now_add=True, null=True)
    time = models.TimeField(auto_now_add=True, null=True)
    branch = models.CharField(max_length=200, null=True)
    year = models.CharField(max_length=200, null=True)
    section = models.CharField(max_length=200, null=True)
    period = models.CharField(max_length=200, null=True)
    status = models.CharField(max_length=200, null=True, default='Absent')

    def __str__(self):
        return f"{self.Student_ID}_{self.date}_{self.period}"
