# RENDER DEPLOYMENT GUIDE (FREE TIER)

Render supports **Infrastructure-as-Code** blueprints. By adding a `render.yaml` file to your repository root, you can spin up the entire LangGraph Agent Server stack (API + PostgreSQL + Redis) with a single click.

---

## Step 1: Push Your Code to GitHub

Before deploying, make sure your latest code (including the newly added `render.yaml`) is pushed to your GitHub repository:

```bash
git add render.yaml
git commit -m "Add Render blueprint configuration"
git push origin <your-branch-name>
```

---

## Step 2: Deploy on Render

1. Go to your [Render Dashboard](https://dashboard.render.com/) and sign in.
2. Click the **"New +"** button in the top right and select **"Blueprint"** (or go to **"Blueprints"** in the top navigation).
3. Connect your GitHub account and select your **agent repository**.
4. Render will read the `render.yaml` file and automatically display the services it will create:
   * `langgraph-postgres` (Database)
   * `langgraph-redis` (Private Redis Cache)
   * `langgraph-api` (Docker Web Service)
5. **Enter your API keys**: Render will prompt you to fill in the missing environment variables:
   * `OPENAI_API_KEY`
   * `TAVILY_API_KEY`
   * `LANGSMITH_API_KEY`
6. Click **"Apply"** or **"Deploy"**.

---

## Step 3: Verify the Deployment

1. Render will take 4–6 minutes to build your Docker image, provision the database, and spin up Redis.
2. Once the `langgraph-api` service status turns green (**"Live"**), copy its public URL from your dashboard. It will look like:
   `https://langgraph-api-xxxx.onrender.com`
3. Test your live deployment in your browser or terminal:
   ```bash
   curl -i https://langgraph-api-xxxx.onrender.com/ok
   ```
   *(You should receive a `{"ok":true}` response!)*

---

## Step 4: Update Your Frontend API URL

Now connect your live agent backend to your Next.js chat frontend on **Vercel** by updating its environment variables:

```env
LANGGRAPH_API_URL=https://langgraph-api-xxxx.onrender.com
LANGSMITH_API_KEY=lsv2_pt_...
```

Vercel will redeploy your frontend, and your chat UI is officially live and connected to your production-grade cloud LangGraph agent!
