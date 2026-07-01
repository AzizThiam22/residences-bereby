from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns


urlpatterns = [
    path('admin/', admin.site.urls),
    # include() : toutes les URLs définies dans residences/urls.py
    # sont "branchées" à partir de la racine du site
    # i18n_urls : permet de changer la langue via /fr/ ou /en/ dans l'URL
    path('i18n/', include('django.conf.urls.i18n')),
]

# i18n_patterns préfixe automatiquement les URLs avec la langue active
# ex: /fr/chambres/, /en/chambres/
urlpatterns += i18n_patterns(
    path('', include('residences.urls')),
    # le français (langue par défaut) n'aura pas de préfixe /fr/
    prefix_default_language=False,
)

# Sert les fichiers media (images) uniquement en mode DEBUG (développement)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
