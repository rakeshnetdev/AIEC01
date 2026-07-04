# STANDALONE SERVER PRODUCTION DEPLOYMENT GUIDE (VPS)

This guide walks you through deploying your production-ready LangGraph agent server stack directly onto your own virtual private server (VPS) using Docker Compose and Nginx (with automated Let's Encrypt HTTPS certificates).

---

## Architecture Overview

On your VPS, the final stack will look like this:

```
                  ┌──────────────────────────────────────────────┐
                  │                  Your VPS                    │
                  │                                              │
Client (HTTPS) ───┼─► [Nginx Proxy (Port 443)]                   │
                  │         │ (Local Proxy)                      │
                  │         ▼                                    │
                  │   [LangGraph API (Port 2024 / 8000)]         │
                  │         │ (Internal Docker Network)          │
                  │         ├────────────────────────┐           │
                  │         ▼                        ▼           │
                  │   [Redis Cache (6379)]     [Postgres (5432)] │
                  └──────────────────────────────────────────────┘
```

---

## Step 1: Prepare Your VPS (Ubuntu Server recommended)

1. SSH into your VPS:
   ```bash
   ssh root@your_vps_ip
   ```

2. Update system packages:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. Install Docker and Docker Compose:
   ```bash
   sudo apt install -y docker.io docker-compose-v2
   sudo systemctl enable --now docker
   ```

---

## Step 2: Clone Code and Configure Environment

1. Clone your agent repository on the VPS:
   ```bash
   git clone <your_github_repository_url>
   cd <your_project_directory>
   ```

2. Create the production `.env` file in the root of the project:
   ```bash
   nano .env
   ```

3. Paste your production environment variables (fill in your actual keys):
   ```env
   OPENAI_API_KEY=sk-...
   TAVILY_API_KEY=tvly-...
   LANGSMITH_API_KEY=lsv2_pt_...
   LANGSMITH_TRACING=true
   LANGSMITH_PROJECT=feline-health-agent-vps
   ```

---

## Step 3: Run the Docker Compose Stack

Start your production containers in detached (background) mode:
```bash
docker compose up --build -d
```

### Verify running containers:
```bash
docker compose ps
```
All three containers (`langgraph-api`, `postgres-db`, and `redis-cache`) should be listed as `healthy` or `running`.

---

## Step 4: Configure Nginx & Let's Encrypt SSL (HTTPS)

Modern browsers block insecure `http` requests to APIs if your frontend (like Next.js on Vercel) is loaded via `https`. Therefore, your VPS API must be served over `https`.

1. Install Nginx and Certbot (for SSL certificates):
   ```bash
   sudo apt install -y nginx certbot python3-certbot-nginx
   ```

2. Create an Nginx configuration file for your subdomain (e.g. `api.yourdomain.com`):
   ```bash
   sudo nano /etc/nginx/sites-available/langgraph-api
   ```

3. Paste the following configuration (replace `api.yourdomain.com` with your actual subdomain pointing to your VPS IP):
   ```nginx
   server {
       server_name api.yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:2024;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # Extend timeouts for streaming / SSE
           proxy_read_timeout 3600s;
           proxy_send_timeout 3600s;
           chunked_transfer_encoding on;
       }
   }
   ```

4. Enable the site and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/langgraph-api /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

5. Request a free SSL certificate from Let's Encrypt:
   ```bash
   sudo certbot --nginx -d api.yourdomain.com
   ```
   *(Follow the prompts. Certbot will automatically issue and install the certificate, and configure automated redirects from http to https!)*

---

## Step 5: Update Your Frontend API Endpoint

Now that your agent backend is running securely online at `https://api.yourdomain.com`, connect it to your Next.js chat frontend on **Vercel** by updating its environment variables:

```env
LANGGRAPH_API_URL=https://api.yourdomain.com
LANGSMITH_API_KEY=lsv2_pt_...
```

Your Next.js frontend API proxy route will now securely forward all streams directly to your standalone VPS Agent Server!
