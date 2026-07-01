from django.urls import path
from . import views

# app_name permet de référencer ces URLs de façon unique dans les templates
# (ex: {% url 'residences:unite_detail' pk=1 %}), utile si plusieurs apps ont des noms similaires
app_name = 'residences'

urlpatterns = [
    path('', views.home, name='home'),
    path('chambres/', views.unite_list, name='unite_list'),
    path('chambres/<int:pk>/', views.unite_detail, name='unite_detail'),
    path('localisation/', views.localisation, name='localisation'),
    path('chambres/<int:pk>/reserver/',
         views.reservation_form, name='reservation_form'),
    path('reservation/confirmee/', views.reservation_success,
         name='reservation_success'),
    path('contact/', views.contact, name='contact'),
    path('contact/envoye/', views.contact_success, name='contact_success'),
]
