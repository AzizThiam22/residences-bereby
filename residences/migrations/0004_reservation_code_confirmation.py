import uuid
from django.db import migrations, models


def generer_codes_existants(apps, schema_editor):
    """
    Fonction de migration de données : génère un code unique pour chaque
    réservation existante avant d'appliquer la contrainte UNIQUE.
    Sans ça, toutes les lignes existantes auraient une valeur vide
    et la contrainte d'unicité échouerait.
    """
    Reservation = apps.get_model('residences', 'Reservation')
    for reservation in Reservation.objects.all():
        code = uuid.uuid4().hex[:8].upper()
        reservation.code_confirmation = f"BRB-{code[:4]}-{code[4:]}"
        reservation.save()


class Migration(migrations.Migration):

    dependencies = [
        # Référence à la migration précédente (gardez le nom exact de votre fichier)
        ('residences', '0003_equipement_nom_fr_en_equipement_nom_fr_fr_and_more'),
    ]

    operations = [
        # Étape 1 : ajoute le champ SANS la contrainte unique et avec une valeur par défaut
        migrations.AddField(
            model_name='reservation',
            name='code_confirmation',
            field=models.CharField(
                max_length=20,
                blank=True,
                default='',  # valeur temporaire pour les lignes existantes
            ),
        ),
        # Étape 2 : génère des codes uniques pour toutes les réservations existantes
        migrations.RunPython(generer_codes_existants,
                             migrations.RunPython.noop),
        # Étape 3 : maintenant que toutes les lignes ont un code unique,
        # on peut appliquer la contrainte UNIQUE en toute sécurité
        migrations.AlterField(
            model_name='reservation',
            name='code_confirmation',
            field=models.CharField(
                max_length=20,
                unique=True,
                blank=True,
                help_text="Code unique envoyé au client pour consulter sa réservation",
            ),
        ),
    ]
