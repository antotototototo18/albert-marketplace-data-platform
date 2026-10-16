# Dictionnaire de données — v1 (L02)

Version du 16 octobre 2026. Elle couvre les 27 tables de l'export legacy
chargées dans `gs://data-engineering-i1-group6/bronze/legacy/<table>/ingested_date=2026-10-16/`
([ADR-0002](adr/0002-bronze-layout.md), [manifeste](evidence/l02-bronze-legacy-manifest.json)).
Les flux L03 (`bronze/manual/`, `bronze/clickstream/`) seront ajoutés par
leurs auteurs.

## Comment lire ce dictionnaire

- **Type bronze :** toutes les colonnes sont stockées en `STRING`, exactement
  comme dans le CSV. Les cellules vides restent des chaînes vides.
- **Type observé :** ce que contiennent les valeurs, d'après un profil de toutes
  les lignes. C'est le type que silver devra appliquer (L05), sauf indication
  contraire.
- **`unnamed_0` :** la première colonne de la plupart des CSV n'a pas d'en-tête.
  C'est un index technique de l'export, nommé `unnamed_0` dans bronze, sans
  sens métier. Elle n'est pas répétée dans les tableaux ci-dessous.
  `order_items` et `payment` n'en ont pas.

| Donnée personnelle | Signification | Conséquence |
|---|---|---|
| **Secret — exclu** | Mot de passe ou donnée de carte complète | Jamais écrit dans bronze ([ADR-0001](adr/0001-target-architecture.md)) ; à exclure à la source en L03 |
| **Directe** | Identifie ou permet de contacter une personne | Accès restreint ; masquage ou pseudonymisation en silver ; audit L10 |
| **Indirecte** | Identifiant pseudonyme ou quasi-identifiant qui relie une ligne à une personne | Reste une donnée personnelle au sens du RGPD ; ne pas exposer en gold sans besoin |
| **Possible** | Texte libre ou image fournis par un utilisateur, qui peuvent contenir des données personnelles | À traiter comme personnel tant qu'il n'est pas filtré |
| **Non** | Aucune donnée personnelle | — |

## Comptes et clients

### `customer` — 130 766 lignes

Tous les comptes : les 100 000 acheteurs de `buyer` et les 30 766 vendeurs de
`seller`.

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `c_id` | texte (30 car.) | Identifiant du compte | Indirecte |
| `fname` | texte | Prénom | **Directe** |
| `lname` | texte | Nom de famille | **Directe** |
| `phone` | texte (chiffres) | Téléphone ; 82 203 valeurs commencent par `0`, donc ne jamais le typer en nombre | **Directe** |
| `email` | texte | Adresse e-mail, unique par compte | **Directe** |
| `pwd` | — | Mot de passe | **Secret — exclu**, absent de bronze |

### `buyer` — 100 000 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `buyer_id` | texte (28 car.) | Compte acheteur ; égal à un `customer.c_id` | Indirecte |

### `seller` — 30 766 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `seller_id` | texte (30 car.) | Compte vendeur ; égal à un `customer.c_id` | Indirecte |
| `seller_type` | texte | `third_party_seller` (30 765) ou `marketplace` (1) | Non |
| `seller_name` | vide | Nom du vendeur ; vide sur toutes les lignes de cet export | **Directe** si renseigné |

### `customer_shipping` — 200 001 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `address_id` | entier | Adresse, vers `shipping_details.address_id` | Indirecte |
| `c_id` | texte | Acheteur propriétaire de l'adresse | Indirecte |
| `is_default` | entier (0/1) | Adresse par défaut du client | Non |

### `shipping_details` — 200 001 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `address_id` | entier | Identifiant de l'adresse | Indirecte |
| `street_address` | texte | Rue et numéro | **Directe** |
| `city` | texte | Ville | Indirecte (quasi-identifiant) |
| `state` | texte | Région administrative | Non |
| `zip` | texte | Code postal : 19 622 commencent par `0` et 12 630 contiennent des lettres (format néerlandais) ; à garder en texte | Indirecte (quasi-identifiant) |
| `country` | texte | Pays, en toutes lettres : Germany, France, Italy, Spain, Netherlands, Belgium | Non |
| `phone` | texte (chiffres) | Téléphone de livraison ; 125 861 valeurs commencent par `0` | **Directe** |

