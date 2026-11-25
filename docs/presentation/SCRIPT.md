# Script — group 6 defence

Ten minutes of pitch, then five minutes of questions. This is the text to say,
word for word, slide by slide. You do not have to learn it by heart: learn
the numbers and the order, and say the rest in your own words.

The same text is in the speaker notes of each slide.

| # | Slide | Who | Time | Ends at |
|---|---|---|---|---|
| 1 | The problem | Colin | 1 min | 1:00 |
| 2 | What we built | Colin | 2 min | 3:00 |
| 3 | Under the hood (shown, not presented) | Colin | a few seconds, inside the 2 min | 3:00 |
| 4 | Decision 1: how we pay for BigQuery | Benjamin | 2 min | 5:00 |
| 5 | Decision 2: who can read personal data | Anthony | 2 min | 7:00 |
| 6 | What went wrong | Antoine | 2 min | 9:00 |
| 7 | What we would do next | Lenny | 1 min | 10:00 |

About 1,250 words: at a calm pace, 9 min 30. Keep that margin.

**Rules for the day**

- One person holds the laptop for the whole pitch. Nobody swaps computers.
- Do not read the slides out loud. The slide shows the numbers; you tell the
  story.
- No live demo. If someone wants to see it running, show the video or a
  screenshot.
- The **handover sentence** ends each part. Say it, then step back.

---

## Slide 1 — The problem · Colin · 1 min

> Good morning. We are group 6, and we built a data platform for Albert's
> Marketplace, an online shop.
>
> When we started, the shop had a few problems.
>
> First, the website and the analysts used the same database, so a big
> analysis could slow down customers at checkout.
>
> Second, nobody agreed on revenue. The old export writes every order twice.
> If you add everything up, you get **39.2 million euros**. The real figure is
> **19.6 million**.
>
> Third, the data science team wanted one simple table: units sold per
> product, per country, per day. No table gave them that.
>
> And on our shared cloud project, anyone could read **200,001** customer
> phone numbers. Nobody had decided that, it just happened.

**Transition** (Colin keeps going): "Here is what we built to fix this."

---

## Slide 2 — What we built · Colin · 2 min

> Here is the platform, from left to right.
>
> **One:** where the data comes from. The shop database, the clicks on the
> website, and an old export of 27 tables.
>
> **Two:** the raw copy. We call it **bronze**. It is the data exactly as it
> arrived, stored as files in Google Cloud Storage. We keep it so we can always
> rebuild everything from it. Two rules apply here: passwords and card numbers
> never get in, and broken click events are put aside in a separate folder
> instead of stopping the pipeline.
>
> **Three:** the clean tables, in BigQuery, Google's database for analysis. A
> tool called **dbt** cleans the data, that's **silver**, and then builds
> **gold**, the tables the business reads. Gold includes the daily table for
> the data science team. This is also where each order is finally counted
> once, so revenue is right.
>
> **Four:** running it. **Airflow** runs the whole pipeline every day.
> **Terraform** describes our cloud setup as code, so we can rebuild it. And
> every column has a label that says how sensitive it is.
>
> Behind each step there is a short written decision. We call it an **ADR**,
> an architecture decision record. We wrote ten. We will not go through all of
> them: we picked two.

---

## Slide 3 — Under the hood · Colin · a few seconds

Not presented. Show it, say one sentence, move on:

> Here is the same pipeline with the real names: buckets, datasets, the daily
> DAG. We can come back to it during the questions.

**Handover:** "Benjamin, the first one: how we pay for BigQuery."

---

## Slide 4 — Decision 1: how we pay for BigQuery · Benjamin · 2 min

> BigQuery can be paid in two ways. Like a **taxi meter**: you pay for the data
> each query reads. Or like a **rent**: you reserve computing power, and you
> pay every hour, used or not.
>
> We chose the meter. And we added a safety limit: any query that would read
> more than **1 GiB**, about one gigabyte, is refused before it runs.
>
> Why the meter? Because our volume is tiny. We estimate we read about
> **0.034 TiB** a month. A TiB is about a thousand gigabytes. The first TiB is
> free every month, so today we pay nothing. Renting only becomes cheaper
> above **258 TiB** a month. We are about **7,600 times** below that.
>
> We looked at two alternatives. Renting without a contract would cost us
> about **31 dollars** a month, because even a tiny query books 50 units of
> computing power for a full minute. A one-year contract costs **1,927
> dollars** a month, paid even at night and on weekends.
>
> What does our choice cost? A meter has no ceiling. Our 1 GiB limit is set in
> our own tools. We could not set it on the whole project, because the project
> belongs to the school and we don't have that right. So a member who forgets
> the setting is not protected.
>
> What would change our mind? Two months above 258 TiB, or one real query
> blocked by the limit. That would mean the data has grown, and we would
> measure again.

