# NestFlow Django Backend

This backend mirrors the React frontend contract in this repository and is structured into independent Django apps for clean maintenance.

## Apps

- `users`: Custom user model, roles, OTP flows, auth/profile endpoints
- `properties`: Properties, units, payment config, property documents, occupancy/stats
- `tenancies`: Tenant invitations, tenancy lifecycle, tenant self-service endpoints
- `leases`: Lease CRUD, signing, renewals, termination, lease documents
- `payments`: Payment ledger, M-Pesa STK simulation endpoints, receipts, statements, summaries
- `maintenance`: Maintenance request model (used by tenancy endpoints)
- `communications`: Announcements, notices, email logs, templates, reminders

## Quick Start

```bash
cd projects/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Backend API base URL:

- `http://localhost:8000/api`

Django admin:

- `http://localhost:8000/admin`

## Frontend Integration

Your frontend already expects:

```env
REACT_APP_API_BASE_URL=http://localhost:8000/api
```

Set that in the project root `.env` (or `.env.example` copy), then run frontend and backend together.

## Important Notes

- M-Pesa endpoints are implemented in development-safe simulated mode for smooth frontend polling and status transitions.
- All major domain models are registered in Django admin for full visibility and editing.
- Endpoint paths follow the frontend service files (`src/services/*.js`).
# Backend
