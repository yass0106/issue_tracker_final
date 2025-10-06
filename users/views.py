from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.views.decorators.cache import cache_control

from chat.models import *

def login_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Fetch role for this user from UserOrganization
            user_org = UserOrganization.objects.filter(user=user).first()
            if user_org:
                request.session['role'] = user_org.role.lower()   # store 'owner', 'manager', 'member'
                request.session['organization_id'] = user_org.organization.id
            else:
                request.session['role'] = None

            messages.success(request, 'Login successful!')
            return redirect('/home/')
        else:
            messages.error(request, 'Invalid email or password. Please try again.')

    if request.user.is_authenticated:
        return redirect('/home/')

    return render(request, 'login.html')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def logout_page(request):
    logout(request)  
    messages.success(request, 'You have been logged out successfully.') 
    return redirect('/')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def home_page(request):
    overdue_issues = Issue.objects.filter(
        assigned_to=request.user,
        due_date__lt=timezone.now(),
        status__in=['Open', 'In Progress']
    )
    return render(request, 'home.html', {'user_overdue_issues': overdue_issues,'username':request.user.username})

def signup_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password1 = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Check if passwords match
        if password1 != confirm_password:
            messages.error(request, 'Passwords do not match. Please try again.')
            return render(request, 'signup.html')

        # Check if email is already taken
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email is already in use. Please try another.')
            return render(request, 'signup.html')

        # Create the new user
        user = User.objects.create_user(username=username, 
                                        email=email,
                                        password=password1
                                        )
        user.save()
        messages.success(request, 'Signup successful! You can now log in.')
        return redirect('login')
    if request.user.is_authenticated:
        return redirect('/home/')
    return render(request, 'signup.html')

