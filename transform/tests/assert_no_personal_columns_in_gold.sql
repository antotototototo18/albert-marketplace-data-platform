-- Gold carries no column that identifies a person (docs/data-dictionary.md):
-- no buyer or customer id, no address id, name, street, phone, e-mail, zip or
-- city, no card data and no free review text. The ML team reads gold directly.
-- Checked on the column names BigQuery actually built, not on what the YAML declares.
-- Returns each offending column; 0 rows = pass.
-- Runs after every gold model: {{ ref('fct_daily_demand') }} {{ ref('dim_product') }} {{ ref('dim_date') }} {{ ref('dim_country') }}
select table_name, column_name
from `{{ target.project }}`.`{{ ref('fct_order_items').schema }}`.INFORMATION_SCHEMA.COLUMNS
where regexp_contains(
    lower(column_name),
    r'(^|_)(buyer|customer|c_id|seller_id|address|street|fname|lname|email|phone|zip|city|card|cvv|expiry|billing|session|review_text|r_desc|title)($|_|id)'
)