**Handover:** "Anthony takes the second decision: who can read what."

---

## Slide 5 — Decision 2: who can read personal data · Anthony · 2 min

> Our data has four sensitive columns: street, phone, city and zip code. They
> all sit in one table, the shipping details.
>
> We decided to protect them by **type of data**, not table by table.
> Concretely, we put a label on each sensitive column. BigQuery calls it a
> **policy tag**. Only people who hold that label's key can read the column.
> And the label follows the column: if a new table gets a phone column, it is
> protected as soon as we label it.
>
> We had two other options. One filtered view per user: but that is one more
> view to maintain for every new use. Or separate **datasets**, which are
> folders of tables, by level of sensitivity: but then the same data is stored
> twice and must stay in sync.
>
> The label is not our only protection. Our cleaning step drops street and
> phone before the business tables, and a test fails if personal data ever
> reaches gold.
>
> Now the costs, honestly. One: when the table is rebuilt, the labels
> disappear, with no error. We have to run a script again each time. Two:
> today the labels **block nobody**. We tested it. The course gives every
> student the key to every label on the project, and we cannot remove it. The
> other options hit the same wall, because the same student access reads every
> table anyway.
>
> What would change our mind: if labels keep getting lost, separate datasets
> are harder to get wrong.

**Handover:** "Not everything went to plan. Antoine."

---

## Slide 6 — What went wrong · Antoine · 2 min

> Two things broke in our daily pipeline.
>
> **First: re-loading past days.** We call it a **back-fill**. We wanted to
> load the 15th and the 16th of September. Before running it, we wrote down our
> prediction: **468** new orders. We got **208**. The 15th was missing.
>
> Why? A test run already existed for the 15th, but it covered the 14th.
> Airflow keeps one run per date, so it reused it and loaded the 14th again.
>
> We deleted that old run and ran again: 468, as predicted. Then we ran it a
> second time: **zero** new rows. That is what we want: running the same day
> twice changes nothing.
>
> **Second: a bad row reached gold.** This one was a drill: we planted one
> duplicate row on purpose. Our first design, the one from the course, built
> all the tables first and tested them after. So for a moment, gold showed
> **10 units and 87 euros 90 too many**. The test caught it, but too late: an
> alarm, not a lock.
>
> We changed it. Now each table is tested right after it is built, and
> everything that depends on a failed test is skipped: 38 steps were skipped.
> Gold kept the right numbers: **1,201 units and 32,802 euros**.
>
> Both lessons are now in our runbook, our incident guide.

**Handover:** "Lenny closes with what we would do next."

---

## Slide 7 — What we would do next · Lenny · 1 min

> Four things are left, in the order we would do them.
>
> **One:** two members can still write to the raw data and the warehouse. The
> fix, read-only access, is already written in Terraform. We just need their
> OK and to apply it.
>
> **Two:** prove the labels really block someone, using an account outside
> the student role.
>
> **Three:** handle deletions. Today, if a line is deleted in the shop, it
> stays in our copy.
>
> **Four:** get the admin rights we lack: a query limit on the whole project,
> a robot account for our programs, called a service account, and a budget
> alert.
>
> That's our platform. Thank you, we are happy to take your questions.

On "Thank you", move to slide 8, the thank-you slide, and stay there during
the questions. The backup slides come right after it.

---

## Questions: who answers, and what to say

One person answers. The others add something only if it is useful. Each
answer below is short on purpose: give it, then stop.

### Announced by the course

**"What happens if the same day runs twice?"** — Antoine, then Benjamin

> Nothing changes. Each step that writes is safe to repeat. Files are named by
> date, so a rerun overwrites its own file. Loads use a MERGE on the order
> number: an order already there is updated, never added twice. Gold is
> rebuilt from scratch each time. Proof: our second back-fill added zero rows.
> One limit: if an order is deleted in the shop, we never delete it.

Source: ADR-0007, `docs/orchestration.md`.

**"Who can read your Terraform state bucket? What if someone deletes the
state file?"** — Lenny, then Benjamin

> The state file is Terraform's memory of what it created. Today, the
> project's owners, editors and viewers can read the bucket, by default, so
> not only our five members. It can hold sensitive values, so it lives in its
> own bucket, separate from the data.
>
> If someone deletes it: we stop. We never run Terraform on an empty state,
> because it would try to create things that already exist. The bucket keeps
> old versions, so we restore the last good one. If there is none, we
> re-import each resource by hand. Deleting the state does not delete our
> resources: it only loses the link between them and the code.

Source: ADR-0008.

**"Show me your data classification and your access matrix."** — Benjamin,
then Anthony

> Open `docs/governance.md`: every column has a class, an owner and a reason,
> and the access matrix says which role can read which class, with a way to ask
> for each "no". The labels themselves are in `infra/terraform/governance.tf`.

