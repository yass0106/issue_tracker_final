from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone



class Organization(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_organizations')

    def __str__(self):
        return self.name

class UserOrganization(models.Model):
    ROLE_CHOICES = (
        ('Owner', 'Owner'),
        ('Manager', 'Manager'),
        ('Member', 'Member'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Member')

    class Meta:
        unique_together = ('user', 'organization')

    def __str__(self):
        return self.user.username +' - '+self.organization.name +' - '+ self.role

class Project(models.Model):
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='projects')

    def __str__(self):
        return self.name



class Issue(models.Model):
    STATUS_CHOICES = (
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Closed', 'Closed'),
    )

    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    )

    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    due_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_issues', null=True, blank=True)

    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_issues')
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='issues', null=True, blank=True)
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    

    def __str__(self):
        return self.title +' - '+self.status

    def is_overdue(self):
        return self.due_date and self.due_date < timezone.now() and self.status != 'Closed'