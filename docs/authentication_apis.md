
# Authentication Feature APIs

## 🔑 Auth Routes

---

### **Login**

#### `POST /login`  
_Authenticate and return tokens. Also, handle MFA challenge if enabled._

<details>
<summary><strong>MFA Disabled</strong></summary>

- **Permissions:** None

### Request:
```json
{
  "user_identity": "<user email>",
  "password": "<password>"
}
```
### Return 

**200 Response:**
```json
{
  "access_token": "<access_token>"
}
```
**Headers:**
```
Set-Cookie: refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires="datetime"; secure; HttpOnly; SameSite=Strict
```

**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```
</details>

<details>
<summary><strong>MFA Enabled</strong></summary>

#### First Request _(checking credentials)_

- **Permissions:** None

### Request:
```json
{
  "user_identity": "<user email>",
  "password": "<password>"
}
```

### Return:
**200 Response:**
```json
{
  "mfa_required": true
}
```
**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```

---

#### Second Request _(MFA challenge)_

- **Permissions:** None

### Request:
```json
{
  "user_identity": "<user email>",
  "password": "<user password>",
  "token": "<totp token>"
}
```

### Return:
**200 Response:**
```json
{
  "success": "<bool>",
  "access_token": "<access_token>"
}
```
**Headers:**
```
Set-Cookie: refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires="datetime"; secure; HttpOnly; SameSite=Strict
```

**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```
</details>

---

### **Token Refresh**

#### `POST /token/refresh`  
_Retrieve new access token using refresh token._

- **Permissions:** None

### Request:
**Headers:**
```
Cookie:refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires=”datetime”; secure; HttpOnly; SameSite=Strict
```
### Return:
**200 Response:**
```json
{
  "success": true,
  "access_token": "<access_token>"
}
```
**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```

---

### **Logout**

#### `POST /logout`  
_Invalidate session or refresh tokens._

- **Permissions:** None

### Request: 
**Headers:**
```
Cookie:refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires=”datetime”; secure; HttpOnly; SameSite=Strict
```
### Return:
**200 Response:**

**Headers:**
```
Set-Cookie: refresh-token=; Max-Age=0; Path=/api/auth/; expires="datetime"
```
**Payload:**
```json
{
  "success": true
}
```
**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```

---

### **Change Password**

#### `POST /users/me/password`  
_Change password for authenticated user._

- **Permissions:** Authenticated user

### Request: 

**Headers:**
```
Authorization: Bearer <access_token>

Cookie:refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires=”datetime”; secure; HttpOnly; SameSite=Strict
```
**Payload:**
```json
{
  "current_password": "<current user password>",
  "new_password": "<new password>"
}
```
### Return:
**200 Response:**
```json
{
  "success": true,
  "message": "<message>"
}
```
**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```

---

### **Revoke Other Tokens**

#### `DELETE /users/me/tokens/others`  
_Revoke all refresh tokens except the current session’s._

- **Permissions:** Authenticated user

### Request: 
**Headers:**
```
Authorization: Bearer <access_token>

Cookie:refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires=”datetime”; secure; HttpOnly; SameSite=Strict
```
**Payload:**
```json
{
  "password": "<user password>"
}
```
### Return:
**200 Response:**
```json
{
  "success": true
}
```
**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```

---

## 🔐 Multifactor Authentication (MFA) Routes

---

### **Setup TOTP**

#### `POST /mfa/app/setup`  
_Retrieve QR code and secret for TOTP setup._

- **Permissions:** Authenticated user

### Request:
**Headers:**
```
Authorization: Bearer <access_token>

Cookie:refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires=”datetime”; secure; HttpOnly; SameSite=Strict
```
**Payload:**
```json
{
  "method_type": "TOTP"
}
```

### Return:
**200 Response:**
```json
{
  "secret": "<mfa_secret>",
  "qr_code": "<Base64-encoded SVG string>"
}
```
**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```

---

### **Verify TOTP**

#### `POST /mfa/app/verify`  
_Verify TOTP code during MFA setup._

- **Permissions:** Authenticated user

### Request: 
**Headers:**
```
Authorization: Bearer <access_token>

Cookie:refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires=”datetime”; secure; HttpOnly; SameSite=Strict
```

**Payload:**
```json
{
  "token": "<token>",
  "setup_key": "<secret key generated by the endpoint>"
}
```
### Return:
**200 Response:**
```json
{
  "success": true
}
```
**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```

---

### **List MFA Methods**

#### `GET /mfa/methods`  
_List all active MFA methods._

- **Permissions:** Authenticated user

### Request: 
**Headers:**
```
Authorization: Bearer <access_token>

Cookie:refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires=”datetime”; secure; HttpOnly; SameSite=Strict
```
### Return:
**200 Response:**
```json
{
  "mfa_methods": [ /* list of methods */ ]
}
```
**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```

---

### **Disable MFA**

#### `POST /mfa/app/disable`  
_Disable the current MFA method._

- **Permissions:** Authenticated user

### Request: 
**Headers:**
```
Authorization: Bearer <access_token>

Cookie:refresh-token={project_prefix}{machine_identifier}; Max-Age={timestamp in s}; Path=/api/auth/; 
expires=”datetime”; secure; HttpOnly; SameSite=Strict
```

**Payload:**
```json
{
  "method_type": "TOTP"
}
```
### Return:
**200 Response:**
```json
{
  "success": true
}
```
**Error Response (400, 401, 403, 500):**
```json
{
  "message": "<i18n translationKey for generic error message>"
}
```

---

## 📖 Glossary

- `< >`: required param  
- `[ ]`: optional param (can be null)

---
