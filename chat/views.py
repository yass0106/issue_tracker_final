from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Organization, UserOrganization, Project, Issue

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# --- Helper functions ---
def get_user_organizations(user):
    return UserOrganization.objects.filter(user=user)

def has_permission(user, organization, min_role='Member'):
    roles = {'Owner': 3, 'Manager': 2, 'Member': 1}
    user_org = get_user_organizations(user).filter(organization=organization).first()
    if not user_org:
        return False
    return roles.get(user_org.role, 0) >= roles.get(min_role, 0)

# --- Organization views ---
@login_required
def organization_list(request):
    # Handle POST actions: create, edit, delete
    if request.method == 'POST':
        action = request.POST.get('action')
        org_id = request.POST.get('org_id')
        name = request.POST.get('name')

        if action == 'create':
            if not name:
                messages.error(request, 'Organization name required')
            else:
                if Organization.objects.filter(name=name, owner=request.user).exists():
                    messages.error(request,'Organization Already Created')
                    return redirect('organization_list')
                org = Organization.objects.create(name=name, owner=request.user)
                UserOrganization.objects.create(user=request.user, organization=org, role='Owner')
                messages.success(request, 'Organization created successfully')

        elif action == 'edit':
            org = get_object_or_404(Organization, pk=org_id, owner=request.user)
            if not name:
                messages.error(request, 'Organization name required')
            else:
                org.name = name
                org.save()
                messages.success(request, 'Organization updated successfully')

        elif action == 'delete':
            org = get_object_or_404(Organization, pk=org_id, owner=request.user)
            org.delete()
            messages.success(request, 'Organization deleted successfully')

        return redirect('organization_list')

    # GET request: show list
    organizations = Organization.objects.filter(owner=request.user)
    edit_org_id = request.GET.get('edit')
    edit_org = None
    if edit_org_id:
        edit_org = get_object_or_404(Organization, pk=edit_org_id, owner=request.user)

    return render(request, 'organizations.html', {
        'organizations': organizations,
        'edit_org': edit_org
    })


@login_required
def project_list(request):
    user_orgs = UserOrganization.objects.filter(user=request.user).select_related('organization')
    accessible_org_ids = [uo.organization.id for uo in user_orgs]

    # Handle POST actions
    if request.method == 'POST':
        action = request.POST.get('action')
        project_id = request.POST.get('project_id')
        name = request.POST.get('name')
        org_id = request.POST.get('org_id')

        if action == 'create':
            if not name or not org_id:
                messages.error(request, 'Project name and organization required')
            else:
                org = get_object_or_404(Organization, pk=org_id)
                if not has_permission(request.user, org, 'Manager'):
                    messages.error(request, 'Permission denied')
                elif Project.objects.filter(name=name, organization=org).exists():
                    messages.info(request, 'Project already exists')
                else:
                    Project.objects.create(name=name, organization=org)
                    messages.success(request, 'Project created successfully')

        elif action == 'edit':
            project = get_object_or_404(Project, pk=project_id)
            if not has_permission(request.user, project.organization, 'Manager'):
                messages.error(request, 'Permission denied')
            elif not name:
                messages.error(request, 'Project name required')
            else:
                project.name = name
                project.save()
                messages.success(request, 'Project updated successfully')

        elif action == 'delete':
            project = get_object_or_404(Project, pk=project_id)
            if not has_permission(request.user, project.organization, 'Manager'):
                messages.error(request, 'Permission denied')
            else:
                project.delete()
                messages.success(request, 'Project deleted successfully')

        return redirect('project_list')

    # GET request: show projects
    projects = Project.objects.filter(organization__id__in=accessible_org_ids).select_related('organization')

    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 10))
    paginator = Paginator(projects, per_page)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Optional edit
    edit_project_id = request.GET.get('edit')
    edit_project = None
    if edit_project_id:
        edit_project = get_object_or_404(Project, pk=edit_project_id)

    return render(request, 'projects.html', {
        'projects': page_obj,
        'organizations': user_orgs,
        'edit_project': edit_project,
        'page_obj': page_obj,
        'paginator': paginator
    })


