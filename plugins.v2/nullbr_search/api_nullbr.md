# Nullbr Official API Reference

Based on the official Nullbr API documentation.

## Base URL
`https://api.nullbr.eu.org`

## Authentication
All requests require the following headers:
*   `X-APP-ID`: Your Application ID
*   `X-API-KEY`: Your User API Key (Required for resource endpoints like `/115`, `/magnet`)

> **Note**: For some metadata endpoints (search, movie info), only `X-APP-ID` might be strictly required, but it's best practice to send both if available.

## Endpoints

### 1. Search (影视查询)
*   **Endpoint:** `/search`
*   **Method:** `GET`
*   **Parameters:**
    *   `query` (string): Search keyword (e.g., "Iron Man").
    *   `page` (int, optional): Page number (default: 1).
*   **Response:**
    ```json
    {
      "page": 1,
      "total_pages": 1,
      "total_results": 24,
      "items": [
        {
          "media_type": "movie", // "movie", "tv", "collection", "person"
          "tmdbid": 1726,
          "title": "Iron Man",
          "poster": "/path/to/poster.jpg",
          "overview": "...",
          "vote_average": 7.6,
          "release_date": "2008-04-30",
          "115-flg": 1,      // 1: Has 115 resources, 0: No
          "magnet-flg": 1,   // 1: Has magnet resources
          "video-flg": 1,    // 1: Has m3u8 resources
          "ed2k-flg": 1      // 1: Has ed2k resources
        }
      ]
    }
    ```

### 2. Movie Metadata (获取电影信息)
*   **Endpoint:** `/movie/{tmdbid}`
*   **Method:** `GET`
*   **Response:** Detailed movie metadata including resource flags.

### 3. Movie Resources

#### 3.1 115 Share Links (网盘资源)
*   **Endpoint:** `/movie/{tmdbid}/115`
*   **Method:** `GET`
*   **Response:**
    ```json
    {
      "id": 78,
      "media_type": "movie",
      "115": [
        {
          "title": "Movie Title (Year)",
          "size": "83.03 GB",
          "share_link": "https://115cdn.com/s/...?password=...",
          "resolution": "2160p",
          "quality": "HDR10"
        }
      ]
    }
    ```

#### 3.2 Magnet Links (磁力资源)
*   **Endpoint:** `/movie/{tmdbid}/magnet`
*   **Method:** `GET`
*   **Response:**
    ```json
    {
      "id": 78,
      "media_type": "movie",
      "magnet": [
        {
          "name": "Movie.Name.2160p.Remux",
          "size": "44.69 GB",
          "magnet": "magnet:?xt=urn:btih:...",
          "resolution": "2160p",
          "quality": ["Remux", "HDR10"],
          "zh_sub": 1 // 1: Has Chinese subs
        }
      ]
    }
    ```

#### 3.3 Ed2k Links
*   **Endpoint:** `/movie/{tmdbid}/ed2k`
*   **Method:** `GET`
*   **Response:** Similar structure to Magnet, but with `ed2k` field.

### 4. TV Show Metadata (获取剧集信息)
*   **Endpoint:** `/tv/{tmdbid}`
*   **Method:** `GET`
*   **Response:**
    ```json
    {
      "id": 1396,
      "title": "Breaking Bad",
      "number_of_seasons": 5,
      "115-flg": 1,
      "magnet-flg": 1, // Note: This means magnet exists at Season/Episode level
      ...
    }
    ```

### 5. TV Show Resources

#### 5.1 115 Share Links (剧集网盘)
*   **Endpoint:** `/tv/{tmdbid}/115`
*   **Method:** `GET`
*   **Description:** Returns 115 share links for the **entire show** (or multiple seasons).
*   **Response:**
    ```json
    {
      "id": 1396,
      "115": [
        {
          "title": "Breaking Bad (2008)",
          "size": "299.82 GB",
          "share_link": "https://115cdn.com/s/...",
          "season_list": ["S1", "S2", "S3", "S4", "S5"] // Seasons included
        }
      ]
    }
    ```

#### 5.2 Season Magnet (剧集季磁力)
*   **Endpoint:** `/tv/{tmdbid}/season/{season_number}/magnet`
*   **Method:** `GET`
*   **Response:**
    ```json
    {
      "id": 1396,
      "season_number": 1,
      "magnet": [
        {
          "name": "Breaking.Bad.S01.Complete...",
          "size": "35.52 GB",
          "magnet": "magnet:?xt=urn:btih:...",
          "quality": "Complete" // Often indicates full season pack
        }
      ]
    }
    ```

#### 5.3 Episode Resources (Single Episode)
*   **Magnet:** `/tv/{tmdbid}/season/{season_number}/episode/{episode_number}/magnet`
*   **Ed2k:** `/tv/{tmdbid}/season/{season_number}/episode/{episode_number}/ed2k`
*   **M3U8:** `/tv/{tmdbid}/season/{season_number}/episode/{episode_number}/video`

### 6. Other Endpoints
*   `/person/{id}`: Person info.
*   `/collection/{id}`: Collection info.
*   `/list/{id}`: List info.

## Error Codes
*   `200`: Success
*   `403`: Invalid APP ID
*   `404`: Resource not found