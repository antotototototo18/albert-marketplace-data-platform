# Coûts de la plateforme

Fichier enrichi à chaque leçon ; il sert d'entrée au travail FinOps de L09.

## Tarifs utilisés

Lus le **16 octobre 2026** sur la [page de tarification de Cloud Storage](https://cloud.google.com/storage/pricing),
pour un bucket mono-région `europe-west1` (Belgique), en USD. Selon la page,
les dernières hausses sont entrées en vigueur le 1er octobre 2022 et le
1er avril 2023.

| Classe | Stockage (par GiB et par mois) | Opérations classe A (par 1 000) | Opérations classe B (par 1 000) | Frais de lecture (par GiB) | Durée minimale |
|---|---|---|---|---|---|
| Standard | $0.02 | $0.005 | $0.0004 | $0 | aucune |
| Nearline | $0.01 | $0.01 | $0.001 | $0.01 | 30 jours |
| Coldline | $0.004 | $0.02 | $0.01 | $0.02 | 90 jours |
| Archive | $0.0012 | $0.05 | $0.05 | $0.05 | 365 jours |

Points qui s'appliquent à notre cas :

- **Opérations :** les écritures (A) et les lectures ou listages (B) sont
  facturées par 1 000 requêtes. Les tarifs ci-dessus valent pour un espace de
  noms plat, celui de notre bucket.
- **Free tier :** il ne s'applique pas. Le quota gratuit (5 Go-mois) ne couvre
  que `us-west1`, `us-central1` et `us-east1`.
- **Transfert :** les données qui restent dans la même région sont gratuites.
  Un dataset BigQuery en `europe-west1` qui lit le bucket ne paie donc aucun
  transfert. Un téléchargement vers Internet coûte $0.12 par GiB.
- **Suppression :** un objet supprimé reste facturé 7 jours, la durée de la
  suppression réversible du bucket.

## L02 — bronze sur Cloud Storage

État du bucket `gs://data-engineering-i1-group6` le 16 octobre 2026.

| Élément | Volume | Coût mensuel | Source du volume |
|---|---|---|---|
| `bronze/legacy/`, 27 fichiers Parquet | 62 328 870 o = 0,0580 GiB | $0.00116 | [manifeste](evidence/l02-bronze-legacy-manifest.json) |
| `bronze/manual/`, `bronze/clickstream/` et préfixes techniques (L03), en croissance | 25 337 171 o = 0,0236 GiB | $0.00047 | `gcloud storage du -s`, moins `legacy/` |
| **Total stockage, classe Standard** | **87 666 041 o = 0,0816 GiB** | **$0.0016 par mois** | |

Opérations :

| Opération | Nombre | Coût |
|---|---|---|
| Écriture du chargement legacy (classe A) | 27 objets | $0.00014, une fois |
| Écritures L03 déjà présentes (classe A) | 207 objets | $0.00104, une fois |
| Lecture complète du legacy pour le chargement BigQuery de L04 (classe B) | 27 objets | $0.00001 par chargement |

**Effet du [lifecycle](../infra/lifecycle.json)** sur `bronze/legacy/` :

- **Calendrier :** Standard le premier mois, Nearline jusqu'à 90 jours, puis
  Coldline jusqu'à un an.
- **Coût sur la première année :** environ **$0.005**, transitions comprises
  (27 × $0.01 + 27 × $0.02 pour 1 000 opérations). Sans lifecycle, ce serait
  $0.014.
- **Contrepartie :** une relecture complète après 30 jours coûte $0.0006 de
  frais de récupération. Les chargements de L04-L05 doivent donc avoir lieu
  dans le premier mois, ou accepter ce coût.

À ce volume, la facture est inférieure à un centime par mois. Le format compte
déjà : les mêmes données en CSV (206 290 602 o) coûteraient 3,3 fois plus cher
à stocker.

## L04 : warehouse BigQuery

État de `group6_warehouse` le 26 octobre 2026
([mesures](evidence/l04-warehouse-measurements.json)). Le choix du compteur est
dans l'[ADR-0004](adr/0004-warehouse-pricing.md).

| Élément | Volume | Coût | Source |
|---|---|---|---|
| Tables natives, vue `daily_demand` comprise | 219 602 295 o de stockage logique, dont 88 253 584 o de copies de mesure (`*_untuned`, `order_items_day`) | ~$0.004 par mois à $0.020 par GiB-mois (tarif du cours L04) ; moitié moins après 90 jours sans modification | Tailles lues par l'API BigQuery |
| Tables externes `group6_bronze` | Aucune ligne stockée | $0 ; chaque requête relit le bucket | |
| Requête type du projet, à la demande | 4 à 13 Mo traités, 10 à 40 Mio facturés (minimum de 10 Mio par table lue) | $0.00007 à $0.0003 par requête, dans le Tio gratuit mensuel | [warehouse-tuning.md](warehouse-tuning.md) |
| Plafond par requête | 1 GiB | Au plus $0.0073 par requête avant refus ; un refus ne coûte rien | Jobs refusés, `JOBS_BY_USER` |

Supprimer les copies de mesure après relecture retire 40 % du stockage.

## Si les données étaient cent fois plus volumineuses

Le legacy passerait à 5,8 GiB, soit environ $0.12 par mois en Standard
($0.16 pour tout le bucket). Le layout actuel reste sobre en opérations : un
chargement écrit toujours 27 objets.

Ce qui changerait vraiment :

- **Partitionner par jour coûterait cher en opérations.** Il faudrait environ
  46 600 objets par chargement ($0.23 en écritures), multipliés par le nombre de
  lectures et de listages.
- **Des instantanés complets quotidiens rendraient le stockage dominant.**
  Ils ajouteraient environ $3.50 par mois, de façon cumulative. Il faudrait
  alors passer à l'incrémental ou au CDC (L03) et rendre le lifecycle
  indispensable.
- **Un téléchargement complet hors de GCP** coûterait environ $0.70 de
  transfert par copie.
