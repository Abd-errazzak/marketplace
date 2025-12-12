# Troubleshooting Registration Issues

## Common Registration Errors and Solutions

### Error: "Registration failed" or "Cannot connect to server"

**Cause:** Backend server is not running or MySQL is not connected.

**Solution:**
1. **Start MySQL in XAMPP:**
   - Open XAMPP Control Panel
   - Click "Start" next to MySQL
   - Wait until status shows "Running"

2. **Create the Database:**
   - Open phpMyAdmin: http://localhost/phpmyadmin
   - Click "New" to create a database
   - Name it: `marketplace`
   - Click "Import" tab
   - Choose file: `database/schema.sql`
   - Click "Go"

3. **Start the Backend:**
   ```powershell
   cd backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   
   Or use the startup script:
   ```powershell
   cd backend
   python start_backend.py
   ```

4. **Verify Backend is Running:**
   - Open browser: http://localhost:8000/docs
   - You should see the API documentation

### Error: "Email already registered"

**Cause:** The email address is already in the database.

**Solution:** Use a different email address or delete the existing user from the database.

### Error: "Password must be at least 8 characters long"

**Cause:** Password validation failed.

**Solution:** Use a password with at least 8 characters.

### Error: "Cannot register as admin"

**Cause:** Admin role cannot be selected during registration (security feature).

**Solution:** Register as "buyer" or "seller". Admin accounts must be created manually.

### Error: Database Connection Failed

**Cause:** MySQL is not running or database doesn't exist.

**Solution:**
1. Check XAMPP MySQL is running
2. Verify database exists: `marketplace`
3. Check credentials in `backend/app/core/config.py`:
   - Default: `root` / `password`
   - Update if your MySQL has different credentials

### How to See Detailed Error Messages

1. **Open Browser Developer Tools:**
   - Press F12 in your browser
   - Go to "Console" tab
   - Try registering again
   - Check for red error messages

2. **Check Network Tab:**
   - Press F12 → "Network" tab
   - Try registering
   - Click on the failed request
   - Check "Response" tab for error details

3. **Backend Logs:**
   - Check the terminal where backend is running
   - Look for error messages in red

### Quick Test

Test the registration endpoint directly:

```powershell
$body = @{
    name = "Test User"
    email = "test@example.com"
    password = "test123456"
    role = "seller"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/register" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

If this fails, check the error message for details.

