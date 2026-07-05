# Résidences Bereby

Site web pour la gestion et la réservation de logements meublés des **Résidences Bereby**, situées sur le littoral de Grand-Béréby, Côte d'Ivoire.

## À propos

Résidence de 6 unités locatives réparties sur 3 étages, plus un local commercial au sous-sol :

| Niveau | Unités |
|---|---|
| Sous-sol | 1 local commercial (location séparée) |
| 1er étage | 1 studio (vue arrière) + 1 studio (vue mer) |
| 2e étage | 1 studio (vue arrière) + 1 studio (vue mer) |
| 3e étage | 2 appartements (vue mer) |

## Fonctionnalités prévues

- [x] Présentation des unités avec galerie photo
- [x] Carte de localisation (Leaflet/OpenStreetMap) avec distances vers les villes clés
- [x] Formulaire de pré-réservation
- [x] Paiement en ligne (passerelle Mobile Money + carte) et/ou clic direct vers numéros Mobile Money
- [x] Site bilingue Français / Anglais
- [] Formulaire de contact + liens réseaux sociaux

## Stack technique

- **Backend** : Python / Django
- **Base de données** : SQLite (développement) → PostgreSQL (production, à venir)
- **Carte** : Leaflet + OpenStreetMap
- **Frontend** : Templates Django (HTML/CSS, possible évolution selon besoins)

## Installation locale

1. Cloner le répertoire :
```sh
git clone https://github.com/votre-nom-utilisateur/residences-bereby.git
cd residences-bereby
```

2. Créer et activer un environnement virtuel :
```sh
python -m venv .venv
.venv\Scripts\Activate.ps1
```

3. Installer les dépendances :
```sh
pip install -r requirements.txt
```

4. Lancer les migrations :
```sh
python manage.py migrate
```

5. Démarrer le serveur de développement :
```sh
python manage.py runserver

```

## Statut du projet

🚧 **En cours de développement** — Maquette/prototype en attendant la finalisation des résidences (livraison estimée : ~1 an).

## Note du développement
Donner des noms aux unités afin d'apporter une touche aux résidences et facilité l'organisation des images sur le site web.
Ajouter aussi des tests unitaires si possible


## Auteur

Aziz THIAM