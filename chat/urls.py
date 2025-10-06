from django.urls import path , include
from . import views 
urlpatterns = [
     # path('chat/<str:room_name>/', views.chat_room, name='chat'),
     path('organization_list/', views.organization_list, name='organization_list'),
     path('projects/', views.project_list, name='project_list'),
     path('users/', views.user_management, name='user_management'),
     path('issue_create/', views.issue_create, name='issue_create'),
     path('assigned_issues/', views.assigned_issues, name='assigned_issues'),
]