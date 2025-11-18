# AI-powered-barista-BE

Backend for the AI-powered barista. The app is built with FastAPI, SQLAlchemy, and JWT-based authentication, and exposes auth, admin, and self-service profile endpoints under `app/api/routes`.

## TODO
- Add Alembic migrations for `User`, `Order`, and `Preference` models.
- Cover auth flows with unit tests (signup duplicate email, login success/failure, `/me` protection, admin role management access).
- Flesh out cookie/session handling (HttpOnly/secure flags) once frontend/environment requirements are known.
- Create a developer seed script that can bootstrap an initial ADMIN user for local work.
- Add assertions/tests for service-layer logic and ensure admin endpoints are only actionable by ADMIN roles.
