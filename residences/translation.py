from modeltranslation.translator import register, TranslationOptions
from .models import Unite, Equipement, VilleCle, Parametres


@register(Unite)
class UniteTranslationOptions(TranslationOptions):
    """
    Champs de l'unité à traduire.
    modeltranslation va créer automatiquement :
    - nom_fr, nom_en (à partir de 'nom')
    - description_fr, description_en (déjà présents dans votre modèle,
      modeltranslation les gérera automatiquement)
    """
    fields = ('nom', 'description')


@register(Equipement)
class EquipementTranslationOptions(TranslationOptions):
    """
    Champs de l'équipement à traduire.
    Vous aviez déjà nom_fr et nom_en dans le modèle —
    on les remplace par un seul champ 'nom' que modeltranslation dupliquera.
    """
    fields = ('nom_fr',)


@register(VilleCle)
class VilleCleTranslationOptions(TranslationOptions):
    fields = ('nom',)


@register(Parametres)
class ParametresTranslationOptions(TranslationOptions):
    fields = ('nom_residence', 'adresse')
