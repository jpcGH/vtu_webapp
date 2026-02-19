# VTU Platform (Django)

Production-ready Django starter for a retail VTU platform with split settings, PostgreSQL-ready deployment, and modular app architecture.

## Stack
- Django 4+/5+
- django-environ for environment-driven config
- WhiteNoise for static assets
- PostgreSQL (production) + SQLite fallback (development)

## Project Layout
```text
vtu_platform/
  config/
    settings/{base,dev,prod}.py
  apps/
    accounts/    # auth profile + referrals linkage
    ledger/      # wallet + immutable ledger rules
    payments/    # Monnify integration stubs + webhooks
    vtu/         # airtime/data/bills provider abstraction
    referrals/   # one-level referral bonus services
    dashboard/   # staff-only operations console
    core/        # landing pages, shared context + settings
  templates/
  static/
```

## Quick Start (Dev)
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Prepare environment file:
   ```bash
   cp .env.example .env
   ```
3. Run migrations and create admin user:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. Start server:
   ```bash
   python manage.py runserver
   ```

## Production Notes
1. Set `DJANGO_SETTINGS_MODULE=config.settings.prod`.
2. Use PostgreSQL via `DATABASE_URL`.
3. Ensure `DEBUG=False` and restrict `ALLOWED_HOSTS`.
4. Run static collection:
   ```bash
   python manage.py collectstatic --noinput
   ```
5. Use Gunicorn/Uvicorn behind Nginx or Caddy. Example:
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:8000
   ```
6. Persist `logs/` directory for file logs.

## Security in `prod.py`
- HSTS, secure cookies, SSL redirect, referrer and frame protection.
- WhiteNoise compressed manifest static storage for deterministic assets.

## Business Modules
- **Ledger:** `LedgerEntry` cannot be updated after insert. All value movement should occur via `LedgerEntry.post_entry(...)`.
- **Payments:** includes Monnify webhook endpoint (`/payments/webhooks/monnify/`) and event persistence model.
- **VTU Engine:** provider abstraction with sample `StubProvider` for integration testing.
- **Referrals:** one-level referral bonus helper that credits referrer wallet using ledger entries.

## Deployment Checklist
- [ ] Rotate strong `DJANGO_SECRET_KEY`
- [ ] Configure PostgreSQL backups
- [ ] Wire Monnify credentials and signature verification
- [ ] Configure Sentry/APM and external centralized logging
- [ ] Set up CI (lint/test/migrate checks)

## VTpass Setup
1. Enable provider:
   ```bash
   export VTU_PROVIDER=vtpass
   ```
2. Configure VTpass credentials:
   ```bash
   export VTPASS_BASE_URL="https://sandbox.vtpass.com"
   export VTPASS_API_KEY="your-api-key"
   export VTPASS_USERNAME="your-username"
   export VTPASS_PASSWORD="your-password"
   ```
3. In production (`config.settings.prod`), these values are validated and Django raises a clear configuration error if any required key is missing.
4. Sync data plans from VTpass when supported:
   ```bash
   python manage.py sync_data_bundles --service-id mtn-data --provider-slug vtpass
   ```
   If VTpass returns no plans for a service, manage plans manually through the Django admin `DataBundlePlan` model.
5. Pending transactions are re-verified via background tasks (`verify_pending_purchase` / `sweep_pending_purchases`) and failed final verifications trigger wallet reversal automatically.
