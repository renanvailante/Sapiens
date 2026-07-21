# Auth Testing Playbook - Sapiens Dashboard

## Admin credentials (seeded)
- email: admin@sapiens.edu
- password: admin123

## Endpoints
- POST /api/auth/login { email, password } -> sets httpOnly cookies + returns user
- GET /api/auth/me -> returns user via cookie or Authorization Bearer
- POST /api/auth/logout -> clears cookies
- POST /api/auth/register { email, password, name } -> creates user + logs in

## Quick curl test
```
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sapiens.edu","password":"admin123"}'
curl -b cookies.txt http://localhost:8001/api/auth/me
```

## Mongo verification
```
mongosh
use sapiens_dashboard
db.users.findOne({role: "admin"})
db.imports.find({}).count()
```
