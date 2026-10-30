# IAM Module — Authentication & User Management Architecture

## Overview

The Identity and Access Management (IAM) module provides enterprise-grade
authentication, authorization, user management, and security for the AI Video
Studio platform. It follows Clean Architecture with strict layer separation.

---

## Authentication Flow Diagram

```
Client                AuthMiddleware          AuthenticationService         Database
  │                       │                        │                        │
  │  POST /auth/login     │                        │                        │
  ├──────────────────────►│                        │                        │
  │  (public path —       │                        │                        │
  │   middleware skips)   │                        │                        │
  │                       │                        │                        │
  │  email + password     │                        │                        │
  ├──────────────────────────────────────────────►│                        │
  │                       │                        │  get_by_email()        │
  │                       │                        ├───────────────────────►│
  │                       │                        │  User entity           │
  │                       │                        │◄───────────────────────┤
  │                       │                        │                        │
  │                       │                        │  verify_password()     │
  │                       │                        │  create_token_pair()   │
  │                       │                        │  create session        │
  │                       │                        │  update last_login     │
  │                       │                        ├───────────────────────►│
  │                       │                        │                        │
  │  AuthResponse         │                        │                        │
  │  (access + refresh)   │                        │                        │
  │◄──────────────────────────────────────────────┤                        │
  │                       │                        │                        │
  │  GET /users/me        │                        │                        │
  │  Authorization:       │                        │                        │
  │  Bearer <access>      │                        │                        │
  ├──────────────────────►│                        │                        │
  │                       │  decode_access_token() │                        │
  │                       │  set request.state.user│                        │
  │                       │───────────────────────►│                        │
  │                       │                        │  get_by_id()           │
  │                       │                        ├───────────────────────►│
  │                       │                        │  UserResponse          │
  │                       │                        │◄───────────────────────┤
  │  UserResponse         │                        │                        │
  │◄──────────────────────┤                        │                        │
```

---

## RBAC Diagram

```
┌──────────────────────────────────────────────────────────┐
│                     RBAC Hierarchy                       │
│                                                          │
│  ┌────────┐    ┌──────────────┐    ┌────────────┐       │
│  │  User  │───►│  UserRoles   │───►│   Role     │       │
│  │        │    │  (M:N link)  │    │            │       │
│  └────────┘    └──────────────┘    └─────┬──────┘       │
│                                          │               │
│                                          │               │
│                              ┌───────────▼──────────┐    │
│                              │  RolePermissions     │    │
│                              │  (M:N link)          │    │
│                              └───────────┬──────────┘    │
│                                          │               │
│                              ┌───────────▼──────────┐    │
│                              │    Permission        │    │
│                              │  (e.g. project.create)│   │
│                              └──────────────────────┘    │
└──────────────────────────────────────────────────────────┘

Default Roles:
┌──────────────┬─────────────────────────────────────────────┐
│ Role         │ Permissions                                 │
├──────────────┼─────────────────────────────────────────────┤
│ super_admin  │ ALL permissions                             │
│ admin        │ project.*, user.read, user.update,          │
│              │ settings.update, analytics.view,            │
│              │ api_key.manage, audit.view                  │
│ creator      │ project.*, video.*, analytics.view,         │
│              │ api_key.manage                              │
│ viewer       │ project.read, analytics.view                │
└──────────────┴─────────────────────────────────────────────┘
```

---

