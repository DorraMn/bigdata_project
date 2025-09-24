# 📊 Plateforme de gestion de clusters Big Data – Projet de stage TalentHub

Bienvenue sur ce dépôt GitHub, qui présente le projet développé dans le cadre de mon stage de perfectionnement chez **TalentHub**, réalisé sur une période de 2 mois.

## 🎯 Objectif du projet

Développer une **plateforme centralisée et automatisée** permettant de :

- Créer et gérer des **clusters Big Data**
- Installer et désinstaller dynamiquement des outils tels que :  
  **Apache Spark**, **HBase**, **MongoDB**
- Visualiser en temps réel l’état et les performances des nœuds
- Modifier dynamiquement les configurations internes des outils
- Assurer un déploiement simplifié grâce à **Docker**

---

## 🧰 Technologies utilisées

### ⚙️ Backend
- [FastAPI](https://fastapi.tiangolo.com/) – API rapide et moderne avec Python
- Scripts Python pour l’automatisation de déploiement et de configuration

### 🎨 Frontend
- HTML / CSS / JavaScript – Interface utilisateur simple et responsive

### 🐳 Conteneurisation
- **Docker** – Pour l’isolation et la portabilité des services Big Data
- Docker CLI utilisé dans le backend pour orchestrer les conteneurs

### 🔧 Big Data Tools
- **Apache Spark** – Traitement distribué en mémoire
- **HBase** – Stockage NoSQL distribué
- **MongoDB** – Base orientée documents

---

## 🚀 Fonctionnalités principales

- 🧩 Création de clusters en précisant les rôles (Master / Slave)
- 📦 Installation / désinstallation automatisée via Docker
- ⚙️ Modification des fichiers de configuration (YAML, JSON, etc.)
- 📊 Tableau de bord pour la supervision des nœuds
- 🔄 Redéploiement intelligent des services en cas de mise à jour

---

## 🧪 Lancement du projet (Exemple)

```bash
# 1. Cloner le dépôt
git clone https://github.com/ton-utilisateur/nom-du-depot.git
cd nom-du-depot

# 2. Lancer l’API FastAPI via Docker ou localement
docker build -t cluster-platform .
docker run -p 8000:8000 cluster-platform
