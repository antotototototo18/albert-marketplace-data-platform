# Présentation du projet — groupe 6

Pitch de 10 minutes en 6 slides, construit sur les consignes du prof
(`Porject_guidelines.md`) : un problème, le schéma, **deux décisions en
profondeur**, un échec, la suite. Les anciennes slides L01 à L10 restent dans le
deck comme **slides de secours** (A1 à A12), pour les questions.

- **Deck en ligne :** <https://claude.ai/artifact/W5DBUR3ESA3W3Ua4mkr2L8>
  (privé pour l'instant, Anthony doit le partager).
- **Sources :** `deck.json` (ordre des slides), `deck.css` (style commun) et
  `slides/<dossier>/slide.html`. Les notes de l'orateur sont dans le `<aside>`
  de chaque slide.
- **Script oral, en anglais :** [SCRIPT.md](SCRIPT.md). Le texte mot à mot de
  chaque slide, les réponses courtes aux questions probables (avec qui répond)
  et un glossaire de tous les sigles. Le même texte est dans les notes des
  slides.
- **Par slide :** un `README.md` donne qui parle, le message clé et où trouver
  la preuve si on nous la demande.
- **Glossaire :** une slide de secours juste après le pitch, à montrer si un mot
  bloque pendant les questions.

## Le pitch : 10 minutes

Proposition à valider en PR.

| # | Slide | Qui parle | Durée | Fin à |
|---|---|---|---|---|
| 1 | [Le problème](slides/01-cover/README.md) | Antoine | 1 min | 1:00 |
| 2 | [Ce qu'on a construit](slides/02-arch/README.md) | Colin | 2 min | 3:00 |
| 3 | [Décision 1 : payer à la requête (ADR-0004)](slides/03-decision-pricing/README.md) | Benjamin | 2 min | 5:00 |
| 4 | [Décision 2 : l'accès par classe (ADR-0010)](slides/04-decision-access/README.md) | Anthony | 2 min | 7:00 |
| 5 | [Ce qui a mal tourné (L07)](slides/05-failure/README.md) | Benjamin | 2 min | 9:00 |
| 6 | [Ce qu'on ferait ensuite](slides/06-next/README.md) | Lenny | 1 min | 10:00 |

Viser 9 min 30 au chrono, pour garder une marge.

**Pourquoi ces deux décisions :** ce sont celles qui ont les chiffres les plus
nets (le seuil de 258 Tio) et l'argument le plus disputé (le cours dit que
l'ADR-0010 est « le meilleur à défendre »). **Pourquoi cet échec :** le
back-fill perdu est un vrai incident, et la gate qui laisse passer 87,90 € de
trop montre un changement de conception, chiffré avant et après.

## Les passages entre orateurs

L'oral se fait en anglais. À répéter au moins une fois, seuls, sans le reste du
pitch.

| De → à | Phrase |
|---|---|
| Antoine → Colin | "Colin will show you what we built to fix this." |
| Colin → Benjamin | "Benjamin, the first one: how we pay for BigQuery." |
| Benjamin → Anthony | "Anthony takes the second decision: who can read what." |
| Anthony → Benjamin | "Not everything went to plan. Benjamin." |
| Benjamin → Lenny | "Lenny closes with what we would do next." |

Une seule personne tient l'ordinateur pendant tout le pitch : pas d'échange de
laptop.

## Qui répond à quoi

Une personne commence. Les autres n'ajoutent quelque chose que si c'est utile.

| Sujet | Répond d'abord | Slide de secours |
|---|---|---|
| Architecture d'ensemble, choix des deux étages | Colin, puis Anthony (ADR-0001) | 2, A2 |
| Bronze, layout, compression | Antoine (ADR-0002) | A3 |
| Ingestion, Airbyte, Kafka, DLQ | Anthony (ADR-0003) | A4 |
| Warehouse, partitions, coût des requêtes | Benjamin (ADR-0004) | 3, A5 |
| dbt, vues ou tables, doublons, tests | Antoine (ADR-0005) | A6 |
| Images Docker, tags | Lenny (ADR-0006) | A7 |
| Airflow, idempotence, back-fill | Benjamin (ADR-0007) | 5, A8 |
| Terraform, state distant | Lenny (ADR-0008) | A9 |
| Coûts, labels | Anthony (ADR-0009) | A10 |
| Classes, tags, droits d'accès | Benjamin, puis Anthony (ADR-0010) | 4, A11 |
| Effacement RGPD | Anthony | A11 |
| Ce qui reste ouvert | le responsable de la ligne | 6, A12 |

## Lire un ADR qu'on n'a pas écrit

Le prof interroge chacun sur un choix qu'il n'a pas forcément fait. Chacun lit
au moins un ADR qui n'est pas le sien, puis se fait interroger 10 minutes par un
autre membre. Proposition :

| Qui | Lit | Pourquoi celui-là |
|---|---|---|
| Colin | ADR-0007 (idempotence) | « Que se passe-t-il si le même intervalle tourne deux fois ? » est annoncé en L07 |
| Antoine | ADR-0010 (accès par classe) | La question la plus probable selon L10 |
| Benjamin | ADR-0008 (state Terraform) | « Qui peut lire le bucket ? Et si on supprime le state ? » est annoncé en L08 |
| Lenny | ADR-0004 (prix BigQuery) | Il présente la suite, qui parle de quota |
| Anthony | ADR-0005 (vues ou tables) | L'exemple que donne le prof |

## Si on ne sait pas

Réponse forte : « Je ne sais pas, c'est Benjamin qui l'a écrit. Ce que je peux
dire, c'est pourquoi on en avait besoin : … Benjamin peut vous dire pourquoi il
a choisi cette approche. »

À éviter : une réponse inventée sur un ton sûr. La question suivante portera
sur le même sujet.

## Pas de démo en direct

Le prof demande de montrer une vidéo enregistrée ou une capture, pas une démo
en direct. **La vidéo n'existe pas encore dans le dépôt**, et le README
principal n'a pas de lien vers elle. Il faut décider qui l'enregistre.

## La veille

- [ ] Le pitch tient en moins de 10 minutes, chronométré, avec les passages.
- [ ] Chaque affirmation du pitch a un chiffre (déjà le cas sur les 6 slides).
- [ ] Tout le monde sait qui répond à quoi (tableau ci-dessus).
- [ ] La vidéo se lance depuis le lien du README, sur une machine qui ne l'a pas
      enregistrée.
- [ ] Chacun a lu l'ADR sur lequel il sera interrogé, et au moins un qu'il n'a
      pas écrit.
- [ ] Quelqu'un a relu le dépôt avec la checklist du cours.
- [ ] Slide 6 : vérifier si le droit réduit a été appliqué entre-temps.

## Règle pour les chiffres

Chaque chiffre affiché vient d'un fichier du dépôt, cité dans le README de la
slide et dans ses notes. Si un chiffre change, corriger d'abord le document
source, puis la slide. Les chiffres du pitch et des réponses ont été vérifiés le 21 novembre
2026.
