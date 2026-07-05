from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # include() : toutes les URLs définies dans residences/urls.py
    # sont "branchées" à partir de la racine du site
    # i18n_urls : permet de changer la langue via /fr/ ou /en/ dans l'URL
    path('', include('residences.urls')),
]

# Sert les fichiers media (images) uniquement en mode DEBUG (développement)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
