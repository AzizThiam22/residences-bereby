from .models import Reservation, ContactMessage, AbonnementDisponibilite
from django import forms
from .models import Reservation, ContactMessage
from django.utils.translation import gettext_lazy as _


class ReservationForm(forms.ModelForm):
    """
    Formulaire de pré-réservation rempli par le client sur le site.
    Basé directement sur le modèle Reservation : Django génère automatiquement
    les champs correspondants, on contrôle juste lesquels afficher et leur style.
    """

    # Champ "moyen de paiement" : optionnel, car le modèle a une valeur par défaut
    # ('sur_place'). S'il n'est pas choisi par le client, clean_moyen_paiement
    # le remettra à cette valeur par défaut. Le bouton radio est affiché coché
    # par défaut grâce à 'initial'.
    # Note : le label est défini ICI (et non dans Meta.labels) car Meta.labels
    # ne s'applique pas aux champs déclarés explicitement dans la classe.
    moyen_paiement = forms.ChoiceField(
        choices=Reservation.MOYEN_PAIEMENT_CHOICES,
        required=False,
        initial='sur_place',
        label=_('Moyen de paiement souhaité'),
        widget=forms.RadioSelect(attrs={'class': 'radio-option'}),
    )

    # Champ "moyen de communication" : idem, optionnel avec défaut 'email'
    moyen_communication = forms.ChoiceField(
        choices=Reservation.MOYEN_COMMUNICATION_CHOICES,
        required=False,
        initial='email',
        label=_('Comment pouvons-nous vous contacter ?'),
        widget=forms.RadioSelect(attrs={'class': 'radio-option'}),
    )

    class Meta:
        model = Reservation
        # On liste les champs du modèle qu'on veut inclure dans le formulaire.
        # On exclut volontairement 'unite' car elle sera déjà connue (via l'URL),
        # et 'statut'/'date_creation' car ils sont gérés automatiquement.
        fields = [
            'nom_client',
            'email_client',
            'telephone_client',
            'indicatif_regional',
            'moyen_communication',
            'date_arrivee',
            'date_depart',
            'nombre_personnes',
            'moyen_paiement',
            'preuve_paiement',
            'message',
        ]

        # 'widgets' permet de personnaliser l'apparence HTML de chaque champ
        # (par défaut, Django génère des <input> très basiques sans classe CSS)
        widgets = {
            'nom_client': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Votre nom complet')}),
            'email_client': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('votre@email.com')}),
            'telephone_client': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('XX XX XX XX XX')}),
            # Indicatif régional séparé du numéro, pour que le gestionnaire
            # puisse facilement appeler les clients internationaux.
            'indicatif_regional': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': '+225'}),
            # Boutons radio pour le moyen de contact préféré
            'moyen_communication': forms.RadioSelect(attrs={'class': 'radio-option'}),
            # type='date' affiche un vrai sélecteur de date dans le navigateur
            # On utilise un champ texte (et non type='date') car le calendrier natif du navigateur
            # n'est pas personnalisable. Flatpickr (JS) viendra "habiller" ce champ texte
            # avec un vrai calendrier visuel personnalisé.
            'date_arrivee': forms.DateInput(
                attrs={'class': 'form-control datepicker',
                       'placeholder': _('Sélectionner une date'), 'autocomplete': 'off'},
                format='%Y-%m-%d'
            ),
            'date_depart': forms.DateInput(
                attrs={'class': 'form-control datepicker',
                       'placeholder': _('Sélectionner une date'), 'autocomplete': 'off'},
                format='%Y-%m-%d'
            ),
            'nombre_personnes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            # Boutons radio pour le moyen de paiement : le JS affichera
            # les instructions (preuve Mobile Money, avertissement frais carte) selon le choix
            'moyen_paiement': forms.RadioSelect(attrs={'class': 'radio-option'}),
            'preuve_paiement': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('Demandes particulières (optionnel)')}),
        }

        # Labels personnalisés (texte affiché au-dessus de chaque champ)
        labels = {
            'nom_client': _('Nom complet'),
            'email_client': _('Email'),
            'telephone_client': _('Téléphone'),
            'indicatif_regional': _('Indicatif régional'),
            'moyen_communication': _('Comment pouvons-nous vous contacter ?'),
            'date_arrivee': _('Date d\'arrivée'),
            'date_depart': _('Date de départ'),
            'nombre_personnes': _('Nombre de personnes'),
            'moyen_paiement': _('Moyen de paiement souhaité'),
            'preuve_paiement': _('Preuve de paiement (photo/capture)'),
            'message': _('Message (optionnel)'),
        }

    def clean_moyen_paiement(self):
        # Si aucun choix n'a été soumis (champ optionnel), on applique
        # la valeur par défaut du modèle ('sur_place') plutôt qu'une chaîne vide.
        valeur = self.cleaned_data.get('moyen_paiement')
        return valeur or 'sur_place'

    def clean_moyen_communication(self):
        # Idem pour le moyen de communication : défaut 'email'
        valeur = self.cleaned_data.get('moyen_communication')
        return valeur or 'email'

    def clean(self):
        cleaned_data = super().clean()
        date_arrivee = cleaned_data.get('date_arrivee')
        date_depart = cleaned_data.get('date_depart')

        if date_arrivee and date_depart:
            if date_depart <= date_arrivee:
                raise forms.ValidationError(
                    _("La date de départ doit être postérieure à la date d'arrivée.")
                )

            # Vérifie qu'aucune réservation existante (en attente ou confirmée) pour
            # cette même unité ne chevauche les dates demandées.
            # self.unite est défini dans la vue avant validation (voir views.py ci-dessous)
            if hasattr(self, 'unite') and self.unite:
                conflits = Reservation.objects.filter(
                    unite=self.unite,
                    statut__in=['en_attente', 'confirmee'],
                ).filter(
                    # Logique de chevauchement de dates : deux périodes se chevauchent si
                    # la nouvelle arrivée est avant l'ancien départ ET la nouvelle date de
                    # départ est après l'ancienne arrivée.
                    date_arrivee__lt=date_depart,
                    date_depart__gt=date_arrivee,
                )

                if conflits.exists():
                    raise forms.ValidationError(
                        _("Ces dates ne sont plus disponibles pour cette unité. "
                          "Merci de choisir d'autres dates ou de nous contacter directement.")
                    )

        return cleaned_data


class ContactForm(forms.ModelForm):
    """
    Formulaire de contact général : pas lié à une unité spécifique,
    pour toute question ou demande d'information.
    """

    class Meta:
        model = ContactMessage
        fields = ['nom', 'email', 'sujet', 'message']

        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Votre nom complet')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('votre@email.com')
            }),
            'sujet': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Objet de votre message (optionnel)')
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Votre message...')
            }),
        }

        labels = {
            'nom': _('Nom complet'),
            'email': _('Email'),
            'sujet': _('Sujet'),
            'message': _('Message'),
        }


class AbonnementDisponibiliteForm(forms.ModelForm):
    """
    Formulaire permettant à un client de s'abonner aux notifications
    de disponibilité d'une unité, sans avoir de compte.
    """
    class Meta:
        model = AbonnementDisponibilite
        fields = ['nom', 'email']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Votre nom (optionnel)')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('votre@email.com')
            }),
        }
        labels = {
            'nom': _('Nom'),
            'email': _('Email'),
        }
