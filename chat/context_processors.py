from django.utils import timezone
from .models import Issue

def overdue_issues_count(request):
    if request.user.is_authenticated:
        count = Issue.objects.filter(
            assigned_to=request.user,
            due_date__lt=timezone.now(),
            status__in=['Open', 'In Progress']
        ).count()
    else:
        count = 0
    return {'overdue_issues_count': count}
