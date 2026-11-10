# ADR-0004: BigQuery à la demande, plafonné à 1 GiB par requête

- **Status:** proposed - à relire par le groupe
- **Date:** 2026-10-26
- **Author:** Benjamin Caujolle
- **Lesson:** L04

## Context

Le warehouse du groupe (`group6_warehouse`, `europe-west1`) contient sept tables
natives, 219,6 Mo au total en comptant les copies de mesure
([warehouse-tuning.md](../warehouse-tuning.md)). BigQuery propose deux compteurs :
**à la demande**, facturé aux octets traités, et **à la capacité** (éditions),
facturé aux slots réservés, que des requêtes tournent ou non.

**La charge, en chiffres.** Les mesures viennent de
[l04-warehouse-measurements.json](../evidence/l04-warehouse-measurements.json) et
de `INFORMATION_SCHEMA.JOBS_BY_USER` ; les estimations sont signalées comme telles.

| Grandeur | Valeur | Source |
|---|---|---|
| Octets traités par requête du projet | 0,02 à 37 Mo | Mesuré (Q1 à Q3, sondes de réglage) |
| Octets facturés par requête | 10 à 40 Mio, minimum de 10 Mio **par table lue** | Mesuré : Q2 lit 4 tables et facture 41 943 040 o |
| Requêtes par jour | Environ 60 : ~35 pour un `dbt build` quotidien (L05, L07), 1 lecture ML, ~23 de développement | **Estimé.** Le développement extrapole 98 requêtes en 30 jours pour un membre (mesuré) à cinq membres |
| Concentration | Une rafale nocturne (dbt, quelques minutes), puis des requêtes isolées pendant les séances et le soir | **Estimé** à partir du calendrier du cours |
| Concurrence en pointe | 5 personnes, plus 4 threads dbt | Taille du groupe ; `threads: 4` du profil dbt |
| Volume facturé par mois | ~60 × 30 × 20 Mio ≈ 35 Gio ≈ **0,034 Tio** | **Estimé** ; un membre a mesuré 0,0012 Tio facturé en 30 jours |
| Slot-heures consommées | 0,54 en 30 jours pour un membre | Mesuré (`total_slot_ms`) |

