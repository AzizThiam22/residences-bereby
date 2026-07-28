from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
from .models import Unite, Parametres, Reservation, VilleCle
from .forms import ReservationForm, ContactForm
from django.contrib.auth.models import User


# ===== TESTS DES MODÈLES =====

class UniteModelTest(TestCase):
    """Tests du modèle Unite : création, validation, méthodes."""

    def setUp(self):
        """
        setUp est appelé avant chaque test de cette classe.
        On crée une unité de base réutilisable dans tous les tests.
        """
        self.unite = Unite.objects.create(
            nom_fr="Studio Test",
            nom_en="Test Studio",
            type_unite="studio",
            etage=1,
            vue_mer=True,
            prix_nuit=35000,
            disponible=True,
        )

    def test_creation_unite(self):
        """Vérifie qu'une unité est bien créée avec les bons attributs."""
        self.assertEqual(self.unite.nom_fr, "Studio Test")
        self.assertEqual(self.unite.etage, 1)
        self.assertTrue(self.unite.vue_mer)
        self.assertTrue(self.unite.disponible)

    def test_str_unite(self):
        """Vérifie que __str__ retourne bien le format attendu."""
        self.assertIn("Studio Test", str(self.unite))
        self.assertIn("1er étage", str(self.unite))

    def test_prix_nuit_positif(self):
        """Le prix par nuit doit être positif."""
        self.assertGreater(self.unite.prix_nuit, 0)

    def test_type_unite_choices(self):
        """Le type d'unité doit faire partie des choix valides."""
        types_valides = ['studio', 'appartement', 'local_commercial']
        self.assertIn(self.unite.type_unite, types_valides)


class ParametresSingletonTest(TestCase):
    """Tests du modèle Parametres : comportement singleton."""

    def test_singleton(self):
        """
        Vérifie qu'il ne peut exister qu'un seul enregistrement Parametres.
        On utilise update_or_create pour simuler deux créations successives.
        """
        Parametres.objects.update_or_create(
            pk=1,
            defaults={
                'nom_residence_fr': "Résidences Bereby",
                'nom_residence_en': "Bereby Residences",
                'latitude': 4.65082,
                'longitude': -6.92441,
            }
        )
        Parametres.objects.update_or_create(
            pk=1,
            defaults={
                'nom_residence_fr': "Autre résidence",
                'nom_residence_en': "Other residence",
                'latitude': 5.0,
                'longitude': -7.0,
            }
        )
        # Il doit toujours n'y avoir qu'un seul enregistrement
        self.assertEqual(Parametres.objects.count(), 1)
        p_final = Parametres.objects.get(pk=1)
        self.assertEqual(p_final.nom_residence_fr, "Autre résidence")


class VilleCleModelTest(TestCase):
    """Tests du modèle VilleCle."""

    def test_creation_ville(self):
        """Vérifie la création d'une ville clé avec les bons attributs."""
        ville = VilleCle.objects.create(
            nom_fr="San-Pédro",
            nom_en="San-Pedro",
            latitude=4.7500,
            longitude=-6.6333,
            distance_km=52.6,
            temps_trajet="55 min",
        )
        self.assertEqual(ville.nom_fr, "San-Pédro")
        self.assertEqual(str(ville), "San-Pédro")


# ===== TESTS DES VUES =====

class HomeViewTest(TestCase):
    """Tests de la page d'accueil."""

    def setUp(self):
        """Crée les données minimales nécessaires pour que la vue home() fonctionne."""
        self.client = Client()
        # La vue home() appelle get_object_or_404(Parametres, pk=1)
        # donc Parametres doit exister
        Parametres.objects.create(
            nom_residence_fr="Résidences Bereby",
            nom_residence_en="Bereby Residences",
            latitude=4.65082,
            longitude=-6.92441,
        )

    def test_home_accessible(self):
        """La page d'accueil doit retourner un code HTTP 200."""
        response = self.client.get(reverse('residences:home'))
        self.assertEqual(response.status_code, 200)

    def test_home_template(self):
        """La page d'accueil doit utiliser le bon template."""
        response = self.client.get(reverse('residences:home'))
        self.assertTemplateUsed(response, 'residences/home.html')

    def test_home_contient_nom_residence(self):
        """La page d'accueil doit afficher le nom de la résidence."""
        response = self.client.get(reverse('residences:home'))
        self.assertContains(response, "Résidences Bereby")


