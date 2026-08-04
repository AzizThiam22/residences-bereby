from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
import base64
from .models import Unite, Parametres, Reservation, VilleCle
from .forms import ReservationForm, ContactForm
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from io import StringIO

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

    def test_formulaire_valide_avec_paiement_carte(self):
        """
        Un formulaire avec le moyen de paiement "carte" et un moyen de
        communication WhatsApp doit être accepté.
        """
        form = ReservationForm(data={
            'nom_client': 'Jean Dupont',
            'email_client': 'jean@test.com',
            'telephone_client': '01 02 03 04 05',
            'indicatif_regional': '+225',
            'moyen_communication': 'whatsapp',
            'moyen_paiement': 'carte',
            'date_arrivee': self.demain,
            'date_depart': self.dans_3_jours,
            'nombre_personnes': 2,
        })
        form.unite = self.unite
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['moyen_paiement'], 'carte')
        self.assertEqual(form.cleaned_data['moyen_communication'], 'whatsapp')
        self.assertEqual(form.cleaned_data['indicatif_regional'], '+225')

    def test_formulaire_valide_avec_mobile_money_et_preuve(self):
        """
        Un formulaire avec Mobile Money et une capture d'écran (fichier)
        doit être accepté. Le fichier est un vrai PNG 1x1 encodé en base64.
        """
        # Petit PNG 1x1 valide (l'ImageField vérifie que c'est une vraie image)
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        preuve = SimpleUploadedFile(
            "preuve.png", png_bytes, content_type="image/png")

        form = ReservationForm(
            data={
                'nom_client': 'Jean Dupont',
                'email_client': 'jean@test.com',
                'telephone_client': '01 02 03 04 05',
                'indicatif_regional': '+225',
                'moyen_communication': 'appel',
                'moyen_paiement': 'mobile_money',
                'date_arrivee': self.demain,
                'date_depart': self.dans_3_jours,
                'nombre_personnes': 2,
            },
            files={'preuve_paiement': preuve}
        )
        form.unite = self.unite
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['moyen_paiement'], 'mobile_money')
        self.assertIsNotNone(form.cleaned_data['preuve_paiement'])

    def test_moyen_paiement_par_defaut(self):
        """
        Sans choix explicite, le moyen de paiement par défaut doit être
        'sur_place' et le moyen de communication par défaut 'email'.
        """
        form = ReservationForm(data={
            'nom_client': 'Jean Dupont',
            'email_client': 'jean@test.com',
            'telephone_client': '01 02 03 04 05',
            'date_arrivee': self.demain,
            'date_depart': self.dans_3_jours,
            'nombre_personnes': 2,
        })
        form.unite = self.unite
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['moyen_paiement'], 'sur_place')
        self.assertEqual(form.cleaned_data['moyen_communication'], 'email')

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

    def test_soumission_avec_moyen_paiement(self):
        """
        Une soumission avec un moyen de paiement, un indicatif régional
        et un moyen de communication doit les enregistrer en base.
        """
        demain = self.aujourd_hui + timedelta(days=1)
        dans_3_jours = self.aujourd_hui + timedelta(days=3)

        response = self.client.post(
            reverse('residences:reservation_form',
                    kwargs={'pk': self.unite.pk}),
            data={
                'nom_client': 'Awa Diallo',
                'email_client': 'awa@test.com',
                'telephone_client': '07 08 09 10 11',
                'indicatif_regional': '+225',
                'moyen_communication': 'whatsapp',
                'moyen_paiement': 'carte',
                'date_arrivee': demain,
                'date_depart': dans_3_jours,
                'nombre_personnes': 2,
                'message': '',
            }
        )
        # Comme le moyen de paiement est la carte, la soumission redirige
        # vers la page de paiement en ligne (et non la page de confirmation)
        reservation = Reservation.objects.get(email_client='awa@test.com')
        self.assertRedirects(
            response,
            reverse('residences:paiement',
                    args=[reservation.code_confirmation])
        )
        self.assertEqual(reservation.moyen_paiement, 'carte')
        self.assertEqual(reservation.moyen_communication, 'whatsapp')
        self.assertEqual(reservation.indicatif_regional, '+225')

    def test_soumission_mobile_money_avec_preuve(self):
        """
        Une soumission Mobile Money avec capture d'écran doit enregistrer
        la preuve de paiement en base.
        """
        demain = self.aujourd_hui + timedelta(days=1)
        dans_3_jours = self.aujourd_hui + timedelta(days=3)

        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        preuve = SimpleUploadedFile(
            "preuve.png", png_bytes, content_type="image/png")

        response = self.client.post(
            reverse('residences:reservation_form',
                    kwargs={'pk': self.unite.pk}),
            data={
                'nom_client': 'Kouamé Yao',
                'email_client': 'kouame@test.com',
                'telephone_client': '01 02 03 04 05',
                'indicatif_regional': '+225',
                'moyen_communication': 'email',
                'moyen_paiement': 'mobile_money',
                'date_arrivee': demain,
                'date_depart': dans_3_jours,
                'nombre_personnes': 1,
                'message': '',
                # Le fichier se transmet DANS data, pas dans un kwarg séparé
                'preuve_paiement': preuve,
            }
        )
        self.assertRedirects(
            response,
            reverse('residences:reservation_success')
        )
        reservation = Reservation.objects.get(email_client='kouame@test.com')
        self.assertEqual(reservation.moyen_paiement, 'mobile_money')
        self.assertTrue(reservation.preuve_paiement)

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

    def test_email_contient_moyen_paiement(self):
        """
        L'email de confirmation doit mentionner le moyen de paiement choisi.
        """
        from django.core import mail
        from .emails import envoyer_email_confirmation

        # On choisit un moyen de paiement explicite
        self.reservation.moyen_paiement = 'mobile_money'
        self.reservation.save()

        envoyer_email_confirmation(self.reservation)

        # Le corps de l'email doit contenir le libellé du moyen de paiement
        self.assertIn("Mobile Money", mail.outbox[0].body)

    def test_email_bilingue(self):
        """
        L'email de confirmation doit être bilingue : version française,
        un séparateur 'English version will follow', puis la version anglaise,
        dans cet ordre.
        """
        from django.core import mail
        from .emails import envoyer_email_confirmation

        envoyer_email_confirmation(self.reservation)

        body = mail.outbox[0].body

        # La version française est présente
        self.assertIn("Bonjour", body)
        self.assertIn("Votre demande de réservation", body)
        # Le séparateur annonce la version anglaise
        self.assertIn("English version will follow", body)
        # La version anglaise est présente
        self.assertIn("Your booking request", body)

        # Vérifie l'ordre : français → séparateur → anglais
        self.assertLess(
            body.index("Votre demande de réservation"),
            body.index("English version will follow"),
        )
        self.assertLess(
            body.index("English version will follow"),
            body.index("Your booking request"),
        )

    def test_email_html_bilingue(self):
        """
        Le HTML de l'email contient les deux versions, le séparateur,
        et les valeurs traduites dans la bonne langue (nom d'unité FR et EN).
        """
        from django.core import mail
        from .emails import envoyer_email_confirmation

        envoyer_email_confirmation(self.reservation)

        # mail.outbox[0].alternatives contient (contenu, 'text/html')
        html = mail.outbox[0].alternatives[0][0]

        self.assertIn("Bonjour", html)
        self.assertIn("English version will follow", html)
        self.assertIn("Hello", html)

        # Le nom de l'unité apparaît dans les deux langues :
        # version française et version anglaise du récapitulatif
        self.assertIn("Studio Test", html)
        self.assertIn("Test Studio", html)

# ===== TESTS DE L'EXPORT iCal (SYNCHRONISATION AIRBNB) =====


class IcalExportTest(TestCase):
    """Tests de l'export iCal d'une unité (blocage des dates sur Airbnb)."""

    def setUp(self):
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )
        self.url_ical = reverse(
            'residences:calendrier_ical', args=[self.unite.pk])

    def _creer_reservation(self, statut):
        """Helper : crée une réservation avec le statut demandé."""
        return Reservation.objects.create(
            unite=self.unite,
            nom_client="Test Client",
            email_client="test@test.com",
            telephone_client="+225 01 01 01 01 01",
            date_arrivee=date.today() + timedelta(days=2),
            date_depart=date.today() + timedelta(days=5),
            statut=statut,
        )

    def test_ical_accessible_sans_connexion(self):
        """
        Le fichier iCal doit être public : Airbnb doit pouvoir le lire
        sans être connecté au site.
        """
        response = self.client.get(self.url_ical)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/calendar; charset=utf-8')

    def test_ical_contient_headers(self):
        """Le fichier doit contenir les en-têtes VCALENDAR requis."""
        response = self.client.get(self.url_ical)
        self.assertContains(response, 'BEGIN:VCALENDAR')
        self.assertContains(response, 'VERSION:2.0')
        self.assertContains(response, 'END:VCALENDAR')

    def test_ical_contient_reservation_confirmee(self):
        """Une réservation confirmée doit bloquer ses dates dans le iCal."""
        reservation = self._creer_reservation('confirmee')
        response = self.client.get(self.url_ical)
        arrivee = reservation.date_arrivee.strftime('%Y%m%d')
        depart = reservation.date_depart.strftime('%Y%m%d')
        self.assertContains(response, f'DTSTART;VALUE=DATE:{arrivee}')
        self.assertContains(response, f'DTEND;VALUE=DATE:{depart}')

    def test_ical_inclut_reservation_en_attente(self):
        """Une réservation en attente doit aussi bloquer ses dates."""
        reservation = self._creer_reservation('en_attente')
        response = self.client.get(self.url_ical)
        arrivee = reservation.date_arrivee.strftime('%Y%m%d')
        self.assertContains(response, f'DTSTART;VALUE=DATE:{arrivee}')

    def test_ical_exclut_reservation_annulee(self):
        """Une réservation annulée ne doit pas apparaître dans le iCal."""
        reservation = self._creer_reservation('annulee')
        response = self.client.get(self.url_ical)
        arrivee = reservation.date_arrivee.strftime('%Y%m%d')
        self.assertNotContains(response, f'DTSTART;VALUE=DATE:{arrivee}')

    def test_ical_unite_inexistante_404(self):
        """Un fichier iCal pour une unité inconnue doit retourner 404."""
        response = self.client.get(
            reverse('residences:calendrier_ical', args=[99999]))
        self.assertEqual(response.status_code, 404)