**Tarifs.** À la demande : $7.50 par Tio en `europe-west1`, premier Tio gratuit
chaque mois (tarif du cours L04). À la capacité, prix de liste pour la Belgique
trouvés dans une source secondaire datée de 2024
([Cloudfresh](https://cloudfresh.com/en/blog/bigquery-pricing-2024/)) : Standard
$0.044 par slot-heure sans engagement possible ; Enterprise $0.066 sans
engagement, $0.0528 sur un an, $0.0396 sur trois ans. La page officielle n'a
pas pu être lue région par région ; ces prix sont à revérifier avant toute
décision d'achat. La documentation officielle confirme que l'autoscaling se fait
« par multiples de 50 slots », est facturé « à la seconde avec une minute
minimum », pour les slots alloués et non utilisés
([autoscaling](https://docs.cloud.google.com/bigquery/docs/slots-autoscaling-intro)),
et que les engagements n'existent qu'en Enterprise et Enterprise Plus
([engagements](https://docs.cloud.google.com/bigquery/docs/reservations-commitments)).

## Options considered

| Option | Pour | Contre |
|---|---|---|
| **À la demande** (retenue) | Rien à payer entre deux requêtes ; notre volume tient dans le Tio gratuit ; aucun engagement | Facture non bornée : une seule requête imprudente peut coûter des dizaines de dollars (3,48 Tio = $26 dans la démo L04). Une vue matérialisée qui ne réduit pas les octets ne rapporte rien |
| Standard, autoscaling sans engagement | Pas d'engagement ; facture bornée par le maximum de slots fixé | Au moins 50 slots pendant au moins une minute par rafale : une requête isolée coûte 50 × 1/60 × $0.044 = **$0.037**, contre $0.00007 pour 10 Mio à la demande, soit ~500× plus. Nos requêtes sont justement isolées : ~23 × $0.037 par jour, plus ~$0.18 pour une rafale dbt de 5 minutes, soit **~$31 par mois** (estimé) |
| Enterprise, engagement d'un an, 50 slots | Coût fixe et prévisible ; les gains de temps (vue matérialisée, grain mensuel) deviennent des économies | $1 927 par mois, payés même la nuit et le week-end, pour une charge qui en consomme quelques slot-heures |
| Enterprise, engagement de trois ans | Prix par slot le plus bas ($0.0396) | Même problème de volume, et le cours se termine en décembre |

**L'arithmétique de bascule.**

```text
à la demande :  (T - 1) × $7.50          T = Tio facturés par mois
capacité :      50 slots × 730 h × $0.0528 = $1 927.20 par mois
bascule :       (T - 1) × 7.50 = 1 927.20   =>   T ≈ 258 Tio par mois
```

Avec 100 slots, la bascule monte à environ 515 Tio par mois. Notre charge
estimée est de 0,034 Tio : **environ 7 600 fois sous la bascule**, et même sous
le Tio gratuit. Pour que la capacité devienne rentable, il faudrait que chaque
requête du groupe lise environ 150 Gio, et non 20 Mio.

## Criteria

- **Coût au volume réel :** à la demande coûte $0 aujourd'hui ; la capacité
  coûte entre ~$30 (Standard, estimé) et $1 927 par mois.
- **Forme de la charge :** des requêtes rares et isolées, plus une rafale
  nocturne. C'est le cas où un compteur bat un loyer (cours L04, §2).
- **Risque :** la seule faiblesse de l'option à la demande est la requête
  imprudente. Elle se traite par un plafond, pas par un changement de compteur.
- **Réversibilité :** passer à la capacité plus tard ne demande qu'une
  réservation ; un engagement annuel, lui, ne se défait pas.

## Decision

Le projet reste **à la demande**, et chaque chemin de requête que nous
contrôlons porte un plafond `maximum_bytes_billed` de **1 GiB** : le script de
mesure, le CLI `bq` via `~/.bigqueryrc` et dbt à partir de L05
([emplacements](../warehouse-tuning.md#5-le-plafond-maximum_bytes_billed)).

## Consequences

**Ce que nous acceptons.** Une facture sans plafond au niveau du projet : le
quota journalier se règle sur `data-engineering-i1`, partagé avec les autres
groupes, et nos comptes n'en ont pas le droit. Un membre qui n'a pas réglé sa
console reste exposé. Le pire cas plafonné est de $0.0073 par requête ; le pire
cas non plafonné n'a pas de limite.

**Ce que la décision rend inutile.** Économiser du temps de calcul sans
économiser d'octets ne rapporte rien. La vue `daily_demand` (1,00×) et le grain
journalier (42× plus de temps de slot pour Q1) seraient jugés autrement à la
capacité ; ici, seuls les octets comptent.

**Ce qui nous ferait changer d'avis,** à surveiller une fois par mois :

| Signal | Seuil | Ce qu'il déclenche |
|---|---|---|
| Tio facturés par mois, groupe | > 1 Tio | La facture commence ($7.50 par Tio) : chercher les requêtes non élaguées avant de payer |
| Tio facturés par mois, groupe | > 258 Tio pendant deux mois | Évaluer un engagement Enterprise de 50 slots |
| Requête légitime refusée par le plafond | Une seule | La donnée a grossi : re-mesurer le grain et le plafond, nouvel ADR si le plafond change |

Requête de suivi, à lancer par chaque membre (la somme des cinq donne le groupe) :

```sql
SELECT ROUND(SUM(total_bytes_billed) / POW(2, 40), 4) AS tib_billed_30_days
FROM `region-europe-west1`.INFORMATION_SCHEMA.JOBS_BY_USER
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND job_type = 'QUERY';
```

**Ce que nous n'avons pas pu mesurer.** La consommation du projet entier :
`JOBS_BY_PROJECT` répond `Access Denied` (permission `bigquery.jobs.listAll`).
Le Tio gratuit s'applique au compte de facturation, donc il est probablement
partagé avec la vingtaine d'autres datasets visibles dans le projet. Si ces
groupes le consomment, notre première requête du mois est déjà payante, sans
que la décision change : $7.50 par Tio sur 0,034 Tio, c'est $0.26 par mois.
Pour le savoir, il faudrait demander à l'équipe enseignante le total facturé
du projet, ou un rôle qui donne `bigquery.jobs.listAll`.
