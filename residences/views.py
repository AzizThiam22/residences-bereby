from django.shortcuts import render, get_object_or_404
from .models import Unite, Parametres


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

    context = {
        'unite': unite,
        'parametres': parametres,
    }
    return render(request, 'residences/unite_detail.html', context)