# ===== TESTS DU SOCLE DE PAIEMENT CINETPAY =====


class CinetPayTest(TestCase):
    """
    Tests du socle d'intégration CinetPay (paiement en ligne par carte).
    CinetPay n'est pas encore configuré (pas de compte) : les appels API
    sont simulés avec unittest.mock.
    """

    def setUp(self):
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
        self.reservation = Reservation.objects.create(
            unite=self.unite,
            nom_client="Marie Martin",
            email_client="marie@test.com",
            telephone_client="+225 05 05 05 05 05",
            date_arrivee=date.today() + timedelta(days=2),
            date_depart=date.today() + timedelta(days=5),  # 3 nuits
        )

    def test_montant_total(self):
        """Le montant total = nombre de nuits × prix par nuit."""
        # 3 nuits × 30000 FCFA = 90000
        self.assertEqual(self.reservation.montant_total, 90000)

    def test_paiement_statut_defaut(self):
        """Par défaut, le statut de paiement d'une réservation est 'non_paye'."""
        self.assertEqual(self.reservation.paiement_statut, 'non_paye')

    def test_creer_paiement_sans_configuration(self):
        """Sans identifiants CinetPay, creer_paiement doit lever une exception."""
        from .cinetpay import creer_paiement, CinetPayNonConfigure
        with self.assertRaises(CinetPayNonConfigure):
            creer_paiement(self.reservation)

    def test_page_paiement_sans_configuration(self):
        """
        Sans CinetPay configuré, la page de paiement affiche un message
        explicatif (et n'envoie pas l'utilisateur ailleurs).
        """
        response = self.client.get(
            reverse('residences:paiement',
                    args=[self.reservation.code_confirmation]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CinetPay")

    def test_page_paiement_retour_accessible(self):
        """La page de retour après paiement doit être accessible."""
        response = self.client.get(
            reverse('residences:paiement_retour',
                    args=[self.reservation.code_confirmation]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'residences/paiement_retour.html')

    def test_reservation_carte_redirige_vers_paiement(self):
        """
        Une réservation payée par carte doit rediriger vers la page de
        paiement en ligne (route 'residences:paiement').
        """
        from unittest.mock import patch

        with patch('residences.views.creer_paiement'):
            response = self.client.post(
                reverse('residences:reservation_form', args=[self.unite.pk]),
                {
                    'nom_client': 'Test Client',
                    'email_client': 'test@test.com',
                    'telephone_client': '+225 01 01 01 01 01',
                    'date_arrivee': (date.today() + timedelta(days=10)).strftime('%Y-%m-%d'),
                    'date_depart': (date.today() + timedelta(days=13)).strftime('%Y-%m-%d'),
                    'nombre_personnes': '2',
                    'moyen_paiement': 'carte',
                },
            )

        # La réservation a bien été créée
        reservation = Reservation.objects.get(email_client='test@test.com')
        self.assertEqual(reservation.moyen_paiement, 'carte')

        # La réponse redirige vers la page de paiement de cette réservation
        self.assertRedirects(
            response,
            reverse('residences:paiement',
                    args=[reservation.code_confirmation]),
            fetch_redirect_response=False,
        )

    def test_paiement_redirige_vers_cinetpay(self):
        """
        La vue 'paiement' appelle l'API CinetPay et redirige vers l'URL
        de paiement renvoyée par la passerelle.
        """
        from unittest.mock import patch

        url_cinetpay = 'https://paiement.cinetpay.com/checkout/123'
        with patch('residences.views.creer_paiement',
                   return_value=url_cinetpay):
            response = self.client.get(
                reverse('residences:paiement',
                        args=[self.reservation.code_confirmation]))

        self.assertRedirects(
            response, url_cinetpay, fetch_redirect_response=False)

    def test_notification_paiement_accepte(self):
        """
        Le webhook CinetPay doit marquer le paiement comme effectué
        quand la vérification renvoie ACCEPTED.
        """
        from unittest.mock import patch

        url = reverse('residences:paiement_notification',
                      args=[self.reservation.code_confirmation])
        with patch('residences.views.verifier_paiement',
                   return_value=('ACCEPTED', 'CPM-TRANS-123')):
            response = self.client.post(url, data={})

        self.assertEqual(response.status_code, 200)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.paiement_statut, 'effectue')
        self.assertEqual(self.reservation.paiement_reference, 'CPM-TRANS-123')
        self.assertIsNotNone(self.reservation.date_paiement)

    def test_notification_paiement_refuse(self):
        """Le webhook doit marquer le paiement comme refusé si REFUSED."""
        from unittest.mock import patch

        url = reverse('residences:paiement_notification',
                      args=[self.reservation.code_confirmation])
        with patch('residences.views.verifier_paiement',
                   return_value=('REFUSED', 'CPM-TRANS-123')):
            response = self.client.post(url, data={})

        self.assertEqual(response.status_code, 200)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.paiement_statut, 'refuse')

    def test_notification_ignore_methode_get(self):
        """Le webhook doit refuser les requêtes autres que POST."""
        url = reverse('residences:paiement_notification',
                      args=[self.reservation.code_confirmation])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

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

    def test_login_gerant(self):
        """
        Un utilisateur non-staff (gérant) avec les bons identifiants doit
        être redirigé vers la page d'activités (et non le dashboard).
        """
        response = self.client.post(reverse('residences:login'), {
            'username': 'client',
            'password': 'motdepasse123',
        })
        self.assertRedirects(response, '/activites/')

    def test_login_redirige_si_deja_connecte(self):
        """
        Un gestionnaire déjà connecté qui visite /login/
        doit être redirigé vers le dashboard.
        """
        self.client.login(username='gestionnaire', password='motdepasse123')
        response = self.client.get(reverse('residences:login'))
        self.assertRedirects(response, '/dashboard/')

    def test_login_redirige_gerant_deja_connecte(self):
        """
        Un gérant déjà connecté qui visite /login/
        doit être redirigé vers la page d'activités.
        """
        self.client.login(username='client', password='motdepasse123')
        response = self.client.get(reverse('residences:login'))
        self.assertRedirects(response, '/activites/')


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

    def test_dashboard_inaccessible_gerant(self):
        """
        Un gérant (non-staff) connecté qui visite le dashboard doit être
        redirigé vers sa page d'activités.
        """
        # Crée un utilisateur gérant (compte simple, non-staff)
        User.objects.create_user(
            username='gerant', password='motdepasse123', is_staff=False
        )
        self.client.login(username='gerant', password='motdepasse123')
        response = self.client.get(reverse('residences:dashboard'))
        self.assertRedirects(response, '/activites/')

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


class ActivitesViewTest(TestCase):
    """Tests de la page d'activités du gérant (lecture seule)."""

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
        # Un gérant : compte simple, non-staff
        self.gerant = User.objects.create_user(
            username='gerant', password='motdepasse123', is_staff=False,
        )
        # Un gestionnaire : compte staff
        self.gestionnaire = User.objects.create_user(
            username='gestionnaire', password='motdepasse123', is_staff=True,
        )

    def test_activites_inaccessibles_sans_connexion(self):
        """La page d'activités doit rediriger vers /login/ si non connecté."""
        response = self.client.get(reverse('residences:activites'))
        self.assertRedirects(response, '/login/?next=/activites/')

    def test_activites_accessible_gerant(self):
        """Un gérant connecté doit pouvoir accéder à la page d'activités."""
        self.client.login(username='gerant', password='motdepasse123')
        response = self.client.get(reverse('residences:activites'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'residences/activites.html')

    def test_activites_affiche_unites(self):
        """La page d'activités doit afficher les unités disponibles."""
        self.client.login(username='gerant', password='motdepasse123')
        response = self.client.get(reverse('residences:activites'))
        self.assertContains(response, "Studio Test")

    def test_activites_staff_redirige_dashboard(self):
        """
        Un membre du staff qui visite la page d'activités doit être
        redirigé vers le dashboard.
        """
        self.client.login(username='gestionnaire', password='motdepasse123')
        response = self.client.get(reverse('residences:activites'))
        self.assertRedirects(response, '/dashboard/')

    def test_activites_lecture_seule(self):
        """
        La page d'activités ne doit contenir aucun bouton d'action
        (confirmation / annulation) : c'est une vue en lecture seule.
        """
        Reservation.objects.create(
            unite=self.unite,
            nom_client="Test Client",
            email_client="test@test.com",
            telephone_client="+225 01 01 01 01 01",
            date_arrivee=date.today() + timedelta(days=1),
            date_depart=date.today() + timedelta(days=3),
            statut='en_attente',
        )
        self.client.login(username='gerant', password='motdepasse123')
        response = self.client.get(reverse('residences:activites'))
        self.assertNotContains(response, 'dashboard_action')

    def test_gerant_ne_peut_pas_confirmer(self):
        """
        Un gérant ne doit pas pouvoir confirmer une réservation :
        l'action est refusée et le statut reste inchangé.
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
        self.client.login(username='gerant', password='motdepasse123')
        response = self.client.get(
            reverse('residences:dashboard_action',
                    kwargs={'reservation_id': reservation.pk, 'action': 'confirmer'})
        )
        self.assertRedirects(response, '/activites/')
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, 'en_attente')

# ===== TESTS DES ABONNEMENTS DE DISPONIBILITÉ =====


class AbonnementDisponibiliteModelTest(TestCase):
    """Tests du modèle AbonnementDisponibilite."""

    def setUp(self):
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )

    def test_creation_abonnement(self):
        """Vérifie qu'un abonnement est bien créé."""
        from .models import AbonnementDisponibilite
        abonnement = AbonnementDisponibilite.objects.create(
            unite=self.unite,
            email="client@test.com",
            nom="Jean Dupont",
        )
        self.assertEqual(abonnement.email, "client@test.com")
        self.assertTrue(abonnement.actif)
        self.assertEqual(
            str(abonnement), f"client@test.com → {self.unite.nom}")

    def test_unicite_email_par_unite(self):
        """
        Un même email ne peut pas s'abonner deux fois à la même unité.
        La contrainte unique_together doit lever une IntegrityError.
        """
        from .models import AbonnementDisponibilite
        from django.db import IntegrityError

        AbonnementDisponibilite.objects.create(
            unite=self.unite,
            email="client@test.com",
        )
        with self.assertRaises(IntegrityError):
            AbonnementDisponibilite.objects.create(
                unite=self.unite,
                email="client@test.com",
            )

    def test_meme_email_differentes_unites(self):
        """
        Le même email peut s'abonner à des unités différentes.
        """
        from .models import AbonnementDisponibilite

        unite2 = Unite.objects.create(
            nom_fr="Studio 2", nom_en="Studio 2",
            type_unite="studio", etage=2, vue_mer=True,
            prix_nuit=38000, disponible=True,
        )
        AbonnementDisponibilite.objects.create(
            unite=self.unite, email="client@test.com"
        )
        AbonnementDisponibilite.objects.create(
            unite=unite2, email="client@test.com"
        )
        from .models import AbonnementDisponibilite as A
        self.assertEqual(A.objects.filter(email="client@test.com").count(), 2)


class AbonnementViewTest(TestCase):
    """Tests des vues d'abonnement aux notifications de disponibilité."""

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

    def test_page_abonnement_accessible(self):
        """La page d'abonnement doit retourner 200."""
        response = self.client.get(
            reverse('residences:abonnement_disponibilite',
                    kwargs={'pk': self.unite.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'residences/abonnement_disponibilite.html'
        )

    def test_soumission_abonnement_valide(self):
        """
        Une soumission valide doit créer un abonnement et rediriger
        vers la page de confirmation.
        """
        from .models import AbonnementDisponibilite

        response = self.client.post(
            reverse('residences:abonnement_disponibilite',
                    kwargs={'pk': self.unite.pk}),
            data={
                'nom': 'Marie Martin',
                'email': 'marie@test.com',
            }
        )
        # Doit rediriger vers la page de confirmation
        self.assertRedirects(
            response,
            reverse('residences:abonnement_success',
                    kwargs={'pk': self.unite.pk})
        )
        # Doit avoir créé un abonnement en base
        self.assertEqual(AbonnementDisponibilite.objects.count(), 1)
        abonnement = AbonnementDisponibilite.objects.first()
        self.assertEqual(abonnement.email, 'marie@test.com')
        self.assertEqual(abonnement.unite, self.unite)
        self.assertTrue(abonnement.actif)

    def test_soumission_doublon_redirige_quand_meme(self):
        """
        Si un email est déjà abonné à cette unité, la soumission
        doit quand même rediriger vers la confirmation (pas d'erreur visible).
        """
        from .models import AbonnementDisponibilite

        # Crée un abonnement existant
        AbonnementDisponibilite.objects.create(
            unite=self.unite,
            email="marie@test.com",
        )
        # Soumet à nouveau le même email
        response = self.client.post(
            reverse('residences:abonnement_disponibilite',
                    kwargs={'pk': self.unite.pk}),
            data={'nom': 'Marie Martin', 'email': 'marie@test.com'}
        )
        # Doit quand même rediriger proprement
        self.assertRedirects(
            response,
            reverse('residences:abonnement_success',
                    kwargs={'pk': self.unite.pk})
        )
        # Toujours un seul abonnement (pas de doublon)
        self.assertEqual(AbonnementDisponibilite.objects.count(), 1)

    def test_page_confirmation_accessible(self):
        """La page de confirmation d'abonnement doit retourner 200."""
        response = self.client.get(
            reverse('residences:abonnement_success',
                    kwargs={'pk': self.unite.pk})
        )
        self.assertEqual(response.status_code, 200)


class NotificationsDisponibiliteTest(TestCase):
    """Tests de l'envoi des emails de notification de disponibilité."""

    def setUp(self):
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )

    def test_notification_envoyee_aux_abonnes(self):
        """
        L'envoi de notifications doit envoyer un email
        à chaque abonné actif de l'unité.
        """
        from django.core import mail
        from .models import AbonnementDisponibilite
        from .emails import envoyer_notifications_disponibilite

        # Crée 2 abonnements actifs
        AbonnementDisponibilite.objects.create(
            unite=self.unite, email="client1@test.com", actif=True
        )
        AbonnementDisponibilite.objects.create(
            unite=self.unite, email="client2@test.com", actif=True
        )

        nb = envoyer_notifications_disponibilite(
            self.unite, raison='annulation')

        # 2 emails doivent avoir été envoyés
        self.assertEqual(nb, 2)
        self.assertEqual(len(mail.outbox), 2)

    def test_abonnement_desactive_apres_notification(self):
        """
        Après l'envoi d'une notification, l'abonnement doit être désactivé
        pour éviter de notifier plusieurs fois le même client.
        """
        from django.core import mail
        from .models import AbonnementDisponibilite
        from .emails import envoyer_notifications_disponibilite

        abonnement = AbonnementDisponibilite.objects.create(
            unite=self.unite, email="client@test.com", actif=True
        )

        envoyer_notifications_disponibilite(self.unite, raison='annulation')

        # Recharge depuis la base de données
        abonnement.refresh_from_db()
        self.assertFalse(abonnement.actif)

    def test_pas_notification_si_aucun_abonne(self):
        """
        Si personne n'est abonné, aucun email ne doit être envoyé.
        """
        from django.core import mail
        from .emails import envoyer_notifications_disponibilite

        nb = envoyer_notifications_disponibilite(
            self.unite, raison='annulation')

        self.assertEqual(nb, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_abonnement_inactif_non_notifie(self):
        """
        Les abonnements inactifs (actif=False) ne doivent pas recevoir
        de notification.
        """
        from django.core import mail
        from .models import AbonnementDisponibilite
        from .emails import envoyer_notifications_disponibilite

        # Crée un abonnement inactif
        AbonnementDisponibilite.objects.create(
            unite=self.unite,
            email="client@test.com",
            actif=False  # inactif
        )

        nb = envoyer_notifications_disponibilite(
            self.unite, raison='annulation')

        self.assertEqual(nb, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_notification_lors_annulation_dashboard(self):
        """
        Quand une réservation est annulée depuis le dashboard,
        les abonnés de cette unité doivent être notifiés.
        """
        from django.core import mail
        from django.contrib.auth.models import User
        from .models import AbonnementDisponibilite

        # Crée le gestionnaire et les données nécessaires
        Parametres.objects.create(
            nom_residence_fr="Résidences Bereby",
            nom_residence_en="Bereby Residences",
            latitude=4.65082, longitude=-6.92441,
        )
        gestionnaire = User.objects.create_user(
            username='gestionnaire', password='mdp123', is_staff=True
        )
        reservation = Reservation.objects.create(
            unite=self.unite,
            nom_client="Client Test",
            email_client="client@test.com",
            telephone_client="+225 01 01 01 01 01",
            date_arrivee=date.today() + timedelta(days=1),
            date_depart=date.today() + timedelta(days=3),
            statut='en_attente',
        )
        # Crée un abonnement actif
        AbonnementDisponibilite.objects.create(
            unite=self.unite, email="abonne@test.com", actif=True
        )

        # Connecte le gestionnaire et annule la réservation
        self.client.login(username='gestionnaire', password='mdp123')
        self.client.get(
            reverse('residences:dashboard_action',
                    kwargs={'reservation_id': reservation.pk, 'action': 'annuler'})
        )

        # Vérifie que le statut a changé
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, 'annulee')

        # Au moins un email de notification doit avoir été envoyé
        self.assertGreater(len(mail.outbox), 0)
        destinataires = [email.to[0] for email in mail.outbox]
        self.assertIn("abonne@test.com", destinataires)


class CommandeVerifierDepartsTest(TestCase):
    """Tests de la commande management verifier_departs."""

    def setUp(self):
        self.unite = Unite.objects.create(
            nom_fr="Studio Test", nom_en="Test Studio",
            type_unite="studio", etage=1, vue_mer=False,
            prix_nuit=30000, disponible=True,
        )
        Parametres.objects.create(
            nom_residence_fr="Résidences Bereby",
            nom_residence_en="Bereby Residences",
            latitude=4.65082, longitude=-6.92441,
        )

    def test_commande_sans_departs(self):
        """
        Si aucune réservation n'est terminée, la commande
        doit s'exécuter sans erreur et sans envoyer d'email.
        """
        from django.core import mail
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        # call_command exécute la commande Django comme si on la tapait en terminal
        call_command('verifier_departs', stdout=out)

        self.assertIn("Aucun départ", out.getvalue())
        self.assertEqual(len(mail.outbox), 0)

    def test_commande_avec_depart_termine(self):
        """
        Une réservation confirmée dont la date de départ est passée
        doit déclencher une notification aux abonnés.
        """
        from django.core import mail
        from django.core.management import call_command
        from .models import AbonnementDisponibilite
        from io import StringIO

        # Crée une réservation terminée (départ hier)
        Reservation.objects.create(
            unite=self.unite,
            nom_client="Client Parti",
            email_client="parti@test.com",
            telephone_client="+225 00 00 00 00 00",
            date_arrivee=date.today() - timedelta(days=5),
            date_depart=date.today() - timedelta(days=1),  # parti hier
            statut='confirmee',
        )
        # Crée un abonné
        AbonnementDisponibilite.objects.create(
            unite=self.unite,
            email="abonne@test.com",
            actif=True,
        )

        out = StringIO()
        call_command('verifier_departs', stdout=out)

        # Un email doit avoir été envoyé
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["abonne@test.com"])
