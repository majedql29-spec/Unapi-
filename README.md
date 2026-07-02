# JometCode - Free Online Python IDE

[![Website](https://img.shields.io/badge/Website-jometcode.2bd.net-orange)](https://jometcode.2bd.net)
[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Learn Python online for free — no install, no signup required.

**Try it now:** [jometcode.2bd.net](https://jometcode.2bd.net)

## Features

- **Online Code Editor** — powered by CodeMirror 6 with syntax highlighting, autocomplete, and multi-tab editing
- **Run Python Instantly** — execute code on a secure backend with isolated mode and 10-second timeout
- **28 Built-in Lessons** — from basics to advanced: variables, loops, functions, OOP, decorators, generators
- **File Explorer** — create, edit, rename, and delete files and folders (with user accounts)
- **Firebase Authentication** — sign in with Google or GitHub to save your projects
- **Dark & Light Themes** — toggle between themes for comfortable coding
- **Download Project** — export all your files as a ZIP archive
- **Mobile-Friendly** — responsive layout works on phones and tablets

## Quick Start

1. Open [jometcode.2bd.net](https://jometcode.2bd.net)
2. Write Python code in the editor
3. Click **Run** or press `Ctrl+Enter`
4. See output instantly in the panel

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | HTML, CSS, JavaScript, CodeMirror 6 |
| Backend | Python 3.14, SimpleHTTPRequestHandler |
| Auth | Firebase Authentication (Google, GitHub) |
| Hosting | Render |
| Domain | jometcode.2bd.net (DNSExit) |
| Analytics | Umami Cloud |
| Code Execution | Python isolated mode (`-I` flag) with sandbox restrictions |

## Security

- All user code runs in Python's isolated mode (`python -I`)
- Dangerous modules (os, subprocess, socket, etc.) are blocked
- Rate limiting: 10 requests per minute per IP
- Code size limit: 100 KB
- 10-second execution timeout
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Strict-Transport-Security`

## Project Structure

```
├── server.py              # HTTP server + API endpoint
├── index.html             # Main application page
├── learn.html             # Lessons page
├── terms.html             # Terms of Service
├── logo.png               # Favicon / logo
└── *.html                 # (28 HTML lesson files)
```

## API

**POST** `/api/run` — Execute Python code

```json
{
  "code": "print('Hello, World!')"
}
```

Response:

```json
{
  "output": "Hello, World!\n",
  "error": ""
}
```

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Made with ❤️ for the Python learning community.