### `customer_payment` — 100 000 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `payment_id` | entier | Moyen de paiement enregistré, vers `payment_details` | Indirecte |
| `c_id` | texte | Acheteur titulaire | Indirecte |
| `is_default` | entier (toujours 1) | Moyen de paiement par défaut | Non |

### `payment_details` — 100 000 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `payment_id` | entier | Identifiant du moyen de paiement | Indirecte |
| `card_no` | — | Numéro de carte complet | **Secret — exclu**, absent de bronze |
| `cvv` | — | Cryptogramme | **Secret — exclu**, absent de bronze |
| `expiry_date` | date | Expiration de la carte (2026-07-28 à 2030-07-27) | **Directe** (donnée de carte) |
| `billing_address` | texte | Adresse de facturation complète | **Directe** |

### `subscription` — 50 091 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `subscription_id` | entier | Identifiant de l'abonnement | Non |
| `c_id` | texte | Acheteur abonné | Indirecte |
| `start_date` | date | Début (2024-07-27 à 2025-07-27) | Non |
| `end_date` | date | Fin, un an après le début | Non |

## Catalogue

### `product` — 42 858 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `p_id` | texte (10 car.) | Identifiant produit de type ASIN (`B0…` pour 42 835 produits) ; 6 commencent par `0`, donc à garder en texte | Non |
| `p_name` | texte | Nom du produit (6 vides) | Non |
| `p_desc` | texte (JSON) | Attributs du produit, objet JSON sérialisé | Non |
| `price` | décimal | Prix catalogue, non arrondi : jusqu'à 20 décimales | Non |
| `qty` | entier | Stock disponible (1 à 99) | Non |
| `category_id` | entier | Catégorie, vers `category` | Non |

### `category` — 2 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `category_id` | entier | Identifiant | Non |
| `name` | texte | `All Beauty`, `Premium Beauty` | Non |
| `c_desc` | texte | Description courte | Non |

### `product_images` — 186 837 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `p_id` | texte | Produit | Non |
| `p_image` | texte (URL) | URL d'une image du catalogue | Non |

### `seller_products` — 46 593 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `seller_id` | texte | Vendeur | Indirecte |
| `p_id` | texte | Produit vendu | Non |

### `daily_deals` — 0 ligne

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `p_id` | vide | Produit en promotion | Non |
| `deal_date` | vide | Jour de la promotion | Non |
| `discount` | vide | Remise | Non |

### `discount` — 0 ligne

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `discount_id` | vide | Identifiant de la remise | Non |
| `discount_name` | vide | Nom | Non |
| `d_desc` | vide | Description | Non |
| `discount_amt` | vide | Montant | Non |

## Commandes, paiements et livraisons

### `orders` — 222 644 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `order_id` | entier | Identifiant de la commande, unique | Non |
| `buyer_id` | texte | Acheteur | Indirecte |
| `discount_id` | vide | Remise appliquée ; vide sur toutes les lignes | Non |
| `payment_id` | entier | Moyen de paiement utilisé, vers `payment_details` | Indirecte |
| `order_date` | date | Jour de la commande (2023-09-15 à 2026-09-14, 1 096 jours) | Non |

### `order_items` — 408 560 lignes

Pas de colonne `unnamed_0`.

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `order_id` | entier | Commande, vers `orders` | Non |
| `p_id` | texte | Produit | Non |
| `qty` | entier | Quantité (1 à 9) | Non |
| `price_at_purchase` | décimal (2 déc.) | Prix unitaire payé | Non |

### `payment` — 222 644 lignes

