from django.urls import path
from . import views

# app_name permet de référencer ces URLs de façon unique dans les templates
# (ex: {% url 'residences:unite_detail' pk=1 %}), utile si plusieurs apps ont des noms similaires
app_name = 'residences'

urlpatterns = [
    path('', views.home, name='home'),
    path('chambres/', views.unite_list, name='unite_list'),
    path('chambres/<int:pk>/', views.unite_detail, name='unite_detail'),
    # Calendrier iCal d'une unité (pour la synchronisation avec Airbnb)
    path('chambres/<int:pk>/calendrier.ics',
         views.calendrier_ical, name='calendrier_ical'),
    path('localisation/', views.localisation, name='localisation'),
    path('chambres/<int:pk>/reserver/',
         views.reservation_form, name='reservation_form'),
    path('reservation/confirmee/', views.reservation_success,
         name='reservation_success'),
    # Paiement en ligne CinetPay (carte)
    path('paiement/<str:code>/', views.paiement, name='paiement'),
    path('paiement/<str:code>/retour/',
         views.paiement_retour, name='paiement_retour'),
    path('paiement/<str:code>/notification/',
         views.paiement_notification, name='paiement_notification'),
    path('contact/', views.contact, name='contact'),
    path('contact/envoye/', views.contact_success, name='contact_success'),
    path('langue/', views.changer_langue, name='changer_langue'),
    path('ma-reservation/<str:code>/',
         views.ma_reservation, name='ma_reservation'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/reservation/<int:reservation_id>/<str:action>/',
         views.dashboard_action, name='dashboard_action'),
    # Page d'activités du gérant (lecture seule)
    path('activites/', views.activites, name='activites'),
    # Authentification gestionnaire
    path('login/', views.gestionnaire_login, name='login'),
    path('logout/', views.gestionnaire_logout, name='logout'),
    path('chambres/<int:pk>/notifier/', views.abonnement_disponibilite,
         name='abonnement_disponibilite'),
    path('chambres/<int:pk>/notifier/confirme/',
         views.abonnement_success, name='abonnement_success'),
]