@login_required
def user_management(request):
    roles_list = ['Owner', 'Manager', 'Member']

    # Get organizations the current user has access to
    user_orgs = UserOrganization.objects.filter(user=request.user).select_related('organization')
    org_ids = [uo.organization.id for uo in user_orgs]

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        org_id = request.POST.get('org_id')
        role = request.POST.get('role', 'Member')

        if not username or not password or not email or not org_id:
            messages.error(request, 'All fields are required')
            return redirect('user_management')

        if role not in roles_list:
            messages.error(request, 'Invalid role selected')
            return redirect('user_management')

        try:
            org = Organization.objects.get(id=org_id)
            if not has_permission(request.user, org, 'Manager'):
                messages.error(request, 'Permission denied')
                return redirect('user_management')

            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
                return redirect('user_management')

            new_user = User.objects.create_user(username=username, password=password, email=email)
            UserOrganization.objects.create(user=new_user, organization=org, role=role)
            messages.success(request, f'User {username} created with role {role}')
            return redirect('user_management')

        except Organization.DoesNotExist:
            messages.error(request, 'Organization not found')
            return redirect('user_management')

    # GET request: prepare data for template
    org_users = UserOrganization.objects.filter(organization__id__in=org_ids).select_related('user', 'organization')

    # Build dictionary {org_id: {org_name, roles: {role: [users]}, counts: {}}}
    org_data = {}
    for uo in org_users:
        org_id = uo.organization.id
        org_name = uo.organization.name
        user_role = uo.role
        username = uo.user.username

        if org_id not in org_data:
            org_data[org_id] = {
                'org_id': org_id,
                'org_name': org_name,
                'roles': {r: [] for r in roles_list}
            }

        org_data[org_id]['roles'][user_role].append(username)

    # Add counts
    # Convert roles dict into a list for easier template rendering
    for org in org_data.values():
        org['roles_list'] = []
        for role, users in org['roles'].items():
            org['roles_list'].append({'role': role, 'users': users, 'count': len(users)})


    return render(request, 'user_management.html', {
        'roles': roles_list,
        'organizations': user_orgs,
        'org_data': list(org_data.values())
    })
    
# @login_required
# def issue_create(request):
#     user_orgs = UserOrganization.objects.filter(user=request.user).select_related('organization')

#     selected_org_id = request.POST.get('organization') or request.GET.get('organization')
#     selected_org = None
#     projects = []
#     org_users = []

#     if selected_org_id:
#         selected_org = get_object_or_404(Organization, id=selected_org_id)
#         # Projects in this organization
#         projects = Project.objects.filter(organization=selected_org)
#         # Users in this organization
#         org_users = UserOrganization.objects.filter(organization=selected_org).select_related('user')

#     if request.method == 'POST' and request.POST.get('action') == 'create':
#         title = request.POST.get('title')
#         description = request.POST.get('description')
#         project_id = request.POST.get('project')
#         assigned_to_id = request.POST.get('assigned_to')

#         if not title or not project_id:
#             messages.error(request, 'Title and project are required')
#         else:
#             project = get_object_or_404(Project, id=project_id)
#             assigned_to = User.objects.get(id=assigned_to_id) if assigned_to_id else None
#             Issue.objects.create(
#                 title=title,
#                 description=description,
#                 project=project,
#                 assigned_to=assigned_to,
#                 created_by=request.user
#             )
#             messages.success(request, 'Issue created successfully')
#             return redirect('issue_create')

#     return render(request, 'issue.html', {
#         'user_orgs': user_orgs,
#         'selected_org': selected_org,
#         'projects': projects,
#         'org_users': org_users
#     })



from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


from django.core.paginator import Paginator
from django.db.models import Q

# @login_required
# def issue_create(request):
#     user_orgs = UserOrganization.objects.filter(user=request.user).select_related('organization')

#     # Filters from GET params
#     status_filter = request.GET.get('status')
#     priority_filter = request.GET.get('priority')
#     due_date_filter = request.GET.get('due_date')

#     selected_org_id = request.POST.get('organization') or request.GET.get('organization')
#     selected_org = None
#     projects = []
#     org_users = []

#     if selected_org_id:
#         selected_org = get_object_or_404(Organization, id=selected_org_id)
#         projects = Project.objects.filter(organization=selected_org)
#         org_users = UserOrganization.objects.filter(organization=selected_org).select_related('user')

#     if request.method == 'POST' and request.POST.get('action') == 'create':
#         title = request.POST.get('title')
#         description = request.POST.get('description')
#         project_id = request.POST.get('project')
#         assigned_to_id = request.POST.get('assigned_to')

#         if not title or not project_id:
#             messages.error(request, 'Title and project are required')
#         else:
#             project = get_object_or_404(Project, id=project_id)
#             assigned_to = User.objects.get(id=assigned_to_id) if assigned_to_id else None
#             issue = Issue.objects.create(
#                 title=title,
#                 description=description,
#                 project=project,
#                 assigned_to=assigned_to,
#                 created_by=request.user
#             )

#             # Broadcast new issue to the assigned user
#             if assigned_to:
#                 channel_layer = get_channel_layer()
#                 async_to_sync(channel_layer.group_send)(
#                     f"user_{assigned_to.id}_issues",
#                     {
#                         "type": "issue_update",
#                         "issue_id": issue.id,
#                         "title": issue.title,
#                         "project_name": issue.project.name,
#                         "status": issue.status,
#                         "due_date": issue.due_date.isoformat() if issue.due_date else None,
#                         "priority": issue.priority
#                     }
#                 )

