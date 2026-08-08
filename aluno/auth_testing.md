## AUTH-GATED APP TESTING PLAYBOOK

### 1. Create Test Session in Mongo
```
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({user_id: userId, email: 'qa+'+Date.now()+'@sapiens.app', name: 'QA User', created_at: new Date()});
db.user_sessions.insertOne({user_id: userId, session_token: sessionToken, expires_at: new Date(Date.now()+7*24*60*60*1000), created_at: new Date()});
print(sessionToken);"
```

### 2. Call `/api/auth/me` with `Authorization: Bearer <token>` OR set the `session_token` cookie.

### 3. For UI, use Playwright `context.add_cookies` with the same value (path=/, httpOnly, secure, sameSite None).

### Checklist
- `user_id` on user and session must match exactly.
- Queries must project `{"_id": 0}` to exclude Mongo `_id`.
- Backend returns 401 (not 500) when unauthenticated.
- Session expiry compares timezone-aware datetimes.
