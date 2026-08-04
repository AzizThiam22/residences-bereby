# AGENTS.md

Instructions permanentes pour les agents travaillant sur ce projet
(Django — site de réservation « Résidences Bereby », Grand-Béréby, Côte d'Ivoire).

## Commits automatiques
- À la **fin de chaque tâche** (implémentation, correction, refactor), effectuer
  automatiquement un commit **atomique** :
  1. Lancer les vérifications : `.venv\Scripts\python.exe manage.py check` puis
     `.venv\Scripts\python.exe manage.py test residences`.
  2. Inspecter `git status` et `git diff` pour ne voir que les fichiers concernés.
  3. `git add` **uniquement** les fichiers relatifs à la tâche.
  4. `git commit` avec un message clair et descriptif.
  5. Annoncer à l'utilisateur le commit effectué et son message.
- Ne **jamais** pousser (`git push`) sans demande explicite de l'utilisateur.
- Ne pas commiter de fichiers de debug, fichiers médias de test, ou données sensibles.

## Conventions de code
- **Commenter tout le code en français**, avec des docstrings pour chaque fonction.
- Code lisible et simple, commentaires explicatifs (niveau pédagogique).

## Environnement
- Shell : PowerShell 7 (`pwsh`). OS : Windows.
- Environnement virtuel : `.venv\Scripts\python.exe` (ex. `.venv\Scripts\python.exe manage.py runserver`).
- Tests : `.venv\Scripts\python.exe manage.py test residences`.
- Base de données dev : SQLite. `DEBUG=True` en dev.
- Site bilingue FR/EN : traduction UI via Django i18n (`makemessages -l en` /
  `compilemessages`) ; contenus via django-modeltranslation.
- En dev, les emails sont affichés dans la console (EMAIL_BACKEND=console).
- Confirmation de réservation : TOUJOURS manuelle (décision métier).
