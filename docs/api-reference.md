# API Reference

Base URL: `http://localhost:8000`  
Interactive docs (Swagger UI): `http://localhost:8000/api/docs/`  
OpenAPI schema: `http://localhost:8000/api/docs/?format=json`

All endpoints except `/api/auth/register/`, `/api/auth/login/`, and `/health/` require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

---

## Authentication

### Register
```
POST /api/auth/register/
```
```json
{
  "email": "user@example.com",
  "password": "strongpassword",
  "full_name": "Jane Doe"
}
```
Returns `201` with `{ "access": "...", "refresh": "...", "user": {...} }`.

### Login
```
POST /api/auth/login/
```
```json
{ "email": "user@example.com", "password": "..." }
```
Returns `200` with `{ "access": "...", "refresh": "...", "user": {...} }`.  
Rate-limited: 5 attempts per 15 minutes.

### Refresh token
```
POST /api/auth/token/refresh/
```
```json
{ "refresh": "<refresh_token>" }
```
Returns a new `access` + `refresh` pair. The old refresh token is blacklisted (rotation).

### Current user
```
GET /api/auth/me/
```
Returns `{ "id", "email", "full_name", "is_staff", "created_at" }`.

### Change password
```
POST /api/auth/me/password/
```
```json
{ "current_password": "...", "new_password": "..." }
```
Invalidates all existing sessions (blacklists all refresh tokens for the user).

### Logout
```
POST /api/auth/logout/
```
```json
{ "refresh": "<refresh_token>" }
```
Blacklists the provided refresh token.

---

## Workspaces

### List workspaces
```
GET /api/workspaces/
```
Returns workspaces the authenticated user is a member of.

### Create workspace
```
POST /api/workspaces/
```
```json
{ "name": "Engineering" }
```
The caller is automatically assigned the `owner` role.

### Get workspace
```
GET /api/workspaces/{workspace_id}/
```

### Delete workspace
```
DELETE /api/workspaces/{workspace_id}/
```
Owner only. Cascades to all collections, documents, and chat sessions.

### List members
```
GET /api/workspaces/{workspace_id}/members/
```

### Invite member
```
POST /api/workspaces/{workspace_id}/members/
```
```json
{ "email": "colleague@example.com", "role": "member" }
```
Roles: `owner`, `admin`, `member`, `viewer`. Admin or owner required.

### Update member role
```
PATCH /api/workspaces/{workspace_id}/members/{member_id}/
```
```json
{ "role": "admin" }
```

### Remove member
```
DELETE /api/workspaces/{workspace_id}/members/{member_id}/
```

---

## Collections

### List collections
```
GET /api/workspaces/{workspace_id}/collections/
```

### Create collection
```
POST /api/workspaces/{workspace_id}/collections/
```
```json
{ "name": "Legal Contracts", "description": "Optional description" }
```
Admin or owner required. Collection names are unique within a workspace.

### Get collection
```
GET /api/workspaces/{workspace_id}/collections/{collection_id}/
```

### Update collection
```
PATCH /api/workspaces/{workspace_id}/collections/{collection_id}/
```

### Delete collection
```
DELETE /api/workspaces/{workspace_id}/collections/{collection_id}/
```
Deletes the collection but does not delete its documents (they become collection-less).

---

## Documents

### List documents
```
GET /api/workspaces/{workspace_id}/documents/
```
Optional query parameters:
- `collection_id=<uuid>` — filter by collection
- `status=ready|processing|queued|failed` — filter by status

Paginated (cursor-based).

### Upload document
```
POST /api/workspaces/{workspace_id}/documents/
Content-Type: multipart/form-data
```
Fields:
- `file` (required) — the file to upload (PDF, DOCX, TXT, MD; max 20 MB)
- `collection_id` (optional) — assign to a collection

Returns `202 Accepted` immediately. Processing happens asynchronously.  
Rate-limited: 30 uploads per minute.

**Document status flow:**
```
QUEUED → PROCESSING → READY
                    ↘ FAILED
```

### Get document (status polling)
```
GET /api/workspaces/{workspace_id}/documents/{document_id}/
```
Poll this endpoint to track processing status. Response includes `status`, `chunk_count`, `error_message`.

### Download document
```
GET /api/workspaces/{workspace_id}/documents/{document_id}/download/
```
Returns `302 Redirect` to a presigned MinIO/S3 URL (valid for 15 minutes).

### Delete document
```
DELETE /api/workspaces/{workspace_id}/documents/{document_id}/
```
Admin/owner, or the user who uploaded the document.

---

## Search

```
POST /api/workspaces/{workspace_id}/search/
```
Rate-limited: 30 requests per minute.

**Request:**
```json
{
  "query": "What are the payment terms?",
  "collection_id": null,
  "limit": 10
}
```
- `query` — the search string (required)
- `collection_id` — restrict search to a specific collection (optional)
- `limit` — number of results, 1–50, default 10

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "document_name": "contract_2024.pdf",
      "collection_id": "uuid",
      "content": "...chunk text...",
      "score": 0.84,
      "chunk_index": 3
    }
  ],
  "query": "What are the payment terms?",
  "total": 4
}
```

---

## Chat

### List sessions
```
GET /api/workspaces/{workspace_id}/chat/sessions/
```

### Create session
```
POST /api/workspaces/{workspace_id}/chat/sessions/
```
```json
{ "title": "Q3 contract review" }
```

### Get session (with messages)
```
GET /api/workspaces/{workspace_id}/chat/sessions/{session_id}/
```

### Delete session
```
DELETE /api/workspaces/{workspace_id}/chat/sessions/{session_id}/
```

### Send message (SSE streaming)
```
POST /api/workspaces/{workspace_id}/chat/sessions/{session_id}/messages/
```
Rate-limited: 20 requests per minute.

**Request:**
```json
{ "content": "What does clause 5 say about liability?" }
```

**Response:** `Content-Type: text/event-stream`

The response streams three event types:

```
data: {"type": "token", "token": "Clause"}

data: {"type": "token", "token": " 5"}

data: {"type": "done", "citations": [
  {"document_name": "contract.pdf", "chunk_index": 12}
]}
```

On error:
```
data: {"type": "error", "message": "Ollama is unreachable"}
```

---

## Health

```
GET /health/
```
Returns `200 OK` when both PostgreSQL and Redis are reachable:
```json
{ "status": "ok", "database": "ok", "cache": "ok" }
```

Returns `503 Service Unavailable` if either dependency is down:
```json
{ "status": "degraded", "database": "ok", "cache": "error" }
```

---

## Error responses

All errors follow the same structure:

```json
{
  "error": "Human-readable message",
  "code": "machine_readable_code"
}
```

Common HTTP status codes:

| Status | Meaning |
|---|---|
| `400` | Validation error (invalid input) |
| `401` | Missing or expired access token |
| `403` | Authenticated but insufficient role |
| `404` | Resource not found or not in this workspace |
| `413` | File exceeds 20 MB limit |
| `415` | Unsupported file type |
| `429` | Rate limit exceeded |
| `503` | Database or Redis unavailable |
