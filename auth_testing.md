# Auth-Gated App Testing Playbook

## Step 1: Create Test User & Session
```bash
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  company_id: null,
  role: null,
  created_at: new Date(),
  updated_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Create Test User WITH Company
```bash
mongosh --eval "
use('test_database');
var userId = 'test-admin-' + Date.now();
var companyId = 'comp_' + Date.now();
var sessionToken = 'test_admin_session_' + Date.now();
db.companies.insertOne({
  company_id: companyId,
  name: 'Test Company',
  subscription_status: 'trial',
  subscription_plan: null,
  created_at: new Date(),
  updated_at: new Date()
});
db.users.insertOne({
  user_id: userId,
  email: 'admin.' + Date.now() + '@example.com',
  name: 'Test Admin',
  picture: 'https://via.placeholder.com/150',
  company_id: companyId,
  role: 'company_admin',
  created_at: new Date(),
  updated_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
print('Company ID: ' + companyId);
"
```

## Step 3: Test Backend API
```bash
curl -X GET "$BACKEND_URL/api/auth/me" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
curl -X GET "$BACKEND_URL/api/properties" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
curl -X POST "$BACKEND_URL/api/seed-demo-data" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Step 4: Browser Testing
```python
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "your-app.com",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None"
}]);
await page.goto("https://your-app.com/dashboard");
```

## Checklist
- User document has user_id field
- Session user_id matches user's user_id exactly
- All queries use {"_id": 0} projection
- API returns user data (not 401/404)
- Dashboard loads without redirect to login
