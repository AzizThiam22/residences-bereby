"""
Filtres de template pour le formatage des prix.

Les prix sont stockés en base en décimal (ex : 35000.00) ; à l'affichage on veut :
- retirer les décimales (« .00 ») ;
- séparer les milliers par un espace : « 35 000 FCFA ».

Le filtre est indépendant de la langue active : le séparateur reste
toujours un espace, même quand le site est affiché en anglais.
"""
from django import template

register = template.Library()


@register.filter
def prix_fcfa(valeur):
    """
    Formate un prix (Decimal, int ou str) pour l'affichage :
    retire les décimales et sépare les milliers par un espace.
    Exemple : 30000.00 -> « 30 000 » (le suffixe FCFA reste dans le template).
    Si la valeur n'est pas un nombre valide, elle est renvoyée telle quelle.
    """
    try:
        # On convertit en nombre entier (arrondi) après avoir retiré
        # d'éventuels espaces déjà présents dans la chaîne
        entier = int(round(float(str(valeur).replace(' ', ''))))
    except (ValueError, TypeError):
        # Valeur non numérique : on l'affiche brute plutôt que de planter
        return str(valeur)
    # Le format « :, » insère des virgules (« 30,000 ») ;
    # on les remplace par des espaces pour obtenir « 30 000 »
    return f'{entier:,}'.replace(',', ' ')
