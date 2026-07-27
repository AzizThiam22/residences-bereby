from django.shortcuts import render, get_object_or_404, redirect
from .models import Unite, Parametres, VilleCle, Reservation
from .forms import ReservationForm, ContactForm
from django.utils import translation
from django.http import HttpResponseRedirect
from .emails import envoyer_email_confirmation
from django.db.models import Q
from datetime import date
from .models import Unite, Parametres, VilleCle, Reservation, ContactMessage
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


def home(request):
    """
    Page d'accueil : présente la résidence, met en avant la vue océan,
    et affiche un aperçu des unités disponibles.
    """
    # On récupère seulement les unités disponibles, qui ne sont pas le local commercial,
    # pour les afficher en aperçu sur la page d'accueil
    unites = Unite.objects.filter(disponible=True).exclude(
        type_unite='local_commercial')

    # On récupère les paramètres du site (un seul enregistrement, pk=1)
    # get_object_or_404 : si jamais aucun enregistrement n'existe, affiche une erreur 404
    # plutôt qu'un crash silencieux
    parametres = get_object_or_404(Parametres, pk=1)

    # 'context' = dictionnaire de données transmises au template HTML
    context = {
        'unites': unites,
        'parametres': parametres,
    }
    return render(request, 'residences/home.html', context)


def unite_list(request):
    """
    Page listant toutes les unités disponibles, avec un filtre optionnel
    sur la vue mer via le paramètre d'URL ?vue_mer=1
    """
    unites = Unite.objects.filter(disponible=True).exclude(
        type_unite='local_commercial')

    # request.GET.get('vue_mer') récupère la valeur du paramètre d'URL ?vue_mer=...
    # Si présent (peu importe la valeur), on filtre pour ne garder que les unités vue mer
    if request.GET.get('vue_mer'):
        unites = unites.filter(vue_mer=True)

    parametres = get_object_or_404(Parametres, pk=1)

    context = {
        'unites': unites,
        'parametres': parametres,
    }
    return render(request, 'residences/unite_list.html', context)


def unite_detail(request, pk):
    """
    Page détaillée d'une unité précise : toutes les photos, la description complète,
    les équipements, et un futur bouton de réservation.
    pk = "primary key", l'identifiant unique de l'unité dans la base de données.
    """
    # get_object_or_404 : récupère l'unité demandée, ou affiche une 404 si elle n'existe pas
    unite = get_object_or_404(Unite, pk=pk)
    parametres = get_object_or_404(Parametres, pk=1)

    # On récupère les réservations en_attente ou confirmées pour cette unité,
    # triées par date d'arrivée croissante (les plus proches dans le temps en premier).
    # On exclut les réservations "annulee" : elles ne bloquent plus rien.
    periodes_reservees = unite.reservations.filter(
        statut__in=['en_attente', 'confirmee']
    ).order_by('date_arrivee')

    context = {
        'unite': unite,
        'parametres': parametres,
        'periodes_reservees': periodes_reservees,
    }
    return render(request, 'residences/unite_detail.html', context)


def localisation(request):
    """
    Page dédiée à la localisation : carte interactive (résidence + villes clés)
    et liste des distances/temps de trajet.
    """
    parametres = get_object_or_404(Parametres, pk=1)
    villes = VilleCle.objects.all()

    context = {
        'parametres': parametres,
        'villes': villes,
    }
    return render(request, 'residences/localisation.html', context)


def reservation_form(request, pk):
    """
    Affiche et traite le formulaire de pré-réservation pour une unité donnée.
    pk = identifiant de l'unité concernée (récupéré depuis l'URL).
    On ajoute les périodes réservées pour afficher le calendrier
    de disponibilité sur cette page également.
    """
    unite = get_object_or_404(Unite, pk=pk)
    parametres = get_object_or_404(Parametres, pk=1)

    # Récupère les périodes déjà réservées pour cette unité
    # (même logique que sur la page détail)
    periodes_reservees = unite.reservations.filter(
        statut__in=['en_attente', 'confirmee']
    ).order_by('date_arrivee')

    if request.method == 'POST':
        # Le formulaire a été soumis : on le reconstruit avec les données envoyées
        form = ReservationForm(request.POST)
        # On attache l'unité au formulaire AVANT d'appeler is_valid(),
        # pour que clean() puisse y accéder via self.unite
        form.unite = unite

        if form.is_valid():
            # form.save(commit=False) crée l'objet Reservation en mémoire,
            # SANS l'enregistrer encore en base de données — ça nous laisse
            # le temps d'ajouter manuellement le champ 'unite' avant la sauvegarde
            reservation = form.save(commit=False)
            reservation.unite = unite
            reservation.save()

            # Envoie l'email de confirmation avec le code et le QR code
            try:
                envoyer_email_confirmation(reservation, request)
            except Exception as e:
                # On ne bloque pas la réservation si l'email échoue
                # (sera loggé en production)
                print(f"Erreur envoi email : {e}")

            # redirect évite qu'un rechargement de page ne soumette le formulaire 2 fois
            return redirect('residences:reservation_success')
        # Si le formulaire n'est pas valide, on continue plus bas : il sera
        # ré-affiché avec les erreurs visibles pour l'utilisateur
    else:
        # Première visite de la page (pas encore de soumission) : formulaire vide
        form = ReservationForm()
        form.unite = unite  # utile aussi en GET si besoin d'affichage conditionnel plus tard

    context = {
        'form': form,
        'unite': unite,
        'parametres': parametres,
        'periodes_reservees': periodes_reservees,
    }
    return render(request, 'residences/reservation_form.html', context)


