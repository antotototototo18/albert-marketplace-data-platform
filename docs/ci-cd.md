# Intégration continue et déploiement

## CI disponible dès maintenant

Le workflow [CI](../.github/workflows/ci.yml) tourne sur chaque pull request vers
`main`, à chaque push sur `main` et à la demande depuis l'onglet Actions.
Le contrôle affiché dans les pull requests s'appelle **Repository checks**.

Il vérifie :

- la syntaxe YAML et la cohérence des workflows GitHub Actions avec actionlint ;
- les marqueurs de conflits et les collisions de noms entre systèmes ;
- les fichiers de plus de 1 Mio, à conserver hors du dépôt ;
- les signatures de clés privées reconnues par `detect-private-key` ;
- les fins de fichiers et les espaces superflus ;
- l'absence de fichiers suivis par Git alors qu'ils sont couverts par `.gitignore`.

Ces contrôles ne remplacent pas une revue des secrets : ils ne détectent pas
tous les mots de passe ou jetons API. La CI actuelle n'exécute pas de tests
applicatifs : le dépôt ne contient pas encore de pipelines ou de modèles dbt.

Les actions et les hooks sont fixés à des commits précis. Le workflow dispose
uniquement d'un accès en lecture au dépôt et n'utilise aucun secret cloud.
Les exécutions devenues obsolètes sur une même branche ou PR sont annulées.

Avant de fusionner une PR, obtenir une approbation d'un autre membre et vérifier
que **Repository checks** est vert. À la mise en place, GitHub refuse la
protection de branche pour ce dépôt privé avec l'offre actuelle (HTTP 403).
Cette règle reste donc une convention d'équipe. Si l'offre évolue, protéger
`main` avec une approbation obligatoire et ce contrôle requis.

## Reproduire les contrôles en local

Avec Python 3.10 ou plus récent et Go 1.25 ou plus récent installés :

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pre-commit run --all-files --show-diff-on-failure
git ls-files --cached --ignored --exclude-standard
```

Sous Windows, activer l'environnement avec `.venv\Scripts\Activate.ps1` dans
PowerShell. La dernière commande doit produire une sortie vide. Les hooks
peuvent corriger la mise en forme : relire les changements et relancer les
contrôles après correction. Pour les lancer avant chaque commit :

```sh
pre-commit install
```

## Évolution avec le cours

| Contenu ajouté | Contrôles à ajouter dans la CI |
|---|---|
| Ingestion Python (L03) | Lint et tests unitaires avec jeux de données synthétiques |
| Modèles dbt (L05) | Compilation puis tests dans un dataset GCP de développement |
| Images Docker (L06) | Construction et tests des images |
| DAG Airflow (L07) | Import des DAG et validation de leur structure |
| Terraform (L08) | Format, validation et plan sur les pull requests |

## CD à raccorder à GCP

Aucun déploiement n'est configuré à ce stade : le code à déployer, le projet
GCP et les ressources cibles ne sont pas encore définis dans ce dépôt.

Quand ces éléments seront disponibles, ajouter un workflow distinct qui :

1. Valide et construit le commit fusionné dans `main`.
2. S'authentifie auprès de GCP avec OpenID Connect et Workload Identity
   Federation, sans clé de service permanente dans GitHub.
3. Publie une image portant le SHA du commit dans Artifact Registry.
4. Déploie cette image dans l'environnement de développement choisi par le groupe.
5. Vérifie le déploiement et permet de revenir à l'image précédente.

Le plan Terraform se fait en revue de code ; l'application des changements et
le passage en production font l'objet d'une validation explicite. Les rôles IAM
et les autorisations OIDC devront être limités à ce dépôt et à la branche ou
à l'environnement de déploiement concerné.

## Mettre à jour les outils

Mettre à jour `requirements-dev.txt`, les SHA des actions et ceux des hooks dans
une pull request dédiée, en indiquant la version correspondante en commentaire.
Exécuter les contrôles localement puis vérifier leur réussite sur GitHub avant
fusion. Aucune automatisation ne crée de commits ou de PR au nom d'un bot.

Références : [pre-commit](https://pre-commit.com/),
[actionlint](https://github.com/rhysd/actionlint) et
[sécurisation des workflows GitHub Actions](https://docs.github.com/en/actions/reference/security/secure-use).
