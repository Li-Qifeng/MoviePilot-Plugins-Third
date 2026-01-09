# CloudDrive2 API Reference

Based on `CloudDrive2_gRPC_API_Guide.html` (mapped to HTTP/JSON).

## Base URL
Typically `http://localhost:19798` or as configured.

## Authentication
**Header:** `Authorization: Bearer <token>`

### 1. Login (Get Token)
*   **Endpoint:** `/api/GetToken`
*   **Method:** `POST`
*   **Payload:**
    ```json
    {
      "userName": "admin",
      "password": "password",
      "totpCode": "" // Optional
    }
    ```
*   **Response:**
    ```json
    {
      "success": true,
      "token": "eyJh...",
      "expiration": "..."
    }
    ```

## File Operations

### 2. Transfer 115 Share Link
*   **Endpoint:** `/api/AddSharedLink` (or `/api/FileOperation/AddSharedLink`)
*   **Method:** `POST`
*   **Payload:**
    ```json
    {
      "sharedLinkUrl": "https://115.com/s/...",
      "sharedPassword": "",
      "toFolder": "/115/Downloads" // Path in CD2
    }
    ```

### 3. Add Offline Task (Magnet/SHA1)
*   **Endpoint:** `/api/AddOfflineFiles` (or `/api/FileOperation/AddOfflineFiles`)
*   **Method:** `POST`
*   **Payload:**
    ```json
    {
      "urls": "magnet:?xt=urn:btih:...",
      "toFolder": "/115/Offline",
      "checkFolderAfterSecs": 0
    }
    ```

### 4. Get Task Status
*   **Endpoint:** `/api/GetUploadFileList` (for transfers) or `/api/ListOfflineFilesByPath` (for offline)
*   **Method:** `POST`
*   **Payload (Offline):**
    ```json
    {
      "path": "/115/Offline",
      "forceRefresh": true
    }
    ```

## Notes
*   Most CD2 Web APIs mirror the gRPC method names.
*   Timestamps are usually ISO strings or Unix epochs.
