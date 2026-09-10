# dbt — SPA Analytics

dbt project powering the transformation layer of the modern data platform. It reads the **STAGING** schemas in Snowflake, builds a dimensional **WAREHOUSE** layer, and exposes business-ready **MART** aggregates — with automated data tests on every release.

## Layers

| Layer | Location | Contents |
|---|---|---|
| Staging | `models/staging/` | Source declarations (`sources.yml`) over `SPA_ANALYTICS.STAGING` tables with primary-key tests |
| Warehouse | `models/warehouse/` | Dimensions + facts (materialized as tables) |
| Mart | `models/mart/` | Analytics-ready business aggregates (materialized as tables in the `MART` schema) |

## Models

### Warehouse (dimensional core)

- `dim_date` — date spine (`2020-01-01` + 3650 days) with year/month/day/quarter attributes
- `dim_customer` — deduplicated customers (by phone), enriched with membership info
- `dim_product` — spa products
- `dim_treatment` — treatment catalogue
- `fact_transactions` — transactional grain: gross/net amounts, discount, source
- `fact_completed_items` — items completed per transaction
- `fact_treatment_activities` — one row per scheduled treatment appointment

Stable surrogate keys (`MD5(<natural_key>)`) are used throughout so facts can join dimensions safely over time.

### Mart (business ready)

- `mart_revenue_daily` — daily revenue by source (transactions, gross, discount, net, AOV)
- `mart_customer_analytics` — customer profile + lifetime value and recency
- `mart_operations_booking` — booking/operations performance
- `mart_product_analytics` — product-level sales performance
- `mart_treatment_analytics` — treatment-level utilization and revenue

## Data Tests

- Every surrogate and natural key is tested for `not_null` + `unique`.
- Business enums (e.g. booking status) are constrained with `accepted_values`.
- The suite currently runs **72/72 passing**.

## Setup

Configure a Snowflake profile named `dbt` (project name and profile are both `dbt`):

```yaml
# ~/.dbt/profiles.yml
dbt:
  outputs:
    dev:
      type: snowflake
      account: <account_identifier>
      user: <user>
      password: <password>
      role: <role>
      database: SPA_ANALYTICS
      warehouse: SPA_WH
      schema: WAREHOUSE
      threads: 4
  target: dev
```

Run:

```bash
dbt deps
dbt run      # builds warehouse + mart tables
dbt test     # 72+ data tests
```

## Lineage

```text
STAGING (Snowflake)
     │  sources.yml
     ▼
warehouse/  dim_date, dim_customer, dim_product, dim_treatment
     │       fact_transactions, fact_completed_items, fact_treatment_activities
     ▼
mart/       mart_revenue_daily, mart_customer_analytics, mart_operations_booking,
            mart_product_analytics, mart_treatment_analytics
     ▼
     Power BI / Streamlit
```