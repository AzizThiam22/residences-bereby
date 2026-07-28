from django.core.management.base import BaseCommand
from django.utils import timezone
from residences.models import Reservation, Parametres
from residences.emails import envoyer_notifications_disponibilite, envoyer_notification_gestionnaire


class Command(BaseCommand):
    """
    Commande Django à exécuter quotidiennement (via un cron job ou un scheduler).
    Vérifie les réservations dont la date de départ est passée et notifie
    les abonnés des unités libérées.

    Usage : python manage.py verifier_departs
    """
    help = "Vérifie les départs du jour et notifie les abonnés des unités libérées"

    def handle(self, *args, **options):
        aujourd_hui = timezone.now().date()

        self.stdout.write(f"Vérification des départs au {aujourd_hui}...")

        # Réservations confirmées dont la date de départ est aujourd'hui ou avant
        # (le client est parti, l'unité est libre)
        reservations_terminees = Reservation.objects.filter(
            statut='confirmee',
            date_depart__lte=aujourd_hui,
        )

        if not reservations_terminees.exists():
            self.stdout.write("Aucun départ à traiter aujourd'hui.")
            return

        parametres = Parametres.objects.filter(pk=1).first()
        unites_traitees = set()  # évite de notifier deux fois la même unité

        for reservation in reservations_terminees:
            unite = reservation.unite

            # On ne traite chaque unité qu'une seule fois
            if unite.pk in unites_traitees:
                continue

            unites_traitees.add(unite.pk)

            # Notifie les abonnés
            nb = envoyer_notifications_disponibilite(unite, raison='depart')
            if nb > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {unite.nom} : {nb} client(s) notifié(s)"
                    )
                )

            # Notifie le gestionnaire si email configuré
            if parametres and parametres.email_contact:
                try:
                    envoyer_notification_gestionnaire(
                        unite, 'depart', parametres)
                    self.stdout.write(f"  → Gestionnaire notifié")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"  → Erreur gestionnaire : {e}"))

        self.stdout.write(self.style.SUCCESS("Vérification terminée."))
