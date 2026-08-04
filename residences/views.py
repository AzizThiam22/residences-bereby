from .forms import ReservationForm, ContactForm, AbonnementDisponibiliteForm
from django.shortcuts import render, get_object_or_404, redirect
from .models import Unite, Parametres, VilleCle, Reservation
from .forms import ReservationForm, ContactForm
from django.utils import translation
from django.utils import timezone
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from .emails import envoyer_email_confirmation
from .cinetpay import creer_paiement, verifier_paiement, CinetPayNonConfigure
from django.db.models import Q
from datetime import date, datetime
from django.urls import reverse
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


def calendrier_ical(request, pk):
    """
    Exporte le calendrier de disponibilité d'une unité au format iCal (RFC 5545).
    Chaque réservation 'en_attente' ou 'confirmee' devient un événement qui
    bloque ses dates. On peut importer ce fichier dans un calendrier externe
    (ex: Airbnb) pour éviter les doubles réservations.
    URL publique : pas besoin de connexion (Airbnb doit pouvoir lire ce fichier).
    """
    unite = get_object_or_404(Unite, pk=pk)

    # Réservations qui bloquent les dates : en attente (à confirmer) ou confirmées.
    # Les réservations annulées sont exclues : elles ne bloquent plus rien.
    reservations = unite.reservations.filter(
        statut__in=['en_attente', 'confirmee']
    ).order_by('date_arrivee')

    # On génère le fichier iCal à la main (format texte standard RFC 5545),
    # sans ajouter de dépendance externe.
    # Un événement sur des dates seules (VALUE=DATE) n'a pas de fuseau horaire :
    # pas de risque de décalage selon la localisation d'Airbnb.
    lignes = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Residences Bereby//Disponibilite//FR',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:Résidences Bereby - {unite.nom}',
        'X-WR-TIMEZONE:Africa/Abidjan',
    ]

    # Horodatage de génération du fichier (obligatoire par le standard)
    maintenant = datetime.now().strftime('%Y%m%dT%H%M%S')

    for reservation in reservations:
        # Les dates sont au format AAAAMMJJ (sans heure).
        # IMPORTANT : DTEND est EXCLUSIF dans le standard iCal : le jour de départ
        # n'est pas considéré comme occupé. On met donc la date de départ telle quelle.
        date_arrivee = reservation.date_arrivee.strftime('%Y%m%d')
        date_depart = reservation.date_depart.strftime('%Y%m%d')

        lignes.append('BEGIN:VEVENT')
        # UID stable : indispensable pour que les calendriers externes
        # synchronisent correctement les annulations / modifications
        lignes.append(f'UID:reservation-{reservation.pk}@residences-bereby')
        lignes.append(f'DTSTAMP:{maintenant}')
        lignes.append(f'DTSTART;VALUE=DATE:{date_arrivee}')
        lignes.append(f'DTEND;VALUE=DATE:{date_depart}')
        lignes.append(f'SUMMARY:Réservé - {reservation.nom_client}')
        # TRANSP:OPAQUE = cette période est bien indisponible (pas un simple rappel)
        lignes.append('TRANSP:OPAQUE')
        lignes.append('END:VEVENT')

    lignes.append('END:VCALENDAR')

    # Le standard iCal exige des retours à la ligne en CRLF
    contenu = '\r\n'.join(lignes) + '\r\n'

    response = HttpResponse(
        contenu, content_type='text/calendar; charset=utf-8')
    # filename est proposé au téléchargement ; le nom contient celui de l'unité
    response['Content-Disposition'] = f'attachment; filename="{unite.nom}.ics"'
    return response


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
        # Le formulaire a été soumis : on le reconstruit avec les données envoyées.
        # request.FILES est transmis pour que la capture d'écran (preuve de paiement)
        # puisse être reçue et enregistrée par Django.
        form = ReservationForm(request.POST, request.FILES)
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

            # IMPORTANT : model.save() seul ne stocke PAS le fichier joint
            # (la preuve de paiement). On doit l'écrire explicitement sur le
            # disque avec FileField.save(), sinon seule la référence en base
            # serait enregistrée sans le fichier lui-même.
            preuve = form.cleaned_data.get('preuve_paiement')
            if preuve:
                reservation.preuve_paiement.save(
                    preuve.name, preuve, save=False)
                reservation.save()

            # Envoie l'email de confirmation avec le code et le QR code
            try:
                envoyer_email_confirmation(reservation, request)
            except Exception as e:
                # On ne bloque pas la réservation si l'email échoue
                # (sera loggé en production)
                print(f"Erreur envoi email : {e}")

            # redirect évite qu'un rechargement de page ne soumette le formulaire 2 fois
            # Si le client a choisi de payer par carte, on l'envoie vers le
            # paiement en ligne CinetPay ; sinon, page de confirmation classique.
            if reservation.moyen_paiement == 'carte':
                return redirect('residences:paiement',
                                code=reservation.code_confirmation)
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


