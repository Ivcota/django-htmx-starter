import logging

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def home(request):
    return render(request, 'home.html')


@login_required
def dashboard(request):
    return render(request, 'dashboard.html')


def counter(request):
    return render(request, 'counter.html', {'count': 0})


@require_POST
def counter_update(request):
    if not request.htmx:
        return HttpResponseBadRequest()
    try:
        count = int(request.POST.get('count', 0))
    except (ValueError, TypeError):
        count = 0
    action = request.POST.get('action')
    if action == 'increment':
        count += 1
    elif action == 'decrement':
        count -= 1
    return render(request, 'cotton/counter.html', {'count': count})


def health(request):
    try:
        connection.ensure_connection()
        return JsonResponse({'status': 'ok'})
    except Exception:
        logger.exception('Health check failed')
        return JsonResponse({'status': 'unhealthy'}, status=503)


def error_404(request, exception):
    return render(request, '404.html', status=404)


def error_500(request):
    return render(request, '500.html', status=500)
