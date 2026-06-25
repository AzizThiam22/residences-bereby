from django.contrib import admin
from .models import Unite, Photo, Equipement, Reservation, ContactMessage, Parametres, VilleCle


# Inline = permet d'ajouter/modifier les photos directement DANS la page d'une unité,
# au lieu d'aller dans une page séparée. Pratique pour gérer la galerie.
class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1  # nombre de lignes vides affichées par défaut pour ajouter une nouvelle photo


@admin.register(Unite)
class UniteAdmin(admin.ModelAdmin):
    # Colonnes affichées dans la liste des unités
    list_display = ['nom', 'type_unite', 'etage',
                    'vue_mer', 'prix_nuit', 'disponible']

    # Filtres affichés sur le côté droit de la liste
    list_filter = ['type_unite', 'etage', 'vue_mer', 'disponible']

    # Barre de recherche (cherche dans le nom et la description)
    search_fields = ['nom', 'description_fr']

    # Permet de modifier ces champs directement depuis la liste, sans ouvrir la fiche
    list_editable = ['disponible', 'prix_nuit']

    # Affiche les photos directement dans la page de l'unité (voir PhotoInline ci-dessus)
    inlines = [PhotoInline]


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['unite', 'legende', 'principale', 'ordre']
    list_filter = ['unite']


@admin.register(Equipement)
class EquipementAdmin(admin.ModelAdmin):
    list_display = ['nom_fr', 'nom_en', 'icone']
    # filter_horizontal améliore l'affichage des champs ManyToMany (double liste avec recherche)
    filter_horizontal = ['unites']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['nom_client', 'unite',
                    'date_arrivee', 'date_depart', 'statut']
    list_filter = ['statut', 'unite']
    search_fields = ['nom_client', 'email_client', 'telephone_client']
    # Permet de changer le statut directement depuis la liste (ex: passer "en_attente" à "confirmee")
    list_editable = ['statut']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['nom', 'email', 'sujet', 'date_envoi', 'traite']
    list_filter = ['traite']
    list_editable = ['traite']


@admin.register(Parametres)
class ParametresAdmin(admin.ModelAdmin):
    # Empêche d'ajouter un 2e enregistrement (rappel : c'est un singleton)
    def has_add_permission(self, request):
        return not Parametres.objects.exists()

    # Empêche la suppression du seul enregistrement existant
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VilleCle)
class VilleCleAdmin(admin.ModelAdmin):
    list_display = ['nom', 'distance_km', 'temps_trajet', 'ordre']
    list_editable = ['distance_km', 'temps_trajet', 'ordre']