def paiement(request, code):
    """
    Initie le paiement en ligne CinetPay pour une réservation (moyen de
    paiement 'carte'). Redirige le client vers la page de paiement CinetPay.
    Si l'intégration n'est pas encore configurée, affiche une page explicative.
    """
    parametres = get_object_or_404(Parametres, pk=1)
    reservation = get_object_or_404(
        Reservation, code_confirmation__iexact=code)

    # On marque le paiement comme en attente avant d'initier la session
    if reservation.paiement_statut == 'non_paye':
        reservation.paiement_statut = 'en_attente'
        reservation.save(update_fields=['paiement_statut'])

    try:
        # L'appel à CinetPay peut échouer (identifiants absents, réseau...)
        url_paiement = creer_paiement(reservation, request)
    except CinetPayNonConfigure:
        # Intégration pas encore activée : on affiche une page explicative
        return render(request, 'residences/paiement_erreur.html', {
            'reservation': reservation,
            'parametres': parametres,
            'message': (
                "L'intégration du paiement en ligne (CinetPay) n'est pas "
                "encore activée. Votre demande a bien été enregistrée ; "
                "notre équipe vous contactera pour régler le paiement."
            ),
        })
    except Exception as e:
        # Erreur imprévue côté CinetPay
        print(f"Erreur création paiement CinetPay : {e}")
        return render(request, 'residences/paiement_erreur.html', {
            'reservation': reservation,
            'parametres': parametres,
            'message': (
                "Une erreur est survenue lors de la création du paiement. "
                "Veuillez réessayer ou contacter la résidence."
            ),
        })

    # Le client paie sur la page sécurisée de CinetPay
    return redirect(url_paiement)


def paiement_retour(request, code):
    """
    Page de retour sur le site après le paiement CinetPay.
    CinetPay redirige le client ici une fois le paiement tenté.
    La confirmation fiable passe par le webhook (paiement_notification) ;
    cette page affiche simplement le récapitulatif et l'état du paiement.
    """
    parametres = get_object_or_404(Parametres, pk=1)
    reservation = get_object_or_404(
        Reservation, code_confirmation__iexact=code)

    context = {
        'reservation': reservation,
        'parametres': parametres,
    }
    return render(request, 'residences/paiement_retour.html', context)