### Likely, because the teacher gave them as examples

**"Why that partition key?"** — Benjamin

> Orders are split by month of order date. A query on one day reads 78 times
> less data, a query on the last 28 days 27 times less. We tested splitting by
> day: only 4% better on our 12-month query, but 1,096 tiny pieces, and 42
> times more computing time. Nobody reads a single day, so we kept months.

Source: `docs/warehouse-tuning.md`.

**"Why views in silver and tables in gold?"** — Antoine

> A view is a saved query: it stores nothing and is always up to date. Silver
> is read only by dbt, so a view avoids keeping a second copy. The price: each
> read recomputes it from bronze, and we watch that cost. Gold is read often,
> so we store it as tables and pay the computing once per build. We would
> change if a full build took more than an hour or came close to our 1 GiB
> limit: then we would update gold bit by bit instead of rebuilding it.

Source: ADR-0005.

**"How do you tag your Docker images?"** — Lenny

> A Docker image is a packaged program. Our tag is the date and the step plus a
> number, for example `20261103T-step6-01`, and we never reuse one. We also
> record the digest, a fingerprint of the exact image. Honest limit: the
> registry allows reusing a tag, so "never reuse" is a team rule, not
> something the system enforces.

Source: ADR-0006.

### Other questions we could get

**"Why store bronze as Parquet, all in text?"** — Antoine

> Parquet is a compressed column format. 62 MB instead of 206 MB of CSV. We
> measured the compression: zstd 2.58 times, snappy 1.42 times. Everything
> stays as text so bronze is exactly what we received, checked cell by cell.
> Silver sets the types.

Source: ADR-0002.

**"How do you erase a customer who asks for it (GDPR)?"** — Anthony

> We have a runbook and a script, and we tested them on a real buyer on
> 20 November: 1,419 rows removed from 54 raw files, 13 tables cleaned, gold
> rebuilt, zero rows left in the group's data. Three limits, all written down:
> the cloud can still restore the old data for 7 days; personal test folders
> of members are not covered; and reloading from the original export would
> bring the person back.

Source: `docs/runbooks/erasure.md`.

**"How do you know who pays for what?"** — Anthony

> Every resource carries four labels: team, environment, pipeline, component.
> We could not read the billing export, and the budget alert is written but
> switched off: the API it needs is disabled on the school project.

Source: ADR-0009, `docs/costs.md`.

**"What does your click stream guarantee?"** — Anthony

> At least once: an event is never lost, but it can arrive twice, so the
> next layer has to handle duplicates. A broken event goes to a separate folder, the
> dead-letter queue, and the stream keeps going.

Source: ADR-0003.

**"Why two tiers? Why not only BigQuery?"** — Colin, then Anthony

> The course asked for files in Cloud Storage and a BigQuery warehouse. Files
> are cheap and can be replayed: if we break a table, we rebuild it from
> bronze. BigQuery is where people query.

Source: ADR-0001.

### When you don't know

Say it like this:

> "I don't know, Benjamin wrote that one. What I can tell you is why we needed
> it: … Benjamin can tell you why he chose that approach."

Honest, gives what you know, points to who knows. A confident wrong answer is
the hardest thing to recover from: the next question will be on the same
subject.

---

## Glossary

| Word | Meaning |
|---|---|
| ADR | Architecture decision record: one page per technical choice, with the options and the reasons. |
| Back-fill | Re-running the pipeline for past days. |
| BigQuery | Google's database for analysis. You pay for the data each query reads. |
| Bronze | Raw copy of the data, exactly as it arrived. |
| DAG | The list of steps Airflow runs, in order. |
| Dataset | A folder of tables in BigQuery. |
| dbt | Tool that builds tables with SQL and tests them. |
| DLQ | Dead-letter queue: the folder where broken events wait. |
| GCS | Google Cloud Storage, where our raw files live. |
| GDPR | General Data Protection Regulation, the EU law on personal data. It includes the right to be erased. |
| GiB / TiB | About one gigabyte / about a thousand gigabytes. |
| Gold | Tables the business and the data scientists read. |
| Idempotent | Running it twice gives the same result as running it once. |
| IAM | Identity and access management: who has which rights in the cloud. |
| MERGE | SQL command that updates a row if it exists and inserts it if not. |
| ML | Machine learning, here the data science team. |
| Parquet | A compressed file format, stored column by column. |
| PII | Personally identifiable information: personal data. |
| Policy tag | A label on a column that decides who can read it. |
| Runbook | Step-by-step guide for an incident. |
| Service account | A robot account, used by programs instead of a person. |
| Silver | Cleaned data: types fixed, duplicates removed. |
| Slot | A unit of computing power in BigQuery. |
| SQL | The language used to query databases. |
| Terraform | Tool that writes the cloud setup as code, so it can be rebuilt. |
