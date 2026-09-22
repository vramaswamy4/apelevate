from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
from .decorators import unauthenticated_user, allowed_users, admin_only
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.auth.forms import UserCreationForm
from .forms import SignUpForm, ClassForm, ClassFormUnit, ClassFormSubject, MenAppForm
from django.contrib.auth import authenticate, login, logout
from.models import Mentors, MentorApplications, Classes, ClassRequests, Subjects, Subtopics, Units, Students
from django.conf import settings
from django.contrib.auth import get_user_model


# User_set= settings.AUTH_USER_MODEL

# Create your views here.
# @login_required(login_url='login')
@unauthenticated_user
def home_page(request):
    context = {}
    return render(request, "home_page.html", context)

@unauthenticated_user
def sign_up(request):
    form = SignUpForm()

    if request.method =="POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            group = Group.objects.get(name='students')
            user.groups.add(group)
            obj = Students()
            obj.user =(user)
            obj.save()

            firstname = form.cleaned_data.get('first_name')
            lastname = form.cleaned_data.get('last_name')

            # messages.success(request, "Account was created for " + firstname + " " + lastname)

            return redirect('login')



    context = {"form": form,}
    return render(request, "sign_up.html", context)
# group = Group.objects.get(name='students')
# user.groups.add(group

@unauthenticated_user
def log_in(request):

    if request.method == "POST":
        username=request.POST.get('username')
        password=request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('std_dashboard')
        else:
            messages.info(request, "username OR password is incorrect")


    context = {}
    return render(request, "log_in.html", context)

@login_required(login_url='login')
def logout_page(request):
    logout(request)
    return redirect('login')

def forgot_password(request):
    context = {}
    return render(request, "forgot_password.html", context)

@login_required(login_url='login')
def std_dashboard(request):
    student = Students.objects.get(user=request.user)
    print(student)
    context = {"student": student}
    return render(request, "std_dashboard.html", context)

@allowed_users(allowed_roles=['mentors', 'admin'])
def men_dashboard(request):
    student = Students.objects.get(user=request.user)
    context = {"student": student}
    return render(request, "men_dashboard.html", context)

@allowed_users(allowed_roles=['mentors', 'admin'])
def create_a_class(request):
    student = Students.objects.get(user=request.user)

    form1 = ClassFormSubject()


    if request.method == 'POST':
        form1 = ClassFormSubject(request.POST)
        # subject = form1.cleaned_data.get("sub_name")
        return redirect('/create-a-class2')


    context = {"form1": form1,
               "student": student}
    return render(request, "create_a_class.html", context)

@allowed_users(allowed_roles=['mentors', 'admin'])
def create_a_class2(request):
    student = Students.objects.get(user=request.user)

    form2 = ClassFormUnit()


    if request.method == 'POST':
        form2 = ClassFormUnit(request.POST)
        return redirect('/create-a-class3')

    context = {"form2": form2,
               "student": student}
    return render(request, "create_a_class2.html", context)

@allowed_users(allowed_roles=['mentors', 'admin'])
def create_a_class3(request):
    form = ClassForm()
    student = Students.objects.get(user=request.user)

    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            new_class = form.save()
            new_class.mentor = request.user
            subs = Subtopics.objects.all()[:2]
            print(subs)
            for sub in subs:
                new_class.subtopics.add(sub)
            return redirect('/mentor-dashboard')

    context = {"form": form,
               "student": student}
    return render(request, "create_a_class3.html", context)



@login_required(login_url='login')
def enrol_page(request):
    student = Students.objects.get(user=request.user)

    obj = Classes.objects.all()
    subtopics = []
    for o in obj:
        subtopics.append(o.subtopics.all())
    print(subtopics)

    context = {'object': obj,
               'subtopics_l': subtopics,
               'user': request.user,
               "student": student}

    return render(request, "enrol.html", context)

@login_required(login_url='login')
def enrol_page_filtered(request):
    student = Students.objects.get(user=request.user)

    obj = Classes.objects.all()[:3]
    subtopics = []
    for o in obj:
        subtopics.append(o.subtopics.all())
    print(subtopics)

    context = {'object': obj,
               'filter': filter,
               'subtopics_l': subtopics,
               "student": student}

    return render(request, "enrol_filtered.html", context)

@login_required(login_url='login')
def purchase_tokens(request):
    student = Students.objects.get(user=request.user)

    context = {"student": student}
    return render(request, "purchase.html", context)

@login_required(login_url='login')
def payment_portal(request, cost):
    student = Students.objects.get(user=request.user)

    context = {"cost": cost,
               "student": student}
    return render(request, "payment_portal.html", context)

@login_required(login_url='login')
def payment_complete(request, cost):

    student = Students.objects.get(user=request.user)
    if cost == 20:
        tokens = 1
    elif cost == 80:
        tokens = 5
    elif cost == 120:
        tokens = 10
    elif cost == 180:
        tokens = 20
    else:
        print('unknown tokens')
    print(student.Tokens)
    student.Tokens=student.Tokens + tokens
    print(student.Tokens)
    student.save()
    context = {"student": student}
    return render(request, "payment_complete.html", context)

@login_required(login_url='login')
def class_info(request, id):
    student = Students.objects.get(user=request.user)

    obj = Classes.objects.get(id=id)
    subtopics = obj.subtopics.all()


    if request.method == 'POST':
        student=Students.objects.get(user=request.user)
        obj.students.add(student)
    context = {"object": obj,
               "subtopics": subtopics}
    return render(request, "class_info.html", context)

@login_required(login_url='login')
def joined_classes(request):
    student = Students.objects.get(user=request.user)

    obj = Classes.objects.all()
    subtopics = []
    students = []


    for o in obj:
        subtopics.append(o.subtopics.all())
        students.append(o.students.all())

    context = {'object': obj,
               'subtopics_l': subtopics,
               'user': request.user,
               "student": student}

    return render(request, "joined_classes.html", context)



@allowed_users(allowed_roles=['mentors', 'admin'])
def my_classes(request):
    student = Students.objects.get(user=request.user)
    obj = Classes.objects.all()
    subtopics = []

    for o in obj:
        subtopics.append(o.subtopics.all())

    context = {'object': obj,
               'user': request.user,
               "student": student}
    return render(request, "my_classes.html", context)



@allowed_users(allowed_roles=['students'])
def mentor_application(request):
    student = Students.objects.get(user=request.user)

    form = MenAppForm()

    if request.method == 'POST':
        print('submited')
        form = MenAppForm(request.POST, request.FILES)
        if form.is_valid():
            print('valid')
            menapp = form.save(commit=False)

            menapp.subject = Subjects.objects.get(pk=1)
            menapp.accepted = False
            menapp.save()
            return redirect('/student-dashboard/')
        else:
            print(form.errors.as_data())  # here you print errors to terminal

    context = {"form": form,
               "student": student,}
    return render(request, "mentor_applications.html", context)

@allowed_users(allowed_roles=['admin'])
def accept(request, id):

    obj = MentorApplications.objects.get(id=id)
    if request.method == 'GET':
        group = Group.objects.get(name='mentors')
        obj.user.groups.add(group)
        obj.decided=True
        obj.save()
    return redirect('/applications/')

@allowed_users(allowed_roles=['admin'])
def reject(request, id):

    obj = MentorApplications.objects.get(id=id)
    if request.method == 'GET':
        obj.decided=True
        obj.save()
    return redirect('/applications/')




@allowed_users(allowed_roles=['admin'])
def applications(request):
    student = Students.objects.get(user=request.user)

    obj = MentorApplications.objects.all()

    context = {'object': obj,
               "student": student}

    return render(request, "applications.html", context)