Une transaction par commande. Pas de colonne `unnamed_0`. Pour les 222 644
commandes, `amount` est égal à la somme de `qty × price_at_purchase`.

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `transaction_id` | entier | Identifiant de la transaction | Non |
| `order_id` | entier | Commande payée | Non |
| `payment_id` | entier | Moyen de paiement | Indirecte |
| `amount` | décimal | Montant de la transaction | Non |
| `method` | texte | Toujours `Credit Card` | Non |
| `status` | texte | Toujours `completed` | Non |
| `created_at` | horodatage | Date et heure du paiement, sans fuseau | Non |

### `shipment` — 408 560 lignes

Une livraison par ligne de commande.

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `shipping_id` | entier | Identifiant de la livraison | Non |
| `order_id` | entier | Commande | Non |
| `p_id` | texte | Produit livré | Non |
| `carrier_id` | entier | Transporteur, vers `carrier` | Non |
| `shipment_type` | texte | Toujours `NP`, code non documenté | Non |
| `status` | texte | `delivered` (404 679), `in_transit` (2 807), `processing` (1 074) | Non |
| `est_delivery_date` | date | Livraison prévue | Non |
| `actual_delivery_date` | date | Livraison réelle ; vide sur 3 881 lignes non livrées | Non |

### `carrier` — 4 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `carrier_id` | entier | Identifiant | Non |
| `carrier_name` | texte | Nom du transporteur | Non |

### `cart` — 0 ligne

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `cart_id` | vide | Panier | Non |
| `buyer_id` | vide | Acheteur | Indirecte |
| `total_qty` | vide | Quantité totale | Non |
| `total_price` | vide | Montant total | Non |

### `cart_items` — 0 ligne

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `cart_id` | vide | Panier | Non |
| `p_id` | vide | Produit | Non |
| `qty` | vide | Quantité | Non |

### `returns` — 0 ligne

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `return_id` | vide | Retour | Non |
| `buyer_id` | vide | Acheteur | Indirecte |
| `p_id` | vide | Produit retourné | Non |
| `order_id` | vide | Commande | Non |

### `wishlist_item` — 24 810 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `product_id` | texte | Produit ; même identifiant que `p_id` sous un autre nom | Non |
| `buyer_id` | texte | Acheteur | Indirecte |

## Avis

### `review` — 111 322 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `review_id` | entier | Identifiant de l'avis | Non |
| `buyer_id` | texte | Auteur de l'avis | Indirecte |
| `r_desc` | texte | Texte de l'avis (14 vides) | **Possible** (texte libre) |
| `title` | texte | Titre de l'avis | **Possible** (texte libre) |
| `rating` | entier | Note de 1 à 5 | Non |
| `seller_product_flag` | texte | Toujours `S`, code non documenté | Non |

### `review_images` — 119 382 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `review_id` | entier | Avis illustré | Non |
| `review_img` | texte (URL) | Photo publiée par l'auteur de l'avis | **Possible** (image d'utilisateur) |

### `product_reviews` — 111 322 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `p_id` | texte | Produit évalué | Non |
| `review_id` | entier | Avis | Non |

### `seller_reviews` — 111 322 lignes

| Colonne | Type observé | Signification | Donnée personnelle |
|---|---|---|---|
| `seller_id` | texte | Vendeur évalué | Indirecte |
| `review_id` | entier | Avis | Non |

## Bilan pour L03 et L10

- **Ne jamais ingérer :** `customer.pwd`, `payment_details.card_no` et
  `payment_details.cvv`. Ils sont absents de bronze et les pipelines L03 doivent
  les exclure à la source.
- **Données personnelles directes présentes dans bronze :**
  - `customer` : `fname`, `lname`, `phone`, `email`
  - `shipping_details` : `street_address`, `phone`
  - `payment_details` : `expiry_date`, `billing_address`

  Ce sont les colonnes à auditer et à masquer en L10.
- **À ne pas typer en nombre :** `phone`, `zip` et `p_id`, sous peine de
  perdre les zéros initiaux.
