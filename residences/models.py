from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
import uuid


class Unite(models.Model):
    """
    Représente une unité locative de la résidence : un studio, un appartement,
    ou le local commercial du sous-sol.
    """

    # Liste des choix possibles pour le type d'unité.
    # Format : (valeur stockée en base de données, texte affiché dans l'admin/formulaires)
    TYPE_CHOICES = [
        ('studio', _('Studio')),
        ('appartement', _('Appartement')),
        ('local_commercial', _('Local commercial')),
    ]

    # Pareil pour l'étage : on stocke un chiffre (0,1,2,3) mais on affiche un texte clair
    ETAGE_CHOICES = [
        (0, _('Sous-sol')),
        (1, _('1er étage')),
        (2, _('2e étage')),
        (3, _('3e étage')),
    ]

    # CharField = texte court (max_length obligatoire)
    nom = models.CharField(max_length=100, help_text="Ex: Studio Vue Mer 1")

    # On utilise les choix définis plus haut ; valeur par défaut = 'studio'
    type_unite = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='studio')

    # IntegerField avec choices : stocke un entier, mais admin affichera le texte correspondant
    etage = models.IntegerField(choices=ETAGE_CHOICES)

    # BooleanField = case Oui/Non. Ici : est-ce que l'unité a vue sur la mer ?
    vue_mer = models.BooleanField(default=False)

    # DecimalField = nombre décimal précis (mieux que FloatField pour des mesures/prix)
    # null=True : peut être vide en base de données
    # blank=True : peut être laissé vide dans les formulaires/admin
    surface_m2 = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True)

    # PositiveIntegerField = entier positif uniquement (pas de nombre négatif de personnes)
    capacite_personnes = models.PositiveIntegerField(default=2)

    # TextField = texte long, sans limite de caractères (contrairement à CharField)
    # blank=True = champ optionnel
    # anciennement, on avait deux champs séparés pour la description en français et en anglais.
    # Avec django-modeltranslation, on va utiliser un seul champ "description" et modeltranslation
    # Un seul champ 'description' : modeltranslation créera automatiquement
    # 'description_fr' et 'description_en' en base de données
    description = models.TextField(blank=True)

    # Prix par nuit. validators=[MinValueValidator(0)] empêche un prix négatif
    prix_nuit = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    # Permet de masquer temporairement une unité du site sans la supprimer
    disponible = models.BooleanField(default=True)

    # auto_now_add : rempli automatiquement à la création, jamais modifié après
    date_creation = models.DateTimeField(auto_now_add=True)
    # auto_now : mis à jour automatiquement à chaque sauvegarde
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        # Ordre d'affichage par défaut : d'abord par étage, puis par nom
        ordering = ['etage', 'nom']
        # Nom affiché dans l'admin Django (singulier / pluriel)
        verbose_name = "Unité"
        verbose_name_plural = "Unités"

    def __str__(self):
        # Définit comment l'objet s'affiche en texte (ex: dans l'admin, dans le shell Django)
        # get_etage_display() est une méthode automatique de Django qui retourne
        # le texte du choix plutôt que le chiffre brut (ex: "1er étage" au lieu de "1")
        return f"{self.nom} ({self.get_etage_display()})"


class Photo(models.Model):
    """
    Une photo associée à une unité. Une unité peut avoir plusieurs photos.
    """

    # ForeignKey = relation "plusieurs photos pour une unité" (relation many-to-one)
    # related_name='photos' permet de faire unite.photos.all() pour récupérer toutes les photos
    # on_delete=models.CASCADE : si l'unité est supprimée, ses photos le sont aussi
    unite = models.ForeignKey(
        Unite, on_delete=models.CASCADE, related_name='photos')

    # ImageField stocke le fichier image ; upload_to définit le sous-dossier dans /media/
    image = models.ImageField(upload_to='unites/')

    # Légende optionnelle affichée sous la photo
    legende = models.CharField(max_length=200, blank=True)

    # Permet de marquer une photo comme "photo principale" (affichée en premier sur la liste)
    principale = models.BooleanField(
        default=False, help_text="Photo affichée en premier")

    # Permet de définir manuellement l'ordre d'affichage des photos
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordre']
        verbose_name = "Photo"
        verbose_name_plural = "Photos"

    def __str__(self):
        return f"Photo de {self.unite.nom}"


class Equipement(models.Model):
    """
    Un équipement/aménité (Wi-Fi, climatisation, etc.) pouvant être associé
    à plusieurs unités à la fois.
    """

    nom_fr = models.CharField(max_length=100)
    nom_en = models.CharField(max_length=100)

    # Nom d'icône à utiliser côté template (ex: "wifi", "tv", "ac") — facultatif
    icone = models.CharField(max_length=50, blank=True,
                             help_text="Nom d'icône (ex: wifi, tv, ac)")

    # ManyToManyField : un équipement peut appartenir à plusieurs unités,
    # et une unité peut avoir plusieurs équipements (relation many-to-many)
    unites = models.ManyToManyField(
        Unite, related_name='equipements', blank=True)

    class Meta:
        verbose_name = "Équipement"
        verbose_name_plural = "Équipements"

    def __str__(self):
        return self.nom_fr


