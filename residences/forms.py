from django import forms
from .models import Reservation


class ReservationForm(forms.ModelForm):
    """
    Formulaire de pré-réservation rempli par le client sur le site.
    Basé directement sur le modèle Reservation : Django génère automatiquement
    les champs correspondants, on contrôle juste lesquels afficher et leur style.
    """

    class Meta:
        model = Reservation
        # On liste les champs du modèle qu'on veut inclure dans le formulaire.
        # On exclut volontairement 'unite' car elle sera déjà connue (via l'URL),
        # et 'statut'/'date_creation' car ils sont gérés automatiquement.
        fields = [
            'nom_client',
            'email_client',
            'telephone_client',
            'date_arrivee',
            'date_depart',
            'nombre_personnes',
            'message',
        ]

        # 'widgets' permet de personnaliser l'apparence HTML de chaque champ
        # (par défaut, Django génère des <input> très basiques sans classe CSS)
        widgets = {
            'nom_client': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre nom complet'}),
            'email_client': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'votre@email.com'}),
            'telephone_client': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+225 XX XX XX XX XX'}),
            # type='date' affiche un vrai sélecteur de date dans le navigateur
            # On utilise un champ texte (et non type='date') car le calendrier natif du navigateur
            # n'est pas personnalisable. Flatpickr (JS) viendra "habiller" ce champ texte
            # avec un vrai calendrier visuel personnalisé.
            'date_arrivee': forms.DateInput(
                attrs={'class': 'form-control datepicker',
                       'placeholder': 'Sélectionner une date', 'autocomplete': 'off'},
                format='%Y-%m-%d'
            ),
            'date_depart': forms.DateInput(
                attrs={'class': 'form-control datepicker',
                       'placeholder': 'Sélectionner une date', 'autocomplete': 'off'},
                format='%Y-%m-%d'
            ),
            'nombre_personnes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Demandes particulières (optionnel)'}),
        }

        # Labels personnalisés (texte affiché au-dessus de chaque champ)
        labels = {
            'nom_client': 'Nom complet',
            'email_client': 'Email',
            'telephone_client': 'Téléphone',
            'date_arrivee': "Date d'arrivée",
            'date_depart': 'Date de départ',
            'nombre_personnes': 'Nombre de personnes',
            'message': 'Message (optionnel)',
        }

    def clean(self):
        cleaned_data = super().clean()
        date_arrivee = cleaned_data.get('date_arrivee')
        date_depart = cleaned_data.get('date_depart')

        if date_arrivee and date_depart:
            if date_depart <= date_arrivee:
                raise forms.ValidationError(
                    "La date de départ doit être postérieure à la date d'arrivée."
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
                        "Ces dates ne sont plus disponibles pour cette unité. "
                        "Merci de choisir d'autres dates ou de nous contacter directement."
                    )

        return cleaned_data