#             messages.success(request, 'Issue created successfully')
#             return redirect('issue_create')

#     # Filter issues
#     user_issues = Issue.objects.filter(created_by=request.user).select_related(
#         'project', 'project__organization', 'assigned_to'
#     )
#     if status_filter:
#         user_issues = user_issues.filter(status=status_filter)
#     if priority_filter:
#         user_issues = user_issues.filter(priority=priority_filter)
#     if due_date_filter:
#         user_issues = user_issues.filter(due_date=due_date_filter)

#     # Pagination
#     paginator = Paginator(user_issues.order_by('-created_at'), 10)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     return render(request, 'issue.html', {
#         'user_orgs': user_orgs,
#         'selected_org': selected_org,
#         'projects': projects,
#         'org_users': org_users,
#         'page_obj': page_obj,
#         'statuses': ['Open', 'In Progress', 'Closed'],
#         'priorities': ['Low', 'Medium', 'High'],
#         'status_filter': status_filter,
#         'priority_filter': priority_filter,
#         'due_date_filter': due_date_filter
#     })

# from django.core.paginator import Paginator

@login_required
def assigned_issues(request):
    issues = Issue.objects.filter(assigned_to=request.user).select_related('project', 'project__organization')

    # Filters
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    due_date_filter = request.GET.get('due_date')

    if status_filter:
        issues = issues.filter(status=status_filter)
    if priority_filter:
        issues = issues.filter(priority=priority_filter)
    if due_date_filter:
        try:
            from datetime import datetime
            due_date_obj = datetime.strptime(due_date_filter, "%Y-%m-%d").date()
            issues = issues.filter(due_date__date=due_date_obj)
        except ValueError:
            pass

    # Handle status update via POST
    if request.method == "POST":
        issue_id = request.POST.get("issue_id")
        status = request.POST.get("status")
        issue = get_object_or_404(Issue, id=issue_id, assigned_to=request.user)
        if status:
            issue.status = status
            issue.save()
            # In assigned_issues view after issue.save()
            if status:
                issue.status = status
                issue.save()

                # Broadcast update
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{request.user.id}_issues",
                    {
                        "type": "issue_update",
                        "issue_id": issue.id,
                        "title": issue.title,
                        "project_name": issue.project.name,
                        "status": issue.status,
                        "due_date": issue.due_date.isoformat() if issue.due_date else None,
                        "priority": issue.priority
                    }
                )

            messages.success(request, f"Issue '{issue.title}' status updated to {status}")
        return redirect("assigned_issues")

    # Pagination
    paginator = Paginator(issues.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "assigned_issues.html", {
        "page_obj": page_obj,
        "statuses": ['Open', 'In Progress', 'Closed'],
        "status_filter": status_filter,
        "priority_filter": priority_filter,
        "due_date_filter": due_date_filter
    })



@login_required
def issue_create(request):
    user_orgs = UserOrganization.objects.filter(user=request.user).select_related('organization')

    # Filters from GET params
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    due_date_filter = request.GET.get('due_date')

    selected_org_id = request.POST.get('organization') or request.GET.get('organization')
    selected_org = None
    projects = []
    org_users = []

    if selected_org_id:
        selected_org = get_object_or_404(Organization, id=selected_org_id)
        projects = Project.objects.filter(organization=selected_org)
        org_users = UserOrganization.objects.filter(organization=selected_org).select_related('user')

    if request.method == 'POST' and request.POST.get('action') == 'create':
        title = request.POST.get('title')
        description = request.POST.get('description')
        project_id = request.POST.get('project')
        assigned_to_id = request.POST.get('assigned_to')
        due_date_str = request.POST.get('due_date')
        attachment_file = request.FILES.get('attachment')

        if not title or not project_id:
            messages.error(request, 'Title and project are required')
        else:
            project = get_object_or_404(Project, id=project_id)
            assigned_to = User.objects.get(id=assigned_to_id) if assigned_to_id else None

            # Parse due date safely
            due_date = None
            if due_date_str:
                try:
                    due_date = timezone.datetime.strptime(due_date_str, '%Y-%m-%d')
                    due_date = timezone.make_aware(due_date)
                except ValueError:
                    messages.error(request, 'Invalid due date format. Use YYYY-MM-DD.')
                    due_date = None

            # Create the issue
            issue = Issue.objects.create(
                title=title,
                description=description,
                project=project,
                assigned_to=assigned_to,
                due_date=due_date,
                attachment=attachment_file,
                created_by=request.user
            )

            # Broadcast new issue to the assigned user
            if assigned_to:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"user_{assigned_to.id}_issues",
                    {
                        "type": "issue_update",
                        "issue_id": issue.id,
                        "title": issue.title,
                        "project_name": issue.project.name,
                        "status": issue.status,
                        "due_date": issue.due_date.isoformat() if issue.due_date else None,
                        "priority": issue.priority
                    }
                )

            messages.success(request, 'Issue created successfully')
            return redirect('issue_create')

    elif request.POST.get('action') == 'delete':
        issue_id = request.POST.get('id')
        if issue_id:
            try:
                issue = Issue.objects.get(id=issue_id, created_by=request.user)
                issue.delete()
                messages.success(request, 'Issue deleted successfully.')
                return redirect('issue_create')
            except Issue.DoesNotExist:
                messages.error(request, 'Issue not found or you do not have permission to delete it.')
    # Filter issues
    user_issues = Issue.objects.filter(created_by=request.user).select_related(
        'project', 'project__organization', 'assigned_to'
    )
    if status_filter:
        user_issues = user_issues.filter(status=status_filter)
    if priority_filter:
        user_issues = user_issues.filter(priority=priority_filter)
    if due_date_filter:
        try:
            due_date_parsed = timezone.datetime.strptime(due_date_filter, '%Y-%m-%d')
            due_date_parsed = timezone.make_aware(due_date_parsed)
            user_issues = user_issues.filter(due_date=due_date_parsed)
        except ValueError:
            messages.error(request, 'Invalid due date filter format. Use YYYY-MM-DD.')

    # Pagination
    paginator = Paginator(user_issues.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'issue.html', {
        'user_orgs': user_orgs,
        'selected_org': selected_org,
        'projects': projects,
        'org_users': org_users,
        'page_obj': page_obj,
        'statuses': ['Open', 'In Progress', 'Closed'],
        'priorities': ['Low', 'Medium', 'High'],
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'due_date_filter': due_date_filter
    })




