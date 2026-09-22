from django.contrib import admin
from.models import Mentors, MentorApplications, Classes, ClassRequests, Subjects, Subtopics, Units, Students

# Register your models here.
admin.site.register(Mentors)
admin.site.register(Students)
admin.site.register(MentorApplications)
admin.site.register(Classes)
admin.site.register(ClassRequests)
admin.site.register(Subjects)
admin.site.register(Subtopics)
admin.site.register(Units)