@csrf_exempt
def paiement_notification(request, code):
    """
    Webhook appelé par CinetPay après le traitement du paiement
    (notify_url). On vérifie auprès de l'API CinetPay le vrai statut
    de la transaction, puis on met à jour la réservation.
    csrf_exempt : CinetPay envoie la requête sans cookie de session.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)  # Method Not Allowed

    reservation = get_object_or_404(
        Reservation, code_confirmation__iexact=code)

    try:
        statut, reference = verifier_paiement(reservation.code_confirmation)
    except CinetPayNonConfigure:
        # Intégration pas encore activée : on ne peut pas confirmer
        return HttpResponse('CinetPay non configuré', status=503)
    except Exception as e:
        print(f"Erreur vérification paiement CinetPay : {e}")
        return HttpResponse('Erreur de vérification', status=400)

    # Met à jour le suivi du paiement selon le statut retourné par CinetPay
    if statut == 'ACCEPTED':
        reservation.paiement_statut = 'effectue'
        reservation.paiement_reference = reference
        reservation.date_paiement = timezone.now()
        reservation.save()
    elif statut == 'REFUSED':
        reservation.paiement_statut = 'refuse'
        reservation.save()
    elif statut == 'PENDING':
        reservation.paiement_statut = 'en_attente'
        reservation.save()

    # CinetPay attend une réponse rapide en 200
    return HttpResponse('OK', status=200)


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


def unites_avec_statut_aujourd_hui():
    """
    Calcule, pour chaque unité disponible, son statut du jour :
    'libre', 'occupee' (réservation confirmée en cours) ou 'attente'
    (réservation en attente en cours). Utilisé par le dashboard et
    par la page d'activités du gérant.
    """
    aujourd_hui = date.today()

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

    return unites_avec_statut


@login_required(login_url='/login/')
def dashboard(request):
    """
    Tableau de bord réservé au staff (gestionnaire / admin).
    Affiche une vue d'ensemble des réservations, unités et messages,
    avec la possibilité de confirmer ou d'annuler des réservations.
    Un gérant (compte simple non-staff) est redirigé vers sa page
    d'activités : il n'a pas accès à ces actions de gestion.
    """
    # Page réservée au staff : un gérant est redirigé vers sa page d'activités
    if not request.user.is_staff:
        return redirect('residences:activites')

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
    # Statut du jour de chaque unité (libre / occupée / en attente)
    unites_avec_statut = unites_avec_statut_aujourd_hui()

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

    # ===== SYNCHRONISATION AIRBNB (iCal) =====
    # Pour chaque unité, on prépare le lien iCal public à copier dans Airbnb.
    # build_absolute_uri + reverse : l'URL absolue est nécessaire, car Airbnb
    # doit pouvoir accéder au fichier depuis Internet (pas un chemin relatif).
    unites_ical = [
        {
            'nom': item['unite'].nom,
            'url': request.build_absolute_uri(
                reverse('residences:calendrier_ical', args=[item['unite'].pk])),
        }
        for item in unites_avec_statut
    ]

    parametres = get_object_or_404(Parametres, pk=1)

    context = {
        'aujourd_hui': aujourd_hui,
        'arrivees_aujourd_hui': arrivees_aujourd_hui,
        'departs_aujourd_hui': departs_aujourd_hui,
        'reservations_en_attente': reservations_en_attente,
        'reservations_a_venir': reservations_a_venir,
        'messages_non_traites': messages_non_traites,
        'unites_avec_statut': unites_avec_statut,
        'unites_ical': unites_ical,
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
    Confirme ou annule une réservation depuis le dashboard.
    Si annulation : notifie les abonnés et le gestionnaire.
    Réservé au staff (gestionnaire / admin) : un gérant n'a pas le
    droit de confirmer ou d'annuler des réservations.
    """
    from .emails import envoyer_notifications_disponibilite, envoyer_notification_gestionnaire

    # Page réservée au staff : un gérant est redirigé vers sa page d'activités
    if not request.user.is_staff:
        return redirect('residences:activites')

    reservation = get_object_or_404(Reservation, pk=reservation_id)
    parametres = get_object_or_404(Parametres, pk=1)

    if action == 'confirmer':
        reservation.statut = 'confirmee'
        reservation.save()

    elif action == 'annuler':
        reservation.statut = 'annulee'
        reservation.save()

        # Notifie les clients abonnés à cette unité
        try:
            nb = envoyer_notifications_disponibilite(
                reservation.unite, raison='annulation')
            print(f"{nb} notification(s) envoyée(s) pour {reservation.unite.nom}")
        except Exception as e:
            print(f"Erreur notifications clients : {e}")

        # Notifie le gestionnaire
        try:
            envoyer_notification_gestionnaire(
                reservation.unite, 'annulation', parametres)
        except Exception as e:
            print(f"Erreur notification gestionnaire : {e}")

    return redirect('residences:dashboard')