# @login_required
# def issue_create(request):
#     user_orgs = UserOrganization.objects.filter(user=request.user).select_related('organization')

#     selected_org_id = request.POST.get('organization') or request.GET.get('organization')
#     selected_org = None
#     projects = []
#     org_users = []

#     if selected_org_id:
#         selected_org = get_object_or_404(Organization, id=selected_org_id)
#         projects = Project.objects.filter(organization=selected_org)
#         org_users = UserOrganization.objects.filter(organization=selected_org).select_related('user')

#     if request.method == 'POST' and request.POST.get('action') == 'create':
#         title = request.POST.get('title')
#         description = request.POST.get('description')
#         project_id = request.POST.get('project')
#         assigned_to_id = request.POST.get('assigned_to')

#         if not title or not project_id:
#             messages.error(request, 'Title and project are required')
#         else:
#             project = get_object_or_404(Project, id=project_id)
#             assigned_to = User.objects.get(id=assigned_to_id) if assigned_to_id else None
#             issue = Issue.objects.create(
#                 title=title,
#                 description=description,
#                 project=project,
#                 assigned_to=assigned_to,
#                 created_by=request.user
#             )

#             # --- Broadcast new issue to the assigned user ---
#             if assigned_to:
#                 channel_layer = get_channel_layer()
#                 async_to_sync(channel_layer.group_send)(
#                     f"user_{assigned_to.id}_issues",
#                     {
#                         "type": "issue_update",
#                         "issue_id": issue.id,
#                         "title": issue.title,
#                         "project_name": issue.project.name,
#                         "status": issue.status,
#                         "due_date": issue.due_date.isoformat() if issue.due_date else None,
#                         "priority": issue.priority
#                     }
#                 )
#             # if assigned_to:
#             #     channel_layer = get_channel_layer()
#             #     async_to_sync(channel_layer.group_send)(
#             #         f"issue_{issue.id}",
#             #         {
#             #             "type": "issue_update",
#             #             "issue_id": issue.id,
#             #             "title": issue.title,
#             #             "project_name": issue.project.name,
#             #             "status": issue.status,
#             #             "due_date": issue.due_date.isoformat() if issue.due_date else None,
#             #             "priority": issue.priority,
#             #             "assigned_to_id": assigned_to.id,
#             #             "created_by_id": request.user.id
#             #         }
#             #     )

#             messages.success(request, 'Issue created successfully')
#             return redirect('issue_create')

#     user_issues = Issue.objects.filter(created_by=request.user).select_related(
#         'project', 'project__organization', 'assigned_to'
#     )

#     return render(request, 'issue.html', {
#         'user_orgs': user_orgs,
#         'selected_org': selected_org,
#         'projects': projects,
#         'org_users': org_users,
#         'user_issues': user_issues
#     })

# @login_required
# def assigned_issues(request):
#     issues = Issue.objects.filter(assigned_to=request.user).select_related('project', 'project__organization')
#     statuses = ['Open', 'In Progress', 'Closed']
#     return render(request, 'assigned_issues.html', {'issues': issues, 'statuses': statuses})

    