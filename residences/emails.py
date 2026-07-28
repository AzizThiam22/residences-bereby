import qrcode
import qrcode.image.svg
import io
import base64
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def generer_qr_code_base64(url):
    """
    Génère un QR code pointant vers l'URL donnée,
    et retourne son contenu encodé en base64 (pour l'intégrer directement dans un email HTML).
    On utilise le format PNG via Pillow (déjà installé).
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Crée l'image PNG en mémoire (pas besoin de fichier sur le disque)
    img = qr.make_image(fill_color="#1A3A3A", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    # Encode en base64 pour pouvoir l'intégrer dans le HTML de l'email
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def envoyer_email_confirmation(reservation, request=None):
    """
    Envoie un email de confirmation au client après sa pré-réservation.
    Contient :
    - Le récapitulatif de la réservation (unité, dates, code)
    - Un QR code qui pointe vers la page de consultation
    - Les instructions pour annuler ou contacter la résidence
    """
    # Construit l'URL de consultation de la réservation
    if request:
        base_url = request.build_absolute_uri('/')
    else:
        # Fallback vers SITE_URL si pas de requête disponible (ex: tests)
        from django.conf import settings
        base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8080')

    url_consultation = f"{base_url}ma-reservation/{reservation.code_confirmation}/"

    # Génère le QR code
    qr_base64 = generer_qr_code_base64(url_consultation)

    # Contexte transmis au template de l'email
    context = {
        'reservation': reservation,
        'url_consultation': url_consultation,
        'qr_base64': qr_base64,
    }

    # Génère le contenu HTML et texte brut de l'email
    html_content = render_to_string(
        'residences/emails/confirmation.html', context)
    text_content = render_to_string(
        'residences/emails/confirmation.txt', context)

    # Crée et envoie l'email
    email = EmailMultiAlternatives(
        subject=f"Confirmation de votre demande — {reservation.unite.nom} | Résidences Bereby",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[reservation.email_client],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


def envoyer_notifications_disponibilite(unite, raison='annulation'):
    """
    Envoie un email à tous les abonnés actifs d'une unité
    pour les informer qu'elle est maintenant disponible.
    raison : 'annulation' ou 'depart' (fin de séjour naturelle)
    """
    from .models import AbonnementDisponibilite
    from django.conf import settings

    abonnements = AbonnementDisponibilite.objects.filter(
        unite=unite,
        actif=True
    )

    if not abonnements.exists():
        return 0  # Aucun abonné, on s'arrête

    nb_envoyes = 0

    for abonnement in abonnements:
        try:
            # Contexte pour le template
            context = {
                'abonnement': abonnement,
                'unite': unite,
                'raison': raison,
                'url_reservation': f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8080')}/chambres/{unite.pk}/reserver/",
                'url_detail': f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8080')}/chambres/{unite.pk}/",
            }

            html_content = render_to_string(
                'residences/emails/disponibilite.html', context
            )
            text_content = render_to_string(
                'residences/emails/disponibilite.txt', context
            )

            email = EmailMultiAlternatives(
                subject=f"{unite.nom} est maintenant disponible — Résidences Bereby",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[abonnement.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            # Désactive l'abonnement après notification
            # (évite de spammer si l'unité se libère plusieurs fois)
            abonnement.actif = False
            abonnement.save()

            nb_envoyes += 1

        except Exception as e:
            print(f"Erreur notification {abonnement.email} : {e}")

    return nb_envoyes


def envoyer_notification_gestionnaire(unite, raison, parametres):
    """
    Notifie le gestionnaire par email quand une unité se libère.
    raison : 'annulation' ou 'depart'
    """
    from django.conf import settings

    if not parametres.email_contact:
        return  # Pas d'email gestionnaire configuré

    nb_abonnes = unite.abonnements.filter(actif=True).count()

    context = {
        'unite': unite,
        'raison': raison,
        'nb_abonnes': nb_abonnes,
        'url_dashboard': f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8080')}/dashboard/",
    }

    html_content = render_to_string(
        'residences/emails/notification_gestionnaire.html', context
    )
    text_content = render_to_string(
        'residences/emails/notification_gestionnaire.txt', context
    )

    email = EmailMultiAlternatives(
        subject=f"[Résidences Bereby] {unite.nom} vient de se libérer",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[parametres.email_contact],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()
