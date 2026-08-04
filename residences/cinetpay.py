"""
Module de paiement CinetPay.

SOCLE D'INTÉGRATION : la passerelle n'est PAS encore active.
Elle fonctionnera dès que les identifiants (API key + site ID) seront
renseignés dans les réglages Django (settings.CINETPAY_API_KEY et
settings.CINETPAY_SITE_ID), une fois le compte CinetPay créé.

CinetPay gère le paiement par carte (Visa/Mastercard) et Mobile Money
dans plusieurs pays d'Afrique de l'Ouest, dont la Côte d'Ivoire (XOF).

Flux de paiement :
1. creer_paiement()  → on initie la session, CinetPay renvoie une URL
2. le client est redirigé vers cette URL et paie sur la page CinetPay
3. CinetPay appelle notify_url (webhook) pour confirmer le paiement
4. le client revient sur return_url (page de retour)
"""
import requests
from django.conf import settings


class CinetPayNonConfigure(Exception):
    """
    Exception levée quand les identifiants CinetPay ne sont pas renseignés
    dans les réglages. Signale que l'intégration n'est pas encore prête.
    """
    pass


def cinetpay_configure():
    """
    Retourne True si les identifiants CinetPay sont présents dans les
    réglages, False sinon (intégration désactivée).
    """
    cle_api = getattr(settings, 'CINETPAY_API_KEY', '')
    site_id = getattr(settings, 'CINETPAY_SITE_ID', '')
    return bool(cle_api and site_id)


def _url_base(request=None):
    """
    Retourne l'URL de base du site.
    Priorité à la requête (URL réelle vue par le client), sinon SITE_URL.
    L'URL doit être accessible depuis Internet (pas 127.0.0.1) pour que
    CinetPay puisse joindre le site.
    """
    if request:
        return request.build_absolute_uri('/')
    return getattr(settings, 'SITE_URL', 'http://127.0.0.1:8080')


def creer_paiement(reservation, request=None):
    """
    Crée une session de paiement CinetPay pour une réservation.
    Retourne l'URL de paiement vers laquelle rediriger le client.

    Lève CinetPayNonConfigure si l'intégration n'est pas prête,
    ou RuntimeError si CinetPay refuse la création.
    """
    if not cinetpay_configure():
        raise CinetPayNonConfigure(
            "Les identifiants CinetPay ne sont pas configurés.")

    base_url = _url_base(request)
    code = reservation.code_confirmation

    # Le code de confirmation est déjà unique : il sert de transaction_id
    # (CinetPay exige un identifiant unique par paiement).
    donnees = {
        'apikey': settings.CINETPAY_API_KEY,
        'site_id': settings.CINETPAY_SITE_ID,
        'transaction_id': code,
        # Montant en entier (le FCFA n'a pas de décimale)
        'amount': int(reservation.montant_total),
        'currency': 'XOF',
        'description': f"Réservation {reservation.unite.nom} - {reservation.nom_client}",
        # 'ALL' laisse le client choisir son canal (carte, Mobile Money...).
        # On pourrait restreindre à 'CARD' pour ne garder que la carte.
        'channels': 'ALL',
        'return_url': f"{base_url}paiement/{code}/retour/",
        'notify_url': f"{base_url}paiement/{code}/notification/",
        'customer_id': str(reservation.pk),
        'customer_name': reservation.nom_client,
        'customer_email': reservation.email_client,
        'customer_phone_number': reservation.telephone_client,
    }

    # Appel à l'API de création de paiement (POST JSON)
    reponse = requests.post(
        settings.CINETPAY_API_URL_PAIEMENT,
        json=donnees,
        timeout=30,
    )
    reponse.raise_for_status()
    donnees_reponse = reponse.json()

    # code != 0 → CinetPay a refusé la demande
    if donnees_reponse.get('code') != 0:
        message = donnees_reponse.get('message', 'Erreur CinetPay inconnue')
        raise RuntimeError(message)

    # L'URL de paiement est fournie dans data.payment_url
    return donnees_reponse['data']['payment_url']


def verifier_paiement(transaction_id):
    """
    Vérifie auprès de CinetPay le statut réel d'un paiement.
    transaction_id = code de confirmation de la réservation.

    Retourne un tuple (statut, reference) :
    - statut : 'ACCEPTED', 'REFUSED' ou 'PENDING'
    - reference : identifiant de transaction CinetPay (cpm_trans_id)

    La vérification se fait depuis le webhook pour éviter toute
    notification falsifiée.
    """
    if not cinetpay_configure():
        raise CinetPayNonConfigure(
            "Les identifiants CinetPay ne sont pas configurés.")

    reponse = requests.post(
        settings.CINETPAY_API_URL_VERIFICATION,
        json={
            'apikey': settings.CINETPAY_API_KEY,
            'site_id': settings.CINETPAY_SITE_ID,
            'transaction_id': transaction_id,
        },
        timeout=30,
    )
    reponse.raise_for_status()
    donnees_reponse = reponse.json()

    if donnees_reponse.get('code') != 0:
        message = donnees_reponse.get('message', 'Erreur CinetPay inconnue')
        raise RuntimeError(message)

    donnees = donnees_reponse.get('data', {})
    return donnees.get('status'), donnees.get('cpm_trans_id', '')
