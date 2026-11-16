# Expenses Dashboard API

`GET /api/v1/families/{family_pk}/expenses/dashboard/?month=YYYY-MM-01`

Every monetary value is a fixed two-decimal string. `forecast` is explicitly a
plan derived from applicable `ExpenseForecast` records; it is never a confirmed
movement. `confirmed` contains only effective confirmed expense movements for
the requested month. Corrected originals and their reversal records are omitted
so the replacement is counted once.

`ADMIN` receives the household view, including the effective monthly budget and
its lines. `MEMBER` receives only own-private and shared records;
`budget_utilization` is `null` because budget lines have neither ownership nor
allocations, so attributing or revealing them would violate privacy.

`responsibility.items` contains only persisted complete shared forecast
allocations and private forecast ownership. It never infers a split. If a shared
forecast lacks allocations summing exactly to its amount,
`responsibility.setup_required` is `true` and that forecast is omitted from the
breakdown. The dashboard has no materialization behavior: `upcoming_obligations`
contains only already-persisted, visible pending expense obligations.
