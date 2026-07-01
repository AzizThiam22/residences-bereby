from django.shortcuts import render, get_object_or_404, redirect
from .models import Unite, Parametres, VilleCle
from .forms import ReservationForm, ContactForm


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
    """
    unite = get_object_or_404(Unite, pk=pk)
    parametres = get_object_or_404(Parametres, pk=1)

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
