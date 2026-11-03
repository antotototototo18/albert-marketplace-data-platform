-- Drops unnamed_0: the export's row index.
-- Maps country names to ISO 3166-1 alpha-2 codes, the key of dim_country. A name
-- outside the six observed becomes NULL and fails the accepted_values test.
-- Drops street_address and phone: direct personal data that no model reads
-- (docs/data-dictionary.md). city and zip are quasi-identifiers, also unused: dropped.
-- Casts address_id to INT64.
select
    cast(address_id as int64) as address_id,
    state,
    country                   as country_name,
    case country
        when 'Germany'     then 'DE'
        when 'France'      then 'FR'
        when 'Italy'       then 'IT'
        when 'Spain'       then 'ES'
        when 'Netherlands' then 'NL'
        when 'Belgium'     then 'BE'
    end                       as country_code
from {{ source('bronze_legacy', 'shipping_details') }}