def gestionnaire_login(request):
    """
    Page de connexion de l'espace réservé (gestionnaire et gérant).
    Accessible sans être connecté. Si déjà connecté, redirige vers
    l'espace correspondant au rôle :
    - staff (gestionnaire / admin) → dashboard
    - compte simple (gérant) → page d'activités
    """
    # Si déjà connecté, redirige vers l'espace correspondant à son rôle
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('residences:dashboard')
        return redirect('residences:activites')

    parametres = get_object_or_404(Parametres, pk=1)
    erreur = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # authenticate() vérifie les identifiants dans la base Django
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Connexion réussie : crée la session, puis redirige vers
            # l'espace correspondant au rôle de l'utilisateur
            login(request, user)

            # staff (gestionnaire / admin) → dashboard
            # compte simple (gérant) → page d'activités
            if user.is_staff:
                next_url = request.GET.get('next', '/dashboard/')
            else:
                next_url = request.GET.get('next', '/activites/')

            return redirect(next_url)
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
    Déconnecte le gestionnaire ou le gérant et redirige vers la page de login.
    """
    logout(request)
    return redirect('residences:login')


@login_required(login_url='/login/')
def activites(request):
    """
    Page du gérant : vue d'ensemble (lecture seule) sur les activités de la
    résidence — arrivées / départs du jour, disponibilité des unités et
    prochaines réservations.
    Réservée aux comptes simples (gérants, non-staff). Un membre du staff
    (gestionnaire / admin) est redirigé vers le dashboard.
    """
    # Un membre du staff a déjà son propre espace de gestion :
    # on le redirige vers le dashboard
    if request.user.is_staff:
        return redirect('residences:dashboard')

    aujourd_hui = date.today()

    # Arrivées du jour (en attente ou confirmées)
    arrivees_aujourd_hui = Reservation.objects.filter(
        date_arrivee=aujourd_hui,
        statut__in=['en_attente', 'confirmee']
    )

    # Départs du jour (confirmés uniquement)
    departs_aujourd_hui = Reservation.objects.filter(
        date_depart=aujourd_hui,
        statut='confirmee'
    )

    # Prochaines réservations confirmées, triées par date d'arrivée
    reservations_a_venir = Reservation.objects.filter(
        statut='confirmee',
        date_arrivee__gte=aujourd_hui
    ).order_by('date_arrivee')

    # Réservations en attente de confirmation (affichées en compteur)
    reservations_en_attente = Reservation.objects.filter(
        statut='en_attente'
    ).order_by('-date_creation')

    # Statut du jour de chaque unité (libre / occupée / en attente)
    unites_avec_statut = unites_avec_statut_aujourd_hui()

    parametres = get_object_or_404(Parametres, pk=1)

    context = {
        'aujourd_hui': aujourd_hui,
        'arrivees_aujourd_hui': arrivees_aujourd_hui,
        'departs_aujourd_hui': departs_aujourd_hui,
        'reservations_a_venir': reservations_a_venir,
        'reservations_en_attente': reservations_en_attente,
        'unites_avec_statut': unites_avec_statut,
        'parametres': parametres,
        # Compteurs pour les cartes statistiques
        'nb_en_attente': reservations_en_attente.count(),
        'nb_libres': sum(1 for u in unites_avec_statut if u['statut'] == 'libre'),
        'nb_occupees': sum(1 for u in unites_avec_statut if u['statut'] == 'occupee'),
    }
    return render(request, 'residences/activites.html', context)


def abonnement_disponibilite(request, pk):
    """
    Permet à un client de s'abonner pour être notifié
    quand une unité spécifique se libère.
    On utilise transaction.atomic() pour isoler l'IntegrityError
    (doublon email+unité) sans casser la transaction principale.
    """
    from django.db import transaction, IntegrityError

    unite = get_object_or_404(Unite, pk=pk)
    parametres = get_object_or_404(Parametres, pk=1)

    if request.method == 'POST':
        form = AbonnementDisponibiliteForm(request.POST)
        if form.is_valid():
            try:
                # savepoint() crée un point de sauvegarde dans la transaction.
                # Si l'IntegrityError survient, seul ce bloc est annulé,
                # pas toute la transaction Django — ce qui permet de continuer
                # à faire des requêtes après (comme la redirection).
                with transaction.atomic():
                    abonnement = form.save(commit=False)
                    abonnement.unite = unite
                    abonnement.save()
            except IntegrityError:
                # Déjà abonné : on ignore silencieusement
                pass
            return redirect('residences:abonnement_success', pk=pk)
    else:
        form = AbonnementDisponibiliteForm()

    context = {
        'form': form,
        'unite': unite,
        'parametres': parametres,
    }
    return render(request, 'residences/abonnement_disponibilite.html', context)


def abonnement_success(request, pk):
    """Page de confirmation après inscription aux notifications."""
    unite = get_object_or_404(Unite, pk=pk)
    parametres = get_object_or_404(Parametres, pk=1)
    return render(request, 'residences/abonnement_success.html', {
        'unite': unite,
        'parametres': parametres,
    })