def reservation_success(request):
    """
    Page de confirmation affichée après l'envoi réussi d'une pré-réservation.
    """
    parametres = get_object_or_404(Parametres, pk=1)
    context = {'parametres': parametres}
    return render(request, 'residences/reservation_success.html', context)


def contact(request):
    """
    Page de contact : affiche les coordonnées, les réseaux sociaux,
    et un formulaire de contact général.
    """
    parametres = get_object_or_404(Parametres, pk=1)

    if request.method == 'POST':
        form = ContactForm(request.POST)

        if form.is_valid():
            # Sauvegarde le message en base de données (visible dans l'admin)
            form.save()
            return redirect('residences:contact_success')
    else:
        # Première visite : formulaire vide
        form = ContactForm()

    context = {
        'form': form,
        'parametres': parametres,
    }
    return render(request, 'residences/contact.html', context)


def contact_success(request):
    """
    Page de confirmation après envoi du formulaire de contact.
    """
    parametres = get_object_or_404(Parametres, pk=1)
    return render(request, 'residences/contact_success.html', {'parametres': parametres})


def changer_langue(request):
    """
    Vue personnalisée pour changer la langue active du site.
    Sauvegarde le choix dans un cookie valable 1 an.
    """
    if request.method == 'POST':
        langue = request.POST.get('language', 'fr')

        # Validation : on n'accepte que 'fr' ou 'en'
        if langue not in ('fr', 'en'):
            langue = 'fr'

        # Active la langue immédiatement pour cette requête
        translation.activate(langue)

        # Redirige vers la page d'accueil
        response = HttpResponseRedirect('/')

        # Sauvegarde le choix dans un cookie pour les prochaines visites
        response.set_cookie(
            'django_language',
            langue,
            max_age=365 * 24 * 60 * 60,
            httponly=False,
            samesite='Lax'
        )

        return response

    # Si accès direct sans POST, redirige vers l'accueil
    return HttpResponseRedirect('/')


def ma_reservation(request, code):
    """
    Page publique permettant à un client de consulter sa réservation
    uniquement avec son code de confirmation (pas besoin de compte).
    """
    parametres = get_object_or_404(Parametres, pk=1)

    # Cherche la réservation correspondant à ce code
    # iexact = insensible à la casse (BRB-AB12 = brb-ab12)
    reservation = get_object_or_404(
        Reservation,
        code_confirmation__iexact=code
    )

    context = {
        'reservation': reservation,
        'parametres': parametres,
    }
    return render(request, 'residences/ma_reservation.html', context)