## JWT Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    JWT Token Lifecycle                      │
│                                                             │
│  1. LOGIN                                                   │
│     ┌────────┐    access_token (30 min)                     │
│     │ Client │─── refresh_token (7 days, or 30 if remember) │
│     └────┬───┘    session created in DB                     │
│          │                                                  │
│  2. API CALL                                                │
│          │  Authorization: Bearer <access_token>            │
│          ├─────────────► AuthMiddleware validates            │
│          │               Sets request.state.user             │
│          │                                                  │
│  3. TOKEN EXPIRED                                           │
│          │  POST /auth/refresh                              │
│          │  { refresh_token: "..." }                        │
│          ├─────────────► Old refresh token REVOKED           │
│          │               New token pair issued (ROTATION)   │
│          │◄──────────── New access + refresh tokens          │
│          │                                                  │
│  4. LOGOUT                                                  │
│          │  POST /auth/logout                               │
│          ├─────────────► Session revoked                    │
│          │               Refresh token revoked              │
│          │◄──────────── "Successfully logged out"           │
│          │                                                  │
│  5. LOGOUT ALL                                              │
│          │  POST /auth/logout-all                           │
│          ├─────────────► ALL sessions revoked               │
│          │               ALL refresh tokens revoked         │
│          │◄──────────── "Revoked N session(s)"              │
└─────────────────────────────────────────────────────────────┘
```

---

## Entity Relationship Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│     users       │     │    user_roles    │     │     roles       │
├─────────────────┤     ├──────────────────┤     ├─────────────────┤
│ id (PK)         │────►│ user_id (FK)     │────►│ id (PK)         │
│ email           │     │ role_id (FK)     │◄────│ name            │
│ username        │     │ created_at       │     │ description     │
│ hashed_password │     └──────────────────┘     │ is_system       │
│ first_name      │                              │ created_at      │
│ last_name       │                              │ updated_at      │
│ profile_image   │                              │ is_deleted      │
│ phone           │                              └────────┬────────┘
│ status          │                                       │
│ auth_provider   │                              ┌────────▼────────┐
│ timezone        │                              │ role_permissions│
│ language        │                              ├─────────────────┤
│ email_verified  │                              │ role_id (FK)    │
│ two_factor      │                              │ permission_id   │
│ last_login_at   │                              │ created_at      │
│ created_at      │                              └────────┬────────┘
│ updated_at      │                                       │
│ is_deleted      │                              ┌────────▼────────┐
│ deleted_at      │                              │   permissions   │
└────────┬────────┘                              ├─────────────────┤
         │                                       │ id (PK)         │
         │                                       │ name            │
         │                                       │ description     │
         │                                       │ resource        │
         │                                       │ action          │
         │                                       │ is_system       │
         │                                       │ created_at      │
         │                                       └─────────────────┘
         │
         ├──────────────────────────────────────────────────────┐
         │                                                      │
┌────────▼────────┐                              ┌──────────────▼──────┐
│ refresh_tokens  │                              │   user_sessions     │
├─────────────────┤                              ├─────────────────────┤
│ id (PK)         │───── session_id ────────────►│ id (PK)             │
│ user_id (FK)    │                              │ user_id (FK)        │
│ token_hash      │                              │ token_jti           │
│ session_id (FK) │                              │ refresh_token_id    │
│ expires_at      │                              │ device              │
│ revoked         │                              │ browser             │
│ revoked_at      │                              │ operating_system    │
│ created_at      │                              │ ip_address          │
└─────────────────┘                              │ user_agent          │
                                                 │ status              │
┌─────────────────┐                              │ created_at          │
│   api_keys      │                              │ last_activity_at    │
├─────────────────┤                              │ expires_at          │
│ id (PK)         │                              └─────────────────────┘
│ user_id (FK)    │
│ name            │                              ┌─────────────────────┐
│ key_hash        │                              │ user_preferences    │
│ key_prefix      │                              ├─────────────────────┤
│ status          │                              │ user_id (PK, FK)    │
│ scopes          │                              │ theme               │
│ expires_at      │                              │ language            │
│ last_used_at    │                              │ default_ai_model    │
│ created_at      │                              │ preferred_llm       │
│ updated_at      │                              │ preferred_voice     │
│ is_deleted      │                              │ preferred_image_*   │
└─────────────────┘                              │ preferred_video_*   │
                                                 │ email_notifications │
┌──────────────────────┐                         │ push_notifications  │
│ password_reset_tokens│                         │ updated_at          │
├──────────────────────┤                         └─────────────────────┘
│ id (PK)              │
│ user_id (FK)         │                         ┌─────────────────────┐
│ token_hash           │                         │    audit_logs       │
│ expires_at           │                         ├─────────────────────┤
│ used                 │                         │ id (PK)             │
│ used_at              │                         │ user_id (FK, NULL)  │
│ created_at           │                         │ action              │
└──────────────────────┘                         │ resource_type       │
                                                 │ resource_id         │
┌──────────────────────────┐                     │ ip_address          │
│ email_verification_tokens│                     │ user_agent          │
├──────────────────────────┤                     │ details (JSON)      │
│ id (PK)                  │                     │ correlation_id      │
│ user_id (FK)             │                     │ created_at          │
│ token_hash               │                     └─────────────────────┘
│ email                    │
│ expires_at               │
│ used                     │
│ used_at                  │
│ created_at               │
└──────────────────────────┘
```

---

## Sequence Diagram: Registration Flow

```
Client          AuthRouter       AuthenticationService      Database
  │                │                      │                     │
  │  POST /register│                      │                     │
  │  { email,      │                      │                     │
  │    username,   │                      │                     │
  │    password }  │                      │                     │
  ├───────────────►│                      │                     │
  │                │  register()          │                     │
  │                ├─────────────────────►│                     │
  │                │                      │  get_by_email()     │
  │                │                      ├────────────────────►│
  │                │                      │  None               │
  │                │                      │◄────────────────────┤
  │                │                      │                     │
  │                │                      │  validate_strength()│
  │                │                      │  hash_password()    │
  │                │                      │  create user        │
  │                │                      ├────────────────────►│
  │                │                      │  User entity        │
  │                │                      │◄────────────────────┤
  │                │                      │                     │
  │                │  MessageResponse     │                     │
  │                │◄─────────────────────┤                     │
  │  201 Created   │                      │                     │
  │◄───────────────┤                      │                     │
  │                │                      │                     │
  │  (User must verify email before login)                     │
```

---

## File Structure (Phase 2)

