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
        base_url = settings.SITE_URL

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
