# AI Fitness Counter - Application Complète de Décompte d'Exercices par Vision par Ordinateur

Application développée conformément au **Dossier de Conception UML (Niveau 4 - Expertise en architecture des développements logiciels)** :
- **Frontend** : Vue 3 JS (Composition API, Web Audio API, Speech Synthesis, Canvas 2D, MediaPipe Pose 33 points clés).
- **Backend** : Python 3 (FastAPI, SQLite relationnel avec contraintes CASCADE, modèle de domaine orienté objet strict).

---

## 1. Respect Strict des 4 Diagrammes UML

### A. Diagramme de Cas d'Utilisation (Figure 1, Sections 2.4 & 2.5)
- **Acteur Visiteur** :
  - `Consulter le catalogue d'exercices`
  - `S'inscrire` (création de compte)
  - `S'authentifier`
- **Acteur Sportif** (hérite de Visiteur) :
  - `Réaliser une séance de décompte` :
    - `<<include>> Choisir un exercice`
    - `<<include>> Activer la caméra`
    - `<<include>> Détecter la posture et compter les répétitions`
    - `<<include>> Afficher le récapitulatif de la séance`
    - `<<extend>> Recevoir une correction de posture` (émis visuellement et vocalement si l'angle sort de la tolérance)
    - `<<extend>> Mettre en pause ou reprendre`
    - `<<extend>> Notifier l'atteinte de l'objectif` (déclenché lors de la complétion)
  - `Définir un objectif` (quotidien, hebdomadaire, mensuel)
  - `Consulter l'historique des séances`
    - `<<extend>> Partager un résultat` (carte récapitulative et texte partageable)
  - `Consulter la progression` (jauge et pourcentage d'accomplissement)
- **Acteur Administrateur** :
  - `Gérer le catalogue d'exercices` (ajout, modification, suppression)
  - `<<extend>> Paramétrer les règles de comptage` (angles haut/bas, articulation clé, tolérance, durée min)
  - `Gérer les utilisateurs`
  - `Consulter les statistiques globales` (KPIs plateforme, exercices populaires, taux de réussite)
- **Acteur Secondaire (Système externe)** :
  - `Service de notification` : envoie de notifications push lors de la validation d'un objectif.

---

### B. Diagramme de Classes (Figures 2 & 3, Sections 3.4 & 3.7)
Implémenté dans `backend/domain/` et persisté dans `backend/database/` :

1. **Classes d'Exécution & Métier (Domain Model)** :
   - `Utilisateur` (abstraite) -> factorise nom, prénom, email, motDePasse, dateInscription.
   - `Sportif` (hérite de Utilisateur) -> poids, taille, niveau, `lancerSeance()`, `definirObjectif()`.
   - `Administrateur` (hérite de Utilisateur) -> niveauAcces, `gererCatalogue()`, `parametrerRegles()`.
   - `Exercice` -> `idExercice`, nom, description, groupeMusculaire, difficulte, `getDetails()`, `getRegle()`.
   - `RegleDeComptage` (Composition 1-1 avec Exercice) -> `articulationCle`, `angleHaut`, `angleBas`, `tolerance`, `dureeMinRepetition`, `evaluerPhase()`, `estRepetitionValide()`.
   - `Posture` (Composition 1-33 avec PointCle) -> `horodatage`, `confiance`, `getAngle(a, b, c)` avec formule vectorielle :
     $$\theta = \arccos\left(\frac{\vec{BA} \cdot \vec{BC}}{|\vec{BA}| \times |\vec{BC}|}\right)$$
   - `PointCle` -> nom, x, y, z, visibilité, `distanceVers(p)`.
   - `IEstimateurPose` & `EstimateurMediaPipe` -> Inversion des dépendances (DIP) et motif Stratégie.
   - `CompteurRepetitions` (Machine à états) -> `total`, `phaseCourante`, `derniereTransition`, `traiter(p)`, `incrementer()`, `reinitialiser()`.
   - `MoteurVision` -> `resolutionCamera`, `imagesParSeconde`, `seuilConfiance`, `initialiser(r)`, `analyserImage()`, `traiterPosture()`.
   - `SeanceEntrainement` -> `idSeance`, `dateDebut`, `dureeSecondes`, `statut`, `totalRepetitions`, `calculerCalories()`.
   - `Repetition` (Composition 1-* avec Séance) -> `numero`, `horodatage`, `dureeMs`, `amplitude`, `estCorrecte`.
   - `RetourCorrection` (Composition 1-* avec Séance) -> `idRetour`, `message`, `type`, `gravite`.
   - `Objectif` -> `repetitionsCible`, `periode`, `dateLimite`, `atteint`, `verifierAtteinte()`, `calculerProgression()`.
   - `Notification` -> `message`, `dateEnvoi`, `canal`, `envoyer()`.

---

### C. Diagramme de Séquence (Figures 4, 5, 6)
- **Phase 1 : Choix de l'exercice et initialisation**
  - Application -> `GET /api/exercices/{id}` -> SELECT -> renvoie exercice + règle de comptage.
  - Application affiche la consigne.
  - Sportif clique sur démarrer -> `demanderAutorisationCamera()`.
  - Branche `[autorisation accordée]` : `initialiser(regle)`, `POST /api/seances` -> INSERT en base -> `201 Created` + `idSeance`.
  - Vue caméra affichée.
- **Phase 2 : Boucle d'analyse et de comptage (~30 images/s)**
  - Caméra envoie la trame -> `analyserImage(frame)` (MediaPipe 33 points).
  - Si personne non détectée -> signal "Placez-vous dans le cadre".
  - Si posture détectée -> `traiterPosture(posture)` calcule les angles.
  - Si répétition complète (cycle haut-bas-haut avec hystérésis et durée min) -> `incrementer()`, mise à jour du compteur + signal sonore.
  - Si angle hors tolérance -> `signalerCorrection(message)` (conseil visuel et vocal).
- **Phase 3 : Pause, fin de séance et enregistrement**
  - `[pause]` -> `suspendre()` / `reprendre()`.
  - Fin de séance -> `PUT /api/seances/{id}` avec durée, total et répétitions -> UPDATE en base.
  - `verifierAtteinte(total)` exécuté sur l'objectif -> si atteint, notification créée via le service externe.
  - `200 OK` + Récapitulatif affiché au sportif.

---

### D. Diagramme d'Activité (Figure 7)
Structure en **4 couloirs (Sportif, Application, Moteur de vision, Serveur)** :
- Fork parallèle (Application active caméra & Serveur charge la règle) puis Join.
- Boucle d'analyse fermée avec décisions : Personne détectée ? Posture correcte ? Répétition complète ? Séance terminée ? Objectif atteint ?
- Clôture vers Récapitulatif et partage du résultat.

---

## 2. Lancement Rapide

### Option 1 : En 1 Clic sous Windows
Double-cliquez sur :
```bat
start.bat
```
Ce script initialise la base de données, lance le serveur et ouvre automatiquement votre navigateur sur `http://localhost:8000`.

### Option 2 : En Ligne de Commande
```powershell
python run_server.py
```
Puis ouvrez `http://localhost:8000` dans votre navigateur.

---

## 3. Fonctionnalités Implémentées & Ajouts Spécifiques

1. **Double Source Vidéo (Webcam & Échantillons du Projet)** :
   - Fonctionne avec la webcam en temps réel.
   - Permet également d'exécuter l'analyse sur les vidéos du projet (`squat.mp4`, `pushup.mp4`, `dumbbell workout.mp4`, `chest fly machine.mp4`) pour tester sans webcam !
2. **Audio Web API & Synthèse Vocale IA** :
   - Carillon sonore à chaque répétition validée.
   - Retour vocal automatique prononcé en français lors des erreurs de posture ("Descendez plus bas !", "Attention à l'hyperflexion").
3. **Bascule Rapide de Rôles pour Soutenance/Démo** :
   - Boutons en haut à droite permettant de basculer instantanément entre **Sportif**, **Administrateur** et **Visiteur**.
4. **Calcul Réaliste de Dépense Calorique** :
   - Basé sur le poids de l'athlète, le MET de l'exercice et la durée.
5. **Carte de Partage sur Réseaux Sociaux** :
   - Génération d'une carte de score et copie dans le presse-papier.
6. **Tests Unitaires Automatisés (9/9 Validés)** :
   - `python backend/tests/test_domain_and_api.py` valide le modèle mathématique vectoriel et la machine à états.
