from django.contrib import admin
from chat.models import *

admin.site.register(UserOrganization)
admin.site.register(Organization)
admin.site.register(Project)

admin.site.register(Issue)
