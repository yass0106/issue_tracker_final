from celery import shared_task
from django.utils import timezone
from .models import Issue

@shared_task
def mark_overdue_issues():
    now = timezone.now()
    # Update issues where due_date passed and status is not closed
    overdue_issues = Issue.objects.filter(due_date__lt=now, status__in=['Open', 'In Progress'])
    for issue in overdue_issues:
        issue.status = 'Overdue'
        issue.save()
    return f'{overdue_issues.count()} issues marked overdue'
