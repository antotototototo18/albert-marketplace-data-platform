# Contribuer au projet

## Première installation

1. Accepter l'invitation GitHub au dépôt privé.
2. Cloner le projet :

   ```sh
   git clone https://github.com/antotototototo18/albert-marketplace-data-platform.git
   cd albert-marketplace-data-platform
   ```

3. Vérifier son identité Git avant son premier commit :

   ```sh
   git config user.name
   git config user.email
   ```

   Chaque membre utilise son propre nom et une adresse associée à son compte
   GitHub, ou son adresse GitHub privée indiquée dans ses paramètres de compte.

4. Copier `.env.example` vers `.env` lorsque les exercices nécessitent les
   paramètres cloud. Le projet GCP sera fourni par l'équipe enseignante.

## Pour chaque contribution

```sh
git switch main
git pull --ff-only origin main
git switch -c prenom/description-courte
```

Faire des commits courts et explicites, puis publier sa branche :

```sh
git add chemin/du/fichier
git commit -m "Document the source data flows"
git push -u origin prenom/description-courte
```

Ouvrir une pull request vers `main`, expliquer le changement et sa vérification,
puis demander une relecture à un autre membre. Fusionner après son approbation
et supprimer la branche distante terminée. Ne pas pousser directement sur `main`.

## Organisation

- Créer une issue avec le modèle **Task** pour chaque tâche et indiquer le responsable.
- Relier la pull request à l'issue concernée, par exemple avec `Closes #12`.
- Actualiser `docs/architecture.md` si l'architecture change.
- Documenter les décisions dans `docs/adr/` : chaque membre rédige au moins un ADR.
- Ne jamais committer de secrets, fichiers `.env`, clés de service ou données locales.
- Conserver les attributions et les restrictions d'utilisation du modèle du cours.
- Vérifier ensemble les pull requests de l'équipe enseignante avant de les fusionner.

## Vérifications automatiques

Chaque pull request vers `main` déclenche le contrôle **Repository checks**.
Attendre sa réussite et la relecture d'un autre membre avant de fusionner.
Les commandes pour reproduire les contrôles en local et les étapes prévues
pour le déploiement sont décrites dans [docs/ci-cd.md](docs/ci-cd.md).

## Modèle du cours

Le dépôt d'origine est
[`TangoAI-AlbertSchool-Data-Eng-Cloud/de-platform-template`](https://github.com/TangoAI-AlbertSchool-Data-Eng-Cloud/de-platform-template).
Le clone utilisé pour préparer le groupe le conserve sous le remote `upstream`.
Les nouveaux clones ont uniquement le remote `origin` ; pour ajouter le modèle :

```sh
git remote add upstream https://github.com/TangoAI-AlbertSchool-Data-Eng-Cloud/de-platform-template.git
```
