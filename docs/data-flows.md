# Data flows

One row per flow: where the data comes from, what it is, who uses it, how often
it moves, and in which format.


| # | Source                     | Data                                                                        | Consumer               | Frequency               | Format                | Notes                                                    |
| - | -------------------------- | --------------------------------------------------------------------------- | ---------------------- | ----------------------- | --------------------- | -------------------------------------------------------- |
| 1 | Customers & sellers        | Orders, sign-ups (passwords), saved card details, reviews, product listings | Web shop               | Real time               | Web forms / JSON      | Entry point for all personal and payment data            |
| 2 | Web shop                   | Everything from flow 1                                                      | PostgreSQL (25 tables) | Real time               | SQL inserts / updates | The single operational database                          |
| 3 | PostgreSQL                 | Products, orders, accounts needed to render pages                           | Web shop               | Real time               | SQL queries           | Customer-facing reads; latency matters here              |
| 4 | PostgreSQL                 | Any table, including the ones checkout writes to                            | Analysts               | Ad hoc, whenever needed | Direct SQL            | Analytical queries hit the production database           |
| 5 | PostgreSQL                 | Dump of the tables                                                          | Nightly CSV export     | Daily (night)           | CSV files             | Reads from production; no filtering of sensitive columns |
| 6 | Nightly CSV export         | Same data as of last night                                                  | Spreadsheets           | Daily, opened by hand   | CSV → Excel          | Files end up on laptops; edited by hand                  |
| 7 | Analyst SQL + spreadsheets | Revenue figures                                                             | Reports                | When someone asks       | Spreadsheets          | Each report computes revenue its own way                 |
| 8 | *Nothing yet*              | Units sold per product, per country, per day                                | ML team                | Daily (requested)       | A table               | Requested, not built; the gold table we will build       |

## Under the matrix, answer

- **Which flows carry personal data?**
  Flows 1 to 6. They carry customer names, emails, addresses, passwords and
  saved card details. Flows 1 to 3 need it to run the shop. Flows 4 to 6 do not:
  analysts can query those tables directly, and the nightly CSV can copy them onto
  laptops. Flows 7 and 8 are aggregates and carry no personal data.
- **Which consumers read directly from a system that also serves customers?**
  The analysts (flow 4) and the nightly CSV export (flow 5). Both read the same
  PostgreSQL database that checkout writes to, so a heavy query or export can slow
  down or block customers trying to pay. The spreadsheets and reports (flows 6
  and 7) depend on that database indirectly.
- **Where could the same figure be computed twice, in two different ways?**
  Revenue. It is computed once from live SQL (flows 4 → 7) and again from last
  night's CSV after hand edits in spreadsheets (flows 6 → 7). The two differ in
  timing and in whether tax, refunds and cancelled orders are counted, which is why
  the reports disagree. Units sold is the next risk: if the ML table (flow 8) and
  the sales reports each define it separately (for example, whether pending or
  cancelled orders count), the two will drift apart.
