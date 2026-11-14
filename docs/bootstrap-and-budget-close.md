# Bootstrap And Budget Close

## First Family Bootstrap

Run the management command once after migrations to create the Jalberth account, the family, and Jalberth's active administrator membership. It creates no forecasts, balances, goals, or confirmed movements.

```sh
python manage.py bootstrap_family --email jalberth@example.com --family-name "Mosquera Alves"
```

The command prompts for the password. For non-interactive automation, pass `--password` and `--noinput`; protect process arguments and command history. Bootstrap rejects execution once a family, the `jalberth` username, or the supplied email already exists.

An equivalent API is `POST /api/v1/admin/family-bootstrap/`. It requires a Django staff user and accepts `email`, `password`, and `family_name`. Use this only from a controlled administrator session. Both paths record an immutable `family.bootstrap_created` audit event.

Configure planning values only afterward through the administrator-controlled initial forecast configuration flow.

Before that flow can save its mandatory Cigarettes forecast, ensure both family members have active memberships. The provided template uses their member IDs to create the two required 93.00 EUR shared allocations. Account provisioning and membership creation remain controlled administrator operations; do not enter credentials or real movements in fixtures.

## Monthly Close

A family administrator closes the latest version of a monthly forecast with:

```text
POST /api/v1/families/{family_id}/budget-forecasts/{forecast_id}/close/
```

Closing stores an immutable snapshot of that forecast and its lines and records `budget_month.closed`. Ordinary forecast or line creation for that month, including the initial forecast configuration flow, is rejected after close.

## Historical Corrections

Never edit a closed forecast. A family administrator must create a replacement version and provide the complete corrected set of lines:

```text
POST /api/v1/families/{family_id}/budget-forecasts/{forecast_id}/historical-corrections/
{
  "reason": "Corrected the January receipt",
  "lines": [{"name": "Living", "amount": "110.00", "kind": "STANDARD"}]
}
```

The target must be the latest forecast version for an already closed month. The original version and original close snapshot remain unchanged. The new version and correction reason are preserved in the immutable `budget_forecast.historically_corrected` audit event.
