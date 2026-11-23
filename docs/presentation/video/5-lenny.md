# Partie 6 — Lenny · Terraform et la suite · 6:00 → 7:30

**Ton rôle :** montrer que le cloud correspond exactement au code, puis fermer
la vidéo avec ce qu'on ferait avec un mois de plus.

## Avant l'enregistrement

**Le jour J, tout se passe sur le PC de Benjamin.** Tu prends la souris et le clavier pendant ta partie, puis tu laisses la place au suivant.

Sous Windows, on lance Terraform **dans Docker** : le dépôt impose la version
exacte 1.13.5, et son fichier de verrouillage ne connaît que macOS et Linux.

1. Sur le PC de Benjamin, **terminal 2** : PowerShell dans `infra\terraform`
   du dépôt.
2. Avec Benjamin, la veille :

   ```powershell
   docker pull hashicorp/terraform:1.13.5
   docker run --rm -v "${PWD}:/work" -w /work -v "$env:APPDATA\gcloud:/gcloud:ro" -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json hashicorp/terraform:1.13.5 init -lockfile=readonly
   docker run --rm -v "${PWD}:/work" -w /work -v "$env:APPDATA\gcloud:/gcloud:ro" -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/application_default_credentials.json hashicorp/terraform:1.13.5 plan -detailed-exitcode -no-color
   ```

3. Regarde le résultat de ce premier plan **avant** l'enregistrement :
   - **« No changes »** : parfait, c'est ce qu'on montre.
   - **Des changements proposés :** c'est sûrement le passage d'Antoine et
     Colin en lecture seule (`iam.tf`), écrit mais pas encore appliqué. Le
     mieux est d'obtenir leur accord et de faire `apply` avant la vidéo (même
     commande avec `apply` à la place de `plan`). Sinon, tu utilises la
     phrase B plus bas.
   - **Une erreur de verrou (lock) :** ajoute `-lock=false` à la commande
     `plan`. Un plan ne modifie rien.
4. Laisse la commande `plan` **déjà tapée mais pas lancée** dans le
   terminal 2. Elle est longue : garde-la aussi dans un fichier texte pour la
   copier.

## Pendant ta partie

| Quand | Ce que tu fais | Ce que tu dis |
|---|---|---|
| Début | Terminal 2 | « Our cloud setup is written as code with **Terraform**: the bucket, the datasets, the access rights, the labels. » |
| 6:10 | Tu appuies sur **Entrée** | « This command compares the code with what really exists in Google Cloud. » |
| 6:25 | Tu montres le résultat | **A** — « "No changes": nobody changed anything by hand, the cloud matches the code. » <br> **B**, s'il y a des changements — « It shows one change we wrote but have not applied yet: making two members read-only. We will apply it once they agree. » |
| 6:45 | Tu te tournes vers le micro, le terminal reste visible | — |
| 6:50 | Tu parles, sans rien toucher | « With one more month, we would do four things. One: make those two members read-only. Two: prove the labels block someone, with an account outside the student role. Three: handle orders deleted in the shop, which today stay in our copy. Four: get the admin rights we lack, for a project-wide query limit and a budget alert. » |
| 7:20 | — | « Thanks for watching. » |
| Fin | Anthony arrête l'enregistrement | — |

## Les mots à expliquer si on te le demande

- **Terraform** : un outil qui écrit la configuration du cloud sous forme de
  code, pour pouvoir la reconstruire.
- **Plan** : Terraform compare le code et le cloud, et liste ce qu'il
  changerait. « No changes » veut dire que les deux sont identiques.
- **Read-only** : lecture seule, on peut lire mais pas modifier.
