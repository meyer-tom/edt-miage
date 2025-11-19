# 📅 ADE Calendar Scraper - UT Capitole

Script Python automatisé pour scraper votre emploi du temps depuis ADE (UT Capitole) et le convertir en format iCal (.ics) compatible avec Apple Calendar.

## 🚀 Fonctionnalités

- ✅ Scraping automatique via Selenium (supporte JavaScript)
- ✅ Authentification SSO CAS
- ✅ Export au format iCal (.ics)
- ✅ Gestion automatique des timezones (Europe/Paris → UTC)
- ✅ Mise à jour quotidienne automatique via GitHub Actions
- ✅ URL publique pour abonnement dans Apple Calendar

## 📦 Installation locale

```bash
# Cloner le repo
git clone https://github.com/VOTRE_USERNAME/EDT.git
cd EDT

# Installer les dépendances
pip install -r requirements.txt

# Exécuter le scraper
python ade_scraper.py
```

Le script vous demandera vos identifiants SSO si les variables d'environnement ne sont pas configurées.

## ⚙️ Configuration GitHub Actions (automatisation)

### 1. Créer un nouveau repository sur GitHub

```bash
# Dans le dossier EDT
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/VOTRE_USERNAME/EDT.git
git push -u origin main
```

### 2. Configurer les secrets GitHub

1. Allez sur votre repo GitHub : `https://github.com/VOTRE_USERNAME/EDT`
2. Cliquez sur **Settings** > **Secrets and variables** > **Actions**
3. Cliquez sur **New repository secret** et ajoutez :

   - **Nom** : `SSO_USERNAME`
     **Valeur** : Votre identifiant SSO UT Capitole

   - **Nom** : `SSO_PASSWORD`
     **Valeur** : Votre mot de passe SSO UT Capitole

### 3. Activer GitHub Pages

1. Allez dans **Settings** > **Pages**
2. Sous **Source**, sélectionnez **Deploy from a branch**
3. Sélectionnez la branche **gh-pages** et le dossier **/ (root)**
4. Cliquez sur **Save**

### 4. Lancer le workflow manuellement (première fois)

1. Allez dans l'onglet **Actions**
2. Cliquez sur **Update Calendar** dans la liste des workflows
3. Cliquez sur **Run workflow** > **Run workflow**
4. Attendez que le workflow se termine (environ 1-2 minutes)

### 5. Récupérer l'URL de votre calendrier

Votre calendrier sera disponible à l'URL suivante :

```
https://VOTRE_USERNAME.github.io/EDT/emploi_du_temps.ics
```

## 📱 S'abonner au calendrier dans Apple Calendar

### Sur Mac :

1. Ouvrir **Calendar**
2. Menu **Fichier** > **Nouvel abonnement au calendrier...**
3. Coller l'URL : `https://VOTRE_USERNAME.github.io/EDT/emploi_du_temps.ics`
4. Cliquer sur **S'abonner**
5. Configurer :
   - **Nom** : EDT UT Capitole
   - **Couleur** : à votre choix
   - **Fréquence de rafraîchissement** : Tous les jours (recommandé)
6. Cliquer sur **OK**

### Sur iPhone/iPad :

1. Ouvrir **Réglages**
2. **Calendrier** > **Comptes** > **Ajouter un compte**
3. **Autre** > **Ajouter un abonnement**
4. Coller l'URL : `https://VOTRE_USERNAME.github.io/EDT/emploi_du_temps.ics`
5. **Suivant** > **Enregistrer**

## 🕐 Fréquence de mise à jour

Le workflow GitHub Actions s'exécute automatiquement **tous les jours à 6h du matin** (heure de Paris).

Apple Calendar synchronisera automatiquement les modifications selon la fréquence configurée (par défaut : toutes les heures ou tous les jours).

## 🔧 Structure du projet

```
EDT/
├── .github/
│   └── workflows/
│       └── update-calendar.yml   # Workflow GitHub Actions
├── ade_scraper.py                 # Script principal de scraping
├── ade_public_scraper.py          # Script pour calendrier public
├── requirements.txt               # Dépendances Python
├── .gitignore                     # Fichiers à ignorer
└── README.md                      # Ce fichier
```

## 📝 Variables d'environnement

Le script supporte les variables d'environnement suivantes :

- `SSO_USERNAME` : Identifiant SSO UT Capitole
- `SSO_PASSWORD` : Mot de passe SSO UT Capitole

Si ces variables ne sont pas définies, le script demandera les identifiants interactivement.

## 🛠️ Dépannage

### Le workflow échoue ?

1. Vérifiez que les secrets `SSO_USERNAME` et `SSO_PASSWORD` sont bien configurés
2. Vérifiez dans l'onglet **Actions** les logs d'erreur
3. Assurez-vous que GitHub Pages est activé sur la branche `gh-pages`

### Le calendrier ne se synchronise pas ?

1. Vérifiez que l'URL du calendrier est correcte
2. Testez l'URL dans votre navigateur (elle doit télécharger un fichier .ics)
3. Dans Apple Calendar, faites un clic droit sur le calendrier > **Actualiser**

### Changer l'heure d'exécution ?

Modifiez le fichier `.github/workflows/update-calendar.yml` ligne 6 :

```yaml
- cron: '0 5 * * *'  # 5h UTC = 6h Paris (hiver) / 7h Paris (été)
```

Format : `minute heure jour mois jour_semaine` (en UTC)

## 📄 Licence

Ce projet est open-source et libre d'utilisation.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

---

**Note** : Ce projet n'est pas affilié à l'Université Toulouse 1 Capitole. Il s'agit d'un outil personnel pour faciliter la gestion de l'emploi du temps.
