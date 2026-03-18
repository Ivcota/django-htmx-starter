from django.urls import path

from payments import views

app_name = 'payments'

urlpatterns = [
    path('checkout/<str:price_id>/', views.checkout, name='checkout'),
    path('success/', views.success, name='success'),
    path('cancel/', views.cancel, name='cancel'),
]