class Reservation(models.Model):
    """
    Une demande de réservation soumise via le formulaire du site.
    Au départ, ce sera une simple "pré-réservation" en attente de confirmation manuelle.
    """

    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('annulee', 'Annulée'),
    ]

    # Quelle unité est concernée par cette réservation
    unite = models.ForeignKey(
        Unite, on_delete=models.CASCADE, related_name='reservations')

    # Informations du client (pas de compte utilisateur requis pour réserver, pour simplifier)
    nom_client = models.CharField(max_length=150)
    # EmailField valide automatiquement le format email
    email_client = models.EmailField()
    telephone_client = models.CharField(max_length=30)

    # DateField = uniquement une date, sans heure
    date_arrivee = models.DateField()
    date_depart = models.DateField()

    nombre_personnes = models.PositiveIntegerField(default=1)

    # Statut de la réservation, modifiable depuis l'admin (vous validez manuellement)
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='en_attente')

    # Message libre du client (demandes particulières, questions, etc.)
    message = models.TextField(blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        # '-date_creation' = ordre décroissant (les plus récentes en premier)
        ordering = ['-date_creation']
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"

    def __str__(self):
        return f"{self.nom_client} - {self.unite.nom} ({self.date_arrivee} au {self.date_depart})"

    # Code unique généré automatiquement à la création de la réservation.
    # Permet au client de consulter sa réservation sans avoir de compte.
    # uuid4() génère un identifiant aléatoire universel (très peu probable d'avoir deux fois le même)
    code_confirmation = models.CharField(
        max_length=20,
        unique=True,
        blank=True,  # sera rempli automatiquement dans save()
        help_text="Code unique envoyé au client pour consulter sa réservation"
    )

    def save(self, *args, **kwargs):
        """
        Génère automatiquement un code de confirmation à la première sauvegarde
        (quand l'objet est créé, pas lors des modifications suivantes).
        Format : BRB-XXXX-XXXX (lisible et court)
        """
        if not self.code_confirmation:
            # Prend les 8 premiers caractères d'un UUID, en majuscules
            code = uuid.uuid4().hex[:8].upper()
            self.code_confirmation = f"BRB-{code[:4]}-{code[4:]}"
        super().save(*args, **kwargs)


class ContactMessage(models.Model):
    """
    Message envoyé via le formulaire de contact du site (pas forcément lié à une réservation).
    """

    nom = models.CharField(max_length=150)
    email = models.EmailField()
    sujet = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)

    # Permet de cocher dans l'admin une fois que vous avez répondu/traité le message
    traite = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date_envoi']
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"

    def __str__(self):
        return f"{self.nom} - {self.sujet or 'Sans sujet'}"


class Parametres(models.Model):
    """
    Modèle "singleton" : il ne doit exister qu'UN SEUL enregistrement de ce type.
    Sert à stocker les informations générales du site (coordonnées, réseaux sociaux,
    numéros Mobile Money) modifiables facilement depuis l'admin, sans toucher au code.
    """

    nom_residence = models.CharField(
        max_length=150, default="Résidences Bereby")

    # Coordonnées GPS pour la carte Leaflet/OpenStreetMap
    # Valeurs par défaut approximatives pour Grand-Béréby (à ajuster avec les vraies coordonnées)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, default=4.7833)
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, default=-7.0500)
    adresse = models.CharField(max_length=255, blank=True)

    # Coordonnées de contact générales
    telephone_principal = models.CharField(max_length=30, blank=True)

    # Numéros Mobile Money pour le paiement "clic direct" (sans passerelle)
    numero_orange_money = models.CharField(max_length=30, blank=True)
    numero_mtn_money = models.CharField(max_length=30, blank=True)
    numero_wave = models.CharField(max_length=30, blank=True)

    email_contact = models.EmailField(blank=True)

    # URLField valide automatiquement que le texte saisi est bien une URL
    lien_facebook = models.URLField(blank=True)
    lien_instagram = models.URLField(blank=True)
    lien_whatsapp = models.URLField(blank=True)

    class Meta:
        verbose_name = "Paramètres du site"
        verbose_name_plural = "Paramètres du site"

    def __str__(self):
        return self.nom_residence

    def save(self, *args, **kwargs):
        # Astuce pour forcer un seul enregistrement : on fixe toujours pk=1.
        # Donc même si on essaie de créer un 2e enregistrement, il écrasera le 1er
        # au lieu d'en créer un nouveau.
        self.pk = 1
        super().save(*args, **kwargs)


class VilleCle(models.Model):
    """
    Une ville clé à afficher sur la carte de localisation, avec sa distance
    et son temps de trajet approximatif depuis la résidence.
    On stocke la distance manuellement (plutôt que de la calculer automatiquement)
    car la distance routière réelle diffère souvent de la distance "à vol d'oiseau".
    """

    nom = models.CharField(max_length=100)

    # Coordonnées GPS de la ville, utilisées pour placer un marqueur sur la carte
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    # Distance routière approximative en kilomètres (saisie manuellement, plus fiable
    # qu'un calcul automatique "à vol d'oiseau" qui ignore les routes réelles)
    distance_km = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True)

    # Temps de trajet approximatif, en texte libre pour rester flexible (ex: "1h30", "45 min")
    temps_trajet = models.CharField(max_length=50, blank=True)

    # Permet de choisir l'ordre d'affichage dans la liste (ex: villes les plus proches en premier)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'distance_km']
        verbose_name = "Ville clé"
        verbose_name_plural = "Villes clés"

    def __str__(self):
        return self.nom