@login_required(login_url='/login/')
def dashboard(request):
    """
    Tableau de bord réservé aux gestionnaires (staff uniquement).
    Affiche une vue d'ensemble des réservations, unités et messages.
    @staff_member_required redirige automatiquement vers /admin/login/
    si l'utilisateur n'est pas connecté ou n'est pas staff.
    """
    aujourd_hui = date.today()

    # ===== STATISTIQUES GÉNÉRALES =====

    # Réservations du jour (arrivées aujourd'hui)
    arrivees_aujourd_hui = Reservation.objects.filter(
        date_arrivee=aujourd_hui,
        statut__in=['en_attente', 'confirmee']
    )

    # Départs du jour
    departs_aujourd_hui = Reservation.objects.filter(
        date_depart=aujourd_hui,
        statut='confirmee'
    )

    # Réservations en attente de confirmation
    reservations_en_attente = Reservation.objects.filter(
        statut='en_attente'
    ).order_by('-date_creation')

    # Réservations confirmées à venir
    reservations_a_venir = Reservation.objects.filter(
        statut='confirmee',
        date_arrivee__gte=aujourd_hui
    ).order_by('date_arrivee')

    # Messages de contact non traités
    messages_non_traites = ContactMessage.objects.filter(
        traite=False
    ).order_by('-date_envoi')

    # ===== DISPONIBILITÉ DES UNITÉS =====
    # Pour chaque unité, on vérifie si elle est occupée aujourd'hui
    toutes_unites = Unite.objects.filter(
        disponible=True
    ).exclude(type_unite='local_commercial')

    # Unités occupées aujourd'hui (réservation confirmée qui couvre aujourd'hui)
    unites_occupees_ids = Reservation.objects.filter(
        statut='confirmee',
        date_arrivee__lte=aujourd_hui,
        date_depart__gt=aujourd_hui
    ).values_list('unite_id', flat=True)

    # Unités en attente aujourd'hui
    unites_attente_ids = Reservation.objects.filter(
        statut='en_attente',
        date_arrivee__lte=aujourd_hui,
        date_depart__gt=aujourd_hui
    ).values_list('unite_id', flat=True)

    # On enrichit chaque unité avec son statut du jour
    unites_avec_statut = []
    for unite in toutes_unites:
        if unite.pk in list(unites_occupees_ids):
            statut = 'occupee'
        elif unite.pk in list(unites_attente_ids):
            statut = 'attente'
        else:
            statut = 'libre'
        unites_avec_statut.append({'unite': unite, 'statut': statut})

    # ===== RECHERCHE =====
    # Permet de chercher une réservation par nom ou téléphone
    recherche = request.GET.get('q', '').strip()
    resultats_recherche = []

    if recherche:
        # Q() permet de combiner plusieurs conditions avec OR
        resultats_recherche = Reservation.objects.filter(
            Q(nom_client__icontains=recherche) |
            Q(telephone_client__icontains=recherche) |
            Q(email_client__icontains=recherche) |
            Q(code_confirmation__icontains=recherche)
        ).order_by('-date_creation')

    # ===== RÉSERVATIONS RÉCENTES (toutes, pour historique) =====
    reservations_recentes = Reservation.objects.select_related('unite').order_by(
        '-date_creation'
    )[:20]  # les 20 dernières

    parametres = get_object_or_404(Parametres, pk=1)

    context = {
        'aujourd_hui': aujourd_hui,
        'arrivees_aujourd_hui': arrivees_aujourd_hui,
        'departs_aujourd_hui': departs_aujourd_hui,
        'reservations_en_attente': reservations_en_attente,
        'reservations_a_venir': reservations_a_venir,
        'messages_non_traites': messages_non_traites,
        'unites_avec_statut': unites_avec_statut,
        'recherche': recherche,
        'resultats_recherche': resultats_recherche,
        'reservations_recentes': reservations_recentes,
        'parametres': parametres,
        # Compteurs pour les badges
        'nb_en_attente': reservations_en_attente.count(),
        'nb_messages': messages_non_traites.count(),
        'nb_arrivees': arrivees_aujourd_hui.count(),
    }
    return render(request, 'residences/dashboard.html', context)


@login_required(login_url='/login/')
def dashboard_action(request, reservation_id, action):
    """
    Permet de confirmer ou annuler une réservation directement depuis le dashboard,
    sans passer par l'interface admin.
    action : 'confirmer' ou 'annuler'
    """
    reservation = get_object_or_404(Reservation, pk=reservation_id)

    if action == 'confirmer':
        reservation.statut = 'confirmee'
        reservation.save()
    elif action == 'annuler':
        reservation.statut = 'annulee'
        reservation.save()

    # Redirige vers le dashboard avec un message de confirmation
    return redirect('residences:dashboard')


def gestionnaire_login(request):
    """
    Page de connexion dédiée aux gestionnaires.
    Accessible sans être connecté. Si déjà connecté, redirige vers le dashboard.
    """
    # Si déjà connecté, redirige directement vers le dashboard
    if request.user.is_authenticated:
        return redirect('residences:dashboard')

    parametres = get_object_or_404(Parametres, pk=1)
    erreur = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # authenticate() vérifie les identifiants dans la base Django
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_staff:
                # Connexion réussie : crée la session
                login(request, user)
                # Redirige vers le dashboard (ou la page demandée initialement)
                next_url = request.GET.get('next', '/dashboard/')
                return redirect(next_url)
            else:
                # Compte existant mais pas gestionnaire
                erreur = "Vous n'avez pas les droits d'accès au dashboard."
        else:
            # Identifiants incorrects
            erreur = "Identifiants incorrects. Veuillez réessayer."

    context = {
        'parametres': parametres,
        'erreur': erreur,
    }
    return render(request, 'residences/login.html', context)


def gestionnaire_logout(request):
    """
    Déconnecte le gestionnaire et redirige vers la page de login.
    """
    logout(request)
    return redirect('residences:login')
