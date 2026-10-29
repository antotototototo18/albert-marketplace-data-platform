-- Q2 (ML team, flow A8): units per product, country and day over the last 28 days,
-- the grain of fct_daily_demand (docs/model/star-daily-demand.md).
-- The country is the buyer's current default address: a proxy, not the historical one.
-- is_default = 1 is applied before the join so that an order is not multiplied by
-- every address of its buyer.
SELECT
  i.p_id,
  d.country,
  i.order_date,
  SUM(i.qty) AS units_sold
FROM `${order_items}` AS i
JOIN `${orders}` AS o
  ON o.order_id = i.order_id
JOIN (
  SELECT c_id, address_id FROM `${customer_shipping}` WHERE is_default = 1
) AS s
  ON s.c_id = o.buyer_id
JOIN `${shipping_details}` AS d
  ON d.address_id = s.address_id
WHERE i.order_date > DATE_SUB(DATE '2026-09-14', INTERVAL 28 DAY)
  AND o.order_date > DATE_SUB(DATE '2026-09-14', INTERVAL 28 DAY)
GROUP BY i.p_id, d.country, i.order_date;
