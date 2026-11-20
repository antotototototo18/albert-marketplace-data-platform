# Data governance — L10

L10 version of 17 November 2026. For every column of the warehouse, this document
answers the first two of lesson 10's four questions: **what is it?** (a class) and
**who may read it?** (the access matrix). The other two are answered elsewhere: who
did read it, in [the audit evidence](evidence/l10/03-who-read-shipping.txt); how long
we keep it and how to erase it, in [the erasure runbook](runbooks/erasure.md). Why
access is granted by class rather than by table is argued in
[ADR-0010](adr/0010-data-classification.md).

## Starting point, measured on 16 November 2026

- Any account of the shared project `data-engineering-i1` reads the 200,001 street
  addresses and phone numbers of `group6_warehouse.shipping_details`
  ([evidence](evidence/l10/01-who-can-see-what.txt)). Nobody decided it: it is what
  the grants made to load data in L02 and L04 add up to.
- All four datasets give `READER` to `projectReaders` and `WRITER` to
  `projectWriters`; the bronze bucket gives `legacyObjectReader` to `projectViewer`
  ([datasets](evidence/l10/02-datasets-acl.txt), [bucket](evidence/l10/02-bucket-iam.txt)).
  By configuration, the other groups of the class read our data.
- The student role grants, at project level, read access to every table and object,
  and `roles/datacatalog.categoryFineGrainedReader`
  ([measured permissions](evidence/l10/02-project-permissions.txt)). Checked for two
  members of the group (Benjamin, Lenny). See
  [Gaps](#gaps-between-the-matrix-and-what-is-enforced) for what that means.

## Classes

A class says **what the data is**, never who may see it: the audience changes, the
data does not. The levels of the [data dictionary](data-dictionary.md) (Directe,
Indirecte, Possible, Secret) are kept, under a class name that a grant can target.

| Class | Holds | Dictionary level | Example |
|---|---|---|---|
| `public` | What the site already shows to any visitor | Non | `product.p_name`, `dim_date` |
| `internal` | Business data with no personal content | Non | `orders.order_date`, `fct_daily_demand` |
| `pii.identifier` | Stable pseudonymous id of a person or of their address: names nobody alone, but enables the join that does | Indirecte | `buyer_id`, `c_id`, `address_id`, `session_id` |
| `pii.location.coarse` | Location finer than a region, short of an address: a quasi-identifier | Indirecte | `shipping_details.city`, `zip` |
| `pii.contact` | Names or reaches a person | Directe | `shipping_details.street_address`, `phone`; `customer.email` |
| `pii.financial` | Partial card data | Directe | `payment_details.expiry_date` |
| `unclassified` | Free text or images typed by a user: the schema says nothing about the content | Possible | `review.r_desc`, `clickstream.raw_event` |
| `secret` | Password, card number, CVV | Secret — exclu | `customer.pwd`: **never ingested** |

`unclassified` is not a clean class. It says honestly that we cannot tell: a
customer can type their phone number, or somebody else's name, into a review. No
content inspection (Sensitive Data Protection) is in place; for access, these
columns are treated like `pii.contact`.

Pseudonymous is not anonymous. The warehouse holds no names or emails, but
`buyer_id` follows one person through every order and `shipping_details` gives
their address: it is personal data under GDPR Article 4(1), and the whole
regulation applies.

## Owners

An owner is a role that can answer questions about a column, with a named lead. No
column is owned by "nobody".

| Owning role | Covers | Lead |
|---|---|---|
| Ingestion | `group6_bronze` external tables, bronze bucket, clickstream and DLQ | Anthony Rascle |
| Warehouse | `group6_warehouse`, `group6_bronze.orders_raw` and `order_items_raw` (L07 DAG) | Benjamin Caujolle |
| Transformation | `group6_silver`, `group6_gold` (dbt) | Antoine Rabeau |
| Platform | Taxonomy, IAM, Terraform | Lenny Santus |
| GDPR requests | Access and erasure (Articles 15 and 17), [runbook](runbooks/erasure.md) | Benjamin Caujolle |

## Classification, column by column

Each table is owned by the owner of its layer (table above). `unnamed_0` is the
legacy export's technical index: `internal` everywhere. The `*_untuned` copies in
`group6_warehouse` (L04 measurements) have exactly the columns and classes of the
tuned table of the same name.

### Bronze — `group6_bronze` (external tables over Parquet, and L07 native tables)

| Table | Column | Class | Why |
|---|---|---|---|
| `orders`, `orders_raw` | `order_id`, `discount_id`, `order_date` | internal | order data |
| | `buyer_id` | pii.identifier | follows a customer across all their orders |
| | `payment_id` | pii.identifier | leads to `payment_details`, hence to a billing address |
| | `_loaded_at` (`orders_raw`) | internal | `MERGE` timestamp |
| `order_items`, `order_items_raw` | `order_id`, `p_id`, `qty`, `price_at_purchase`, `_loaded_at` | internal | order lines |
| `product` | `p_id`, `p_name`, `p_desc`, `price`, `category_id` | public | shown on the product page; `p_desc` is a JSON of product attributes |
| | `qty` | internal | stock |
| `review` | `review_id`, `rating`, `seller_product_flag` | internal | |
| | `buyer_id` | pii.identifier | author of the review |
| | `r_desc`, `title` | **unclassified** | free text, up to 20,000 characters |
| `product_reviews` | `p_id`, `review_id` | internal | link table |
| `customer_shipping` | `c_id`, `address_id` | pii.identifier | links a customer to their addresses |
| | `is_default` | internal | |
| `shipping_details` | `address_id` | pii.identifier | key of a personal address |
| | `street_address`, `phone` | **pii.contact** | locate and reach a person |
| | `city`, `zip` | pii.location.coarse | quasi-identifiers |
| | `state`, `country` | internal | too broad to single anyone out |
| `clickstream` | `schema_version`, `event_id`, `event_type`, `event_time`, `emitted_at`, `p_id`, `price`, `qty`, `order_id`, `payment_method`, `amount`, `currency`, `items`, `_kafka_topic`, `_kafka_partition`, `_kafka_offset`, `_ingested_at`, `dt` | internal | browsing event |
| | `session_id`, `buyer_id` | pii.identifier | follow a visitor |
| | `raw_event` | **unclassified** | raw JSON, carries the original identifiers |

Tables that exist **only as Parquet** in the bucket (not declared in BigQuery,
readable by anyone who can read the bucket):

| Table | Personal columns | Class |
|---|---|---|
| `customer` | `fname`, `lname`, `phone`, `email` | pii.contact |
| `customer` | `c_id` | pii.identifier |
| `payment_details` | `billing_address` | pii.contact |
| `payment_details` | `expiry_date` | pii.financial |
| `seller` | `seller_name` (empty in the export) | pii.contact |
| `wishlist_item`, `subscription`, `buyer`, `customer_payment` | customer ids | pii.identifier |
| `review_images` | `review_img` | unclassified |
| `customer.pwd`, `payment_details.card_no`, `payment_details.cvv` | — | secret, **excluded at ingestion** ([L03](../ingestion/airbyte/selection.json)) |

The clickstream DLQ (`bronze/_dlq/clickstream/`) keeps the rejected event as it
arrived: `unclassified`.

### Warehouse — `group6_warehouse`

| Table | Columns and classes |
|---|---|
| `orders` | `order_id`, `discount_id`, `order_date` internal; `buyer_id`, `payment_id` pii.identifier |
| `order_items`, `order_items_day` | all internal |
| `product` | as in bronze: public, `qty` internal |
| `review` | `review_id`, `rating`, `seller_product_flag` internal; `buyer_id` pii.identifier; `r_desc`, `title` **unclassified** |
| `product_reviews` | internal |
| `customer_shipping` | `c_id`, `address_id` pii.identifier; `is_default` internal |
| `shipping_details` | `address_id` pii.identifier; **`street_address`, `phone` pii.contact — tagged**; **`city`, `zip` pii.location.coarse — tagged**; `state`, `country` internal |
| `daily_demand` (materialized view) | all internal: aggregate per product and day, no row per person |

### Silver — `group6_silver` (dbt views)

| Model | Columns and classes |
|---|---|
| `stg_orders`, `int_orders__deduplicated` | `order_id`, `order_date` internal; `buyer_id`, `payment_id` pii.identifier |
| `stg_order_items` | internal |
| `stg_product` | `p_id`, `p_name`, `p_desc`, `catalogue_price`, `category_id` public; `stock_qty` internal |
| `stg_review` | `review_id`, `rating` internal; `buyer_id` pii.identifier; `review_text`, `review_title` **unclassified** |
| `stg_product_reviews` | internal |
| `stg_customer_shipping` | `c_id`, `address_id` pii.identifier; `is_default` internal |
| `stg_shipping_details` | `address_id` pii.identifier; `state`, `country_name`, `country_code` internal. **Street, phone, city and postcode are dropped here**: no model reads them |
| `stg_clickstream` | as in bronze, without `raw_event` and `items`: `session_id`, `buyer_id` pii.identifier, the rest internal |
| `int_orders__country` | internal |
| `int_product__ratings` | internal (counts and averages) |

### Gold — `group6_gold` (dbt tables)

| Model | Class |
|---|---|
| `fct_order_items`, `fct_daily_demand` | internal |
| `dim_product` | public (catalogue) and internal (`review_count`, `avg_rating`) |
| `dim_date`, `dim_country` | public |

Gold holds no personal column, and `transform/tests/assert_no_personal_columns_in_gold.sql`
(criterion C13) fails if a column with a personal name appears in it.

## Access matrix

Operations: **read** (query the column), **write** (load or change it), **no**.

| Role | public | internal | pii.identifier | pii.location.coarse | pii.contact, pii.financial | unclassified |
|---|---|---|---|---|---|---|
| Analyst (reads gold for a dashboard) | read | read | no | no | no | no |
| Group engineer (builds the pipeline) | read, write | read, write | read, write | no | no | read |
| Pipeline (dbt and the Airflow DAG) | read, write | read, write | read, write | no | no | read |
| GDPR request handler | read | read | read | read, during a request | read and erase, during a request | read and erase, during a request |
| Other groups of the shared project | no | no | no | no | no | no |

Why **nobody** reads `pii.contact` routinely: no model, no L04 query and no
dashboard needs it. `stg_shipping_details` drops the street and the phone, and
analysis by country goes through `state` and `country`. Data minimisation (GDPR
Article 5(1)(c)) therefore says: nobody.

What each "no" does when the need is real:

| Who | Needs | Route |
|---|---|---|
| Analyst | a customer id (cohort, retention) | "Access request" issue: the need, the duration, the column. The engineer builds an aggregate or a hashed `buyer_id` in gold rather than opening silver |
| Engineer, pipeline | a city or a postcode | "Access request" issue reviewed by a second member; if the need lasts, a silver model that reads it, and a line in this document |
| Engineer, pipeline | the street or the phone | not through analytics: a legitimate need (delivery, support) is served by the source system, not by the warehouse |
| GDPR request handler | to read `pii-contact` | `categoryFineGrainedReader` on the `pii-contact` tag, granted by Terraform (`pii_contact_readers`) for the duration of the request, removed when it closes; the issue is the request record |
| Other group | anything | no legitimate need: no route |

Who decides: the owner of the layer, with a second member's written agreement in
the issue. `roles/datacatalog.categoryAdmin` is treated as privileged: deleting the
taxonomy removes the protection of every column, with no error, and the schema keeps
showing the tag (lesson 10 demo, step 8). The only proof that a column is protected
is a refusal.

## Enforcement

| Mechanism | Where | Status |
|---|---|---|
| Taxonomy `group6-marketplace-pii`, fine-grained access control activated, tags `pii-contact` and `pii-location-coarse` | [`infra/terraform/governance.tf`](../infra/terraform/governance.tf) | see [evidence](evidence/l10/) |
| Tags attached to `group6_warehouse.shipping_details` | [`scripts/apply_policy_tags.py`](../scripts/apply_policy_tags.py) | see [evidence](evidence/l10/) |
| Fine-grained reader on `pii-contact`: nobody outside a request | `governance.tf`, variable `pii_contact_readers`, empty | |
| Narrowed grant | [`infra/terraform/iam.tf`](../infra/terraform/iam.tf) | see [infra.md](infra.md) |

## Gaps between the matrix and what is enforced

A documented gap is a finding; an undocumented one is a lie.

1. **The second key is given to every student.** The student role includes
   `roles/datacatalog.categoryFineGrainedReader` at project level (measured for
   Benjamin and Lenny). A tag therefore refuses nothing to a student: the matrix
   says "no" to the analyst and to the other groups for `pii.contact`, yet every
   student account gets through. We cannot fix it: project IAM is administered by
   the teaching team, and we cannot even read it.
2. **So is the first key.** The same role grants `bigquery.tables.getData` and
   `storage.objects.get` on the whole project: removing `projectReaders` from our
   datasets removes nothing from a student of another group.
3. **No service account.** dbt, the DAG and ingestion run with the credentials of
   the member who launches them (ADC). The "Pipeline" row of the matrix cannot be
   told apart from "Engineer". We cannot create a service account
   (`iam.serviceAccounts.create` denied).
4. **Bronze is not tagged.** The `group6_bronze` tables are external tables over
   Parquet, not BigLake tables. The same street and phone stay readable there, and
   the `customer` Parquet (name, email, phone) is readable by anyone who reads the
   bucket.
5. **A reload drops the tags.** `warehouse/03_native_load.sql` recreates
   `shipping_details` with `CREATE OR REPLACE`: the table comes back untagged. The
   tagging script must be re-run after any reload (reminder at the top of the SQL
   file).
6. **Free text is not inspected.** `r_desc`, `title`, `raw_event` and the DLQ are
   `unclassified` and not tagged: the matrix reserves them for engineers, but
   nothing enforces it.
7. **Nobody watches reads.** `INFORMATION_SCHEMA.JOBS_BY_PROJECT` answers "who read
   it?" after the fact; the Data Access log is not readable by us
   (`logging.privateLogEntries.list` missing) and no alert exists.