```
backend/src/
├── core/
│   └── enums.py                           # EXTENDED — IAM enums
├── domain/
│   ├── entities/
│   │   ├── user.py                        # NEW — User aggregate root
│   │   ├── role.py                        # NEW — Role entity
│   │   ├── permission.py                  # NEW — Permission entity
│   │   ├── session.py                     # NEW — UserSession entity
│   │   ├── api_key.py                     # NEW — ApiKey entity
│   │   ├── refresh_token.py               # NEW — RefreshToken entity
│   │   ├── preferences.py                 # NEW — UserPreferences entity
│   │   ├── audit_log.py                   # NEW — AuditLog entity
│   │   └── tokens.py                      # NEW — PasswordReset/EmailVerification tokens
│   ├── exceptions/
│   │   └── auth_exceptions.py             # NEW — IAM exception hierarchy
│   └── repositories/
│       └── auth_repositories.py           # NEW — 9 repository interfaces
├── application/
│   ├── dto/
│   │   └── auth_dtos.py                   # NEW — Request/Response DTOs
│   └── services/
│       ├── password_service.py            # NEW — Hashing, verification, validation
│       ├── token_service.py               # NEW — JWT creation, validation, rotation
│       ├── authentication_service.py      # NEW — Login, register, refresh, logout
│       ├── authorization_service.py       # NEW — RBAC, FastAPI dependencies
│       ├── user_service.py                # NEW — Profile, password, preferences
│       ├── api_key_service.py             # NEW — API key CRUD and validation
│       ├── session_service.py             # NEW — Session listing and revocation
│       ├── audit_service.py               # NEW — Audit log recording
│       └── role_service.py                # NEW — Role/Permission CRUD + seeding
├── persistence/
│   ├── models/
│   │   └── auth.py                        # NEW — 12 ORM models
│   └── repositories/
│       └── auth_repositories.py           # NEW — 9 repository implementations
├── presentation/
│   ├── middleware/
│   │   └── auth.py                        # NEW — AuthMiddleware
│   ├── routers/
│   │   ├── auth.py                        # NEW — /auth/* endpoints
│   │   ├── users.py                       # NEW — /users/* endpoints
│   │   ├── api_keys.py                    # NEW — /api-keys/* endpoints
│   │   └── sessions.py                    # NEW — /sessions/* endpoints
│   ├── handlers/
│   │   └── auth_handlers.py               # NEW — Exception handler
│   └── main.py                            # UPDATED — Routers + middleware registered
└── tests/
    └── unit/
        ├── test_password_service.py       # NEW
        ├── test_token_service.py          # NEW
        ├── test_auth_entities.py          # NEW
        ├── test_auth_exceptions.py        # NEW
        ├── test_auth_dtos.py              # NEW
        ├── test_authorization.py          # NEW
        ├── test_api_key_service.py        # NEW
        └── test_authentication_service.py # NEW
```

---

## API Endpoints

### Authentication
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login | No |
| POST | `/api/v1/auth/refresh` | Refresh access token | No (refresh token) |
| POST | `/api/v1/auth/logout` | Logout current session | Yes |
| POST | `/api/v1/auth/logout-all` | Revoke all sessions | Yes |
| POST | `/api/v1/auth/forgot-password` | Request password reset | No |
| POST | `/api/v1/auth/reset-password` | Reset password with token | No |
| POST | `/api/v1/auth/verify-email` | Verify email with token | No |
| POST | `/api/v1/auth/resend-verification` | Resend verification email | No |

### Users
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/api/v1/users/me` | Get current user profile | Yes |
| PATCH | `/api/v1/users/me` | Update profile | Yes |
| PATCH | `/api/v1/users/password` | Change password | Yes |
| GET | `/api/v1/users/me/preferences` | Get preferences | Yes |
| PATCH | `/api/v1/users/me/preferences` | Update preferences | Yes |
| GET | `/api/v1/users/{id}` | Get user by ID | Yes |
| GET | `/api/v1/users` | List users | Yes |

### API Keys
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/api/v1/api-keys` | List API keys | Yes |
| POST | `/api/v1/api-keys` | Create API key | Yes |
| DELETE | `/api/v1/api-keys/{id}` | Revoke API key | Yes |
| PATCH | `/api/v1/api-keys/{id}` | Update API key | Yes |

### Sessions
| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/api/v1/sessions` | List active sessions | Yes |
| DELETE | `/api/v1/sessions/{id}` | Revoke specific session | Yes |
| DELETE | `/api/v1/sessions` | Revoke all sessions | Yes |

---

## Security Features

- **Password Hashing**: bcrypt with 12 rounds (Argon2-ready architecture)
- **Password Strength Validation**: min 8 chars, uppercase, lowercase, digit, special char
- **JWT Token Rotation**: Refresh tokens are rotated on each use (old token revoked)
- **Token Revocation**: Sessions and refresh tokens tracked in DB for revocation
- **API Key Security**: SHA-256 hashed, never stored raw, shown once at creation
- **Session Tracking**: Device, browser, OS, IP, user-agent tracked per session
- **Audit Logging**: All security events recorded (append-only)
- **Brute Force Protection**: User status can be set to LOCKED
- **Correlation IDs**: Every request traced via X-Correlation-ID
- **Future MFA Ready**: `two_factor_enabled` field on User entity
- **Future OAuth Ready**: `AuthProvider` enum supports Google, GitHub, Microsoft, etc.