class UniteListViewTest(TestCase):
    """Tests de la page de liste des unités."""

    def setUp(self):
        self.client = Client()
        Parametres.objects.create(
            nom_residence_fr="Résidences Bereby",
            nom_residence_en="Bereby Residences",
            latitude=4.65082,
            longitude=-6.92441,
        )
        # Crée deux unités de test
        Unite.objects.create(
            nom_fr="Studio Vue Mer", nom_en="Sea View Studio",
            type_unite="studio", etage=1, vue_mer=True,
            prix_nuit=38000, disponible=True,
        )
        Unite.objects.create(
            nom_fr="Studio Arrière", nom_en="Back Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )

    def test_liste_accessible(self):
        """La page de liste des unités doit retourner 200."""
        response = self.client.get(reverse('residences:unite_list'))
        self.assertEqual(response.status_code, 200)

    def test_liste_affiche_unites(self):
        """La page de liste doit afficher les unités disponibles."""
        response = self.client.get(reverse('residences:unite_list'))
        self.assertContains(response, "Studio Vue Mer")
        self.assertContains(response, "Studio Arrière")

    def test_filtre_vue_mer(self):
        """Le filtre ?vue_mer=1 doit n'afficher que les unités avec vue mer."""
        response = self.client.get(
            reverse('residences:unite_list') + '?vue_mer=1'
        )
        self.assertContains(response, "Studio Vue Mer")
        self.assertNotContains(response, "Studio Arrière")


class UniteDetailViewTest(TestCase):
    """Tests de la page de détail d'une unité."""

    def setUp(self):
        self.client = Client()
        Parametres.objects.create(
            nom_residence_fr="Résidences Bereby",
            nom_residence_en="Bereby Residences",
            latitude=4.65082,
            longitude=-6.92441,
        )
        self.unite = Unite.objects.create(
            nom_fr="Appartement Panorama",
            nom_en="Panorama Apartment",
            type_unite="appartement",
            etage=3, vue_mer=True,
            prix_nuit=50000, disponible=True,
        )

    def test_detail_accessible(self):
        """La page de détail d'une unité existante doit retourner 200."""
        response = self.client.get(
            reverse('residences:unite_detail', kwargs={'pk': self.unite.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_unite_inexistante(self):
        """Une unité inexistante doit retourner 404."""
        response = self.client.get(
            reverse('residences:unite_detail', kwargs={'pk': 9999})
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_affiche_prix(self):
        """La page de détail doit afficher le prix de l'unité."""
        response = self.client.get(
            reverse('residences:unite_detail', kwargs={'pk': self.unite.pk})
        )
        self.assertContains(response, "50000")


# ===== TESTS DES FORMULAIRES =====

class ReservationFormTest(TestCase):
    """Tests du formulaire de réservation."""

    def setUp(self):
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )
        # Dates de base : arrivée demain, départ dans 3 jours
        self.aujourd_hui = date.today()
        self.demain = self.aujourd_hui + timedelta(days=1)
        self.dans_3_jours = self.aujourd_hui + timedelta(days=3)

    def test_formulaire_valide(self):
        """Un formulaire avec toutes les données valides doit être accepté."""
        form = ReservationForm(data={
            'nom_client': 'Jean Dupont',
            'email_client': 'jean@test.com',
            'telephone_client': '+225 01 02 03 04 05',
            'date_arrivee': self.demain,
            'date_depart': self.dans_3_jours,
            'nombre_personnes': 2,
            'message': '',
        })
        form.unite = self.unite
        self.assertTrue(form.is_valid())

    def test_date_depart_avant_arrivee(self):
        """
        Un formulaire où la date de départ est avant l'arrivée doit être refusé.
        C'est la validation custom qu'on a ajoutée dans forms.py.
        """
        form = ReservationForm(data={
            'nom_client': 'Jean Dupont',
            'email_client': 'jean@test.com',
            'telephone_client': '+225 01 02 03 04 05',
            # date_depart AVANT date_arrivee
            'date_arrivee': self.dans_3_jours,
            'date_depart': self.demain,
            'nombre_personnes': 2,
        })
        form.unite = self.unite
        self.assertFalse(form.is_valid())
        self.assertTrue(
            "La date de départ doit être postérieure à la date d'arrivée.",
            str(form.errors)
        )

    def test_chevauchement_reservation(self):
        """
        Une réservation dont les dates chevauchent une réservation existante
        (en_attente ou confirmée) doit être refusée.
        """
        # Crée une réservation existante du 5 au 10
        dans_5_jours = self.aujourd_hui + timedelta(days=5)
        dans_10_jours = self.aujourd_hui + timedelta(days=10)

        Reservation.objects.create(
            unite=self.unite,
            nom_client="Client Existant",
            email_client="existant@test.com",
            telephone_client="+225 00 00 00 00 00",
            date_arrivee=dans_5_jours,
            date_depart=dans_10_jours,
            statut='confirmee',
        )

        # Tente une réservation du 7 au 12 (chevauche la précédente)
        dans_7_jours = self.aujourd_hui + timedelta(days=7)
        dans_12_jours = self.aujourd_hui + timedelta(days=12)

        form = ReservationForm(data={
            'nom_client': 'Nouveau Client',
            'email_client': 'nouveau@test.com',
            'telephone_client': '+225 01 01 01 01 01',
            'date_arrivee': dans_7_jours,
            'date_depart': dans_12_jours,
            'nombre_personnes': 1,
        })
        form.unite = self.unite
        self.assertFalse(form.is_valid())
        self.assertIn("Ces dates ne sont plus disponibles", str(form.errors))

    def test_pas_chevauchement_apres_fin(self):
        """
        Une réservation qui commence après la fin d'une réservation existante
        doit être acceptée (pas de chevauchement).
        """
        dans_5_jours = self.aujourd_hui + timedelta(days=5)
        dans_10_jours = self.aujourd_hui + timedelta(days=10)
        dans_11_jours = self.aujourd_hui + timedelta(days=11)
        dans_15_jours = self.aujourd_hui + timedelta(days=15)

        Reservation.objects.create(
            unite=self.unite,
            nom_client="Client Existant",
            email_client="existant@test.com",
            telephone_client="+225 00 00 00 00 00",
            date_arrivee=dans_5_jours,
            date_depart=dans_10_jours,
            statut='confirmee',
        )

        # Réservation du 11 au 15 : ne chevauche pas
        form = ReservationForm(data={
            'nom_client': 'Nouveau Client',
            'email_client': 'nouveau@test.com',
            'telephone_client': '+225 01 01 01 01 01',
            'date_arrivee': dans_11_jours,
            'date_depart': dans_15_jours,
            'nombre_personnes': 2,
        })
        form.unite = self.unite
        self.assertTrue(form.is_valid())


class ContactFormTest(TestCase):
    """Tests du formulaire de contact."""

    def test_formulaire_contact_valide(self):
        """Un formulaire de contact complet doit être valide."""
        form = ContactForm(data={
            'nom': 'Marie Martin',
            'email': 'marie@test.com',
            'sujet': 'Question sur les tarifs',
            'message': 'Bonjour, je voudrais savoir...',
        })
        self.assertTrue(form.is_valid())

    def test_formulaire_contact_sans_sujet(self):
        """Le sujet est optionnel, le formulaire doit rester valide sans lui."""
        form = ContactForm(data={
            'nom': 'Marie Martin',
            'email': 'marie@test.com',
            'sujet': '',
            'message': 'Bonjour, je voudrais savoir...',
        })
        self.assertTrue(form.is_valid())

    def test_formulaire_contact_email_invalide(self):
        """Un email mal formaté doit rendre le formulaire invalide."""
        form = ContactForm(data={
            'nom': 'Marie Martin',
            'email': 'pas-un-email',
            'sujet': 'Test',
            'message': 'Message test',
        })
        self.assertFalse(form.is_valid())


# ===== TESTS DE LA VUE RÉSERVATION =====

class ReservationViewTest(TestCase):
    """Tests de la vue de réservation (formulaire + soumission)."""

    def setUp(self):
        self.client = Client()
        Parametres.objects.create(
            nom_residence_fr="Résidences Bereby",
            nom_residence_en="Bereby Residences",
            latitude=4.65082,
            longitude=-6.92441,
        )
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )
        self.aujourd_hui = date.today()

    def test_formulaire_reservation_accessible(self):
        """La page du formulaire de réservation doit retourner 200."""
        response = self.client.get(
            reverse('residences:reservation_form',
                    kwargs={'pk': self.unite.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_soumission_reservation_valide(self):
        """
        Une soumission valide doit créer une réservation en base
        et rediriger vers la page de confirmation.
        """
        demain = self.aujourd_hui + timedelta(days=1)
        dans_3_jours = self.aujourd_hui + timedelta(days=3)

        response = self.client.post(
            reverse('residences:reservation_form',
                    kwargs={'pk': self.unite.pk}),
            data={
                'nom_client': 'Test Client',
                'email_client': 'test@test.com',
                'telephone_client': '+225 01 02 03 04 05',
                'date_arrivee': demain,
                'date_depart': dans_3_jours,
                'nombre_personnes': 2,
                'message': '',
            }
        )
        # Doit rediriger vers la page de succès
        self.assertRedirects(
            response,
            reverse('residences:reservation_success')
        )
        # Doit avoir créé exactement 1 réservation en base
        self.assertEqual(Reservation.objects.count(), 1)
        reservation = Reservation.objects.first()
        self.assertEqual(reservation.nom_client, 'Test Client')
        self.assertEqual(reservation.statut, 'en_attente')

        # ===== TESTS DU CODE DE CONFIRMATION =====


class CodeConfirmationTest(TestCase):
    """Tests de la génération automatique du code de confirmation."""

    def setUp(self):
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )

    def test_code_genere_automatiquement(self):
        """
        Vérifie qu'un code de confirmation est généré automatiquement
        à la création d'une réservation.
        """
        reservation = Reservation.objects.create(
            unite=self.unite,
            nom_client="Test Client",
            email_client="test@test.com",
            telephone_client="+225 01 02 03 04 05",
            date_arrivee=date.today() + timedelta(days=1),
            date_depart=date.today() + timedelta(days=3),
        )
        # Le code ne doit pas être vide
        self.assertTrue(reservation.code_confirmation)
        # Le code doit commencer par "BRB-"
        self.assertTrue(reservation.code_confirmation.startswith("BRB-"))
        # Le code doit avoir le format BRB-XXXX-XXXX (12 caractères)
        self.assertEqual(len(reservation.code_confirmation), 13)

    def test_codes_uniques(self):
        """
        Vérifie que deux réservations ont des codes différents.
        """
        aujourd_hui = date.today()
        reservation1 = Reservation.objects.create(
            unite=self.unite,
            nom_client="Client 1",
            email_client="client1@test.com",
            telephone_client="+225 01 01 01 01 01",
            date_arrivee=aujourd_hui + timedelta(days=1),
            date_depart=aujourd_hui + timedelta(days=3),
        )
        reservation2 = Reservation.objects.create(
            unite=self.unite,
            nom_client="Client 2",
            email_client="client2@test.com",
            telephone_client="+225 02 02 02 02 02",
            date_arrivee=aujourd_hui + timedelta(days=5),
            date_depart=aujourd_hui + timedelta(days=8),
        )
        self.assertNotEqual(
            reservation1.code_confirmation,
            reservation2.code_confirmation
        )


# ===== TESTS DE LA PAGE DE CONSULTATION =====

class MaReservationViewTest(TestCase):
    """Tests de la page de consultation de réservation par code."""

    def setUp(self):
        self.client = Client()
        Parametres.objects.create(
            nom_residence_fr="Résidences Bereby",
            nom_residence_en="Bereby Residences",
            latitude=4.65082,
            longitude=-6.92441,
        )
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )
        # Crée une réservation avec un code connu
        self.reservation = Reservation.objects.create(
            unite=self.unite,
            nom_client="Jean Dupont",
            email_client="jean@test.com",
            telephone_client="+225 01 02 03 04 05",
            date_arrivee=date.today() + timedelta(days=1),
            date_depart=date.today() + timedelta(days=3),
        )

    def test_consultation_avec_bon_code(self):
        """
        Avec un code valide, la page doit retourner 200
        et afficher les infos de la réservation.
        """
        response = self.client.get(
            reverse('residences:ma_reservation',
                    kwargs={'code': self.reservation.code_confirmation})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jean Dupont")
        self.assertContains(response, self.reservation.code_confirmation)

    def test_consultation_avec_mauvais_code(self):
        """Un code inexistant doit retourner 404."""
        response = self.client.get(
            reverse('residences:ma_reservation',
                    kwargs={'code': 'BRB-0000-0000'})
        )
        self.assertEqual(response.status_code, 404)

    def test_consultation_insensible_casse(self):
        """
        La recherche par code doit fonctionner en minuscules aussi
        (grâce à iexact dans la vue).
        """
        code_minuscule = self.reservation.code_confirmation.lower()
        response = self.client.get(
            reverse('residences:ma_reservation',
                    kwargs={'code': code_minuscule})
        )
        self.assertEqual(response.status_code, 200)

    def test_consultation_affiche_statut(self):
        """La page doit afficher le statut de la réservation."""
        response = self.client.get(
            reverse('residences:ma_reservation',
                    kwargs={'code': self.reservation.code_confirmation})
        )
        # Le statut par défaut est 'en_attente'
        self.assertContains(response, "attente")


# ===== TESTS DE L'EMAIL DE CONFIRMATION =====

class EmailConfirmationTest(TestCase):
    """Tests de la génération et de l'envoi de l'email de confirmation."""

    def setUp(self):
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )
        self.reservation = Reservation.objects.create(
            unite=self.unite,
            nom_client="Marie Martin",
            email_client="marie@test.com",
            telephone_client="+225 05 05 05 05 05",
            date_arrivee=date.today() + timedelta(days=2),
            date_depart=date.today() + timedelta(days=5),
        )

    def test_email_envoye_apres_reservation(self):
        """
        Vérifie qu'un email est envoyé après une réservation réussie.
        Django redirige les emails vers la liste 'mail.outbox' en mode test,
        ce qui permet de vérifier leur contenu sans vrai serveur SMTP.
        """
        from django.core import mail
        from .emails import envoyer_email_confirmation

        envoyer_email_confirmation(self.reservation)

        # Un email doit avoir été "envoyé" (capturé dans outbox)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_destinataire_correct(self):
        """L'email doit être envoyé à l'adresse du client."""
        from django.core import mail
        from .emails import envoyer_email_confirmation

        envoyer_email_confirmation(self.reservation)

        self.assertEqual(mail.outbox[0].to, ["marie@test.com"])

    def test_email_contient_code(self):
        """Le sujet ou le corps de l'email doit contenir le code de confirmation."""
        from django.core import mail
        from .emails import envoyer_email_confirmation

        envoyer_email_confirmation(self.reservation)

        # Vérifie dans le corps texte brut
        self.assertIn(
            self.reservation.code_confirmation,
            mail.outbox[0].body
        )

    def test_email_sujet_correct(self):
        """Le sujet de l'email doit mentionner la résidence."""
        from django.core import mail
        from .emails import envoyer_email_confirmation

        envoyer_email_confirmation(self.reservation)

        self.assertIn("Résidences Bereby", mail.outbox[0].subject)

# ===== TESTS DU DASHBOARD ET DE L'AUTHENTIFICATION =====


class LoginViewTest(TestCase):
    """Tests de la page de login gestionnaire."""

    def setUp(self):
        self.client = Client()
        Parametres.objects.create(
            nom_residence_fr="Résidences Bereby",
            nom_residence_en="Bereby Residences",
            latitude=4.65082,
            longitude=-6.92441,
        )
        # Crée un utilisateur staff (gestionnaire)
        self.gestionnaire = User.objects.create_user(
            username='gestionnaire',
            password='motdepasse123',
            is_staff=True,
        )
        # Crée un utilisateur normal (pas staff)
        self.client_normal = User.objects.create_user(
            username='client',
            password='motdepasse123',
            is_staff=False,
        )

    def test_page_login_accessible(self):
        """La page de login doit être accessible sans être connecté."""
        response = self.client.get(reverse('residences:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'residences/login.html')

    def test_login_valide_staff(self):
        """
        Un utilisateur staff avec les bons identifiants doit être
        redirigé vers le dashboard.
        """
        response = self.client.post(reverse('residences:login'), {
            'username': 'gestionnaire',
            'password': 'motdepasse123',
        })
        self.assertRedirects(response, '/dashboard/')

    def test_login_mauvais_mot_de_passe(self):
        """
        Un mauvais mot de passe doit afficher un message d'erreur
        et rester sur la page de login.
        """
        response = self.client.post(reverse('residences:login'), {
            'username': 'gestionnaire',
            'password': 'mauvaismdp',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Identifiants incorrects")

    def test_login_utilisateur_non_staff(self):
        """
        Un utilisateur non-staff ne doit pas pouvoir accéder au dashboard,
        même avec les bons identifiants.
        """
        response = self.client.post(reverse('residences:login'), {
            'username': 'client',
            'password': 'motdepasse123',
        })
        self.assertEqual(response.status_code, 200)
        # On cherche un mot sans apostrophe pour éviter les problèmes d'encodage HTML
        self.assertContains(response, "droits")

    def test_login_redirige_si_deja_connecte(self):
        """
        Un gestionnaire déjà connecté qui visite /login/
        doit être redirigé vers le dashboard.
        """
        self.client.login(username='gestionnaire', password='motdepasse123')
        response = self.client.get(reverse('residences:login'))
        self.assertRedirects(response, '/dashboard/')


class DashboardViewTest(TestCase):
    """Tests du tableau de bord gestionnaire."""

    def setUp(self):
        self.client = Client()
        Parametres.objects.create(
            nom_residence_fr="Résidences Bereby",
            nom_residence_en="Bereby Residences",
            latitude=4.65082,
            longitude=-6.92441,
        )
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )
        # Utilisateur staff pour les tests
        self.gestionnaire = User.objects.create_user(
            username='gestionnaire',
            password='motdepasse123',
            is_staff=True,
        )

    def test_dashboard_inaccessible_sans_connexion(self):
        """
        Le dashboard doit rediriger vers /login/ si non connecté.
        """
        response = self.client.get(reverse('residences:dashboard'))
        self.assertRedirects(response, '/login/?next=/dashboard/')

    def test_dashboard_accessible_staff(self):
        """
        Un gestionnaire connecté doit pouvoir accéder au dashboard.
        """
        self.client.login(username='gestionnaire', password='motdepasse123')
        response = self.client.get(reverse('residences:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'residences/dashboard.html')

    def test_dashboard_affiche_unites(self):
        """Le dashboard doit afficher les unités disponibles."""
        self.client.login(username='gestionnaire', password='motdepasse123')
        response = self.client.get(reverse('residences:dashboard'))
        self.assertContains(response, "Studio Test")

    def test_recherche_par_nom(self):
        """
        La recherche par nom doit retourner les réservations correspondantes.
        """
        # Crée une réservation de test
        Reservation.objects.create(
            unite=self.unite,
            nom_client="Kouamé Yao",
            email_client="kouame@test.com",
            telephone_client="+225 01 02 03 04 05",
            date_arrivee=date.today() + timedelta(days=1),
            date_depart=date.today() + timedelta(days=3),
        )
        self.client.login(username='gestionnaire', password='motdepasse123')
        response = self.client.get(
            reverse('residences:dashboard') + '?q=Kouamé'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kouamé Yao")

    def test_recherche_par_telephone(self):
        """La recherche par téléphone doit aussi fonctionner."""
        Reservation.objects.create(
            unite=self.unite,
            nom_client="Awa Diallo",
            email_client="awa@test.com",
            telephone_client="+225 07 08 09 10 11",
            date_arrivee=date.today() + timedelta(days=2),
            date_depart=date.today() + timedelta(days=4),
        )
        self.client.login(username='gestionnaire', password='motdepasse123')
        response = self.client.get(
            reverse('residences:dashboard') + '?q=07 08 09'
        )
        self.assertContains(response, "Awa Diallo")

    def test_action_confirmer_reservation(self):
        """
        L'action 'confirmer' doit changer le statut de la réservation
        à 'confirmee'.
        """
        reservation = Reservation.objects.create(
            unite=self.unite,
            nom_client="Test Client",
            email_client="test@test.com",
            telephone_client="+225 01 01 01 01 01",
            date_arrivee=date.today() + timedelta(days=1),
            date_depart=date.today() + timedelta(days=3),
            statut='en_attente',
        )
        self.client.login(username='gestionnaire', password='motdepasse123')
        response = self.client.get(
            reverse('residences:dashboard_action',
                    kwargs={'reservation_id': reservation.pk, 'action': 'confirmer'})
        )
        # Doit rediriger vers le dashboard
        self.assertRedirects(response, '/dashboard/')
        # Le statut doit avoir changé
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, 'confirmee')

    def test_action_annuler_reservation(self):
        """
        L'action 'annuler' doit changer le statut de la réservation
        à 'annulee'.
        """
        reservation = Reservation.objects.create(
            unite=self.unite,
            nom_client="Test Client",
            email_client="test@test.com",
            telephone_client="+225 01 01 01 01 01",
            date_arrivee=date.today() + timedelta(days=1),
            date_depart=date.today() + timedelta(days=3),
            statut='en_attente',
        )
        self.client.login(username='gestionnaire', password='motdepasse123')
        response = self.client.get(
            reverse('residences:dashboard_action',
                    kwargs={'reservation_id': reservation.pk, 'action': 'annuler'})
        )
        self.assertRedirects(response, '/dashboard/')
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, 'annulee')
