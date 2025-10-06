from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/assigned_issues/$', consumers.AssignedIssueConsumer.as_asgi()),
]
