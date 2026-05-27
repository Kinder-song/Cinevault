# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`video_view` is a companion project to the RSS Reader application. It currently stores video files in the `video/` directory. The main RSS Reader project is located at `/Users/alexkinder/Hacker/AI/ClaudeCode/RSS/`.

## Video Storage

The `video/` directory contains MP4 video files (game recordings). No video processing or streaming infrastructure exists yet.

## Environment Configuration (.env)

| Variable | Description |
|----------|-------------|
| PORT | Server port (55300) |
| DB_HOST | MySQL host |
| DB_PORT | MySQL port (3306) |
| DB_USER | MySQL user (root) |
| DB_PASSWORD | MySQL password |
| DB_NAME | Database name (RSS) |
| RSSHUB_URL | RSSHub instance URL |
| MINIMAX_API_KEY | MiniMax AI API key |

## Related Project

The main application (RSS Reader with AI summarization) is at `../RSS/`:
- Backend: Node.js + Express + MySQL
- Frontend: Single HTML file with glassmorphism UI
- Features: Subscription management, article browsing, AI summaries, draggable preview modal

## Commands (RSS Backend)

```bash
cd ../RSS/backend
npm install        # Install dependencies
npm start          # Start production server
npm run dev        # Start development server with --watch
```