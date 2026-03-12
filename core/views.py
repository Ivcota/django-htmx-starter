from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    return render(request, 'home.html')


@login_required
def dashboard(request):
    return render(request, 'dashboard.html')


def counter(request):
    return render(request, 'counter.html', {'count': 0})


def counter_update(request):
    count = int(request.POST.get('count', 0))
    action = request.POST.get('action')
    if action == 'increment':
        count += 1
    elif action == 'decrement':
        count -= 1
    return render(request, 'cotton/counter.html', {'count': count})
