from django.utils import translation


class DefaultLanguageMiddleware:
    """
    Lit le cookie 'django_language' à chaque requête et active
    la langue correspondante. Si absent, force le français.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Lecture du cookie AVANT que la réponse soit générée
        langue = request.COOKIES.get('django_language', 'fr')

        # Validation : on n'accepte que 'fr' ou 'en'
        if langue not in ('fr', 'en'):
            langue = 'fr'

        # Active la langue pour TOUTE cette requête
        translation.activate(langue)
        request.LANGUAGE_CODE = langue

        # Génère la réponse avec la bonne langue active
        response = self.get_response(request)
        return response
