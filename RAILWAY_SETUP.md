# Railway Deployment Setup

## Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose **`eritger1110/brikk-ucs-backend`**
5. Railway will auto-detect Python and start building

## Step 2: Configure Environment Variables

In Railway dashboard, go to **Variables** tab and add:

```env
OPENAI_API_KEY=sk-proj-your-key-here
CORS_ORIGINS=https://3000-izm86p4nsuk8lkf8pus89-fe6db43a.manusvm.computer,http://localhost:3000
PORT=${{PORT}}
```

**How to get OpenAI API key:**
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **"Create new secret key"**
3. Name it: `Brikk UCS Backend`
4. Copy the key (starts with `sk-proj-...`)

## Step 3: Deploy

1. Click **"Deploy"** button
2. Wait 3-5 minutes for build to complete
3. Railway will provide a public URL like: `https://brikk-ucs-backend-production.up.railway.app`

## Step 4: Test Deployment

```bash
# Health check
curl https://your-railway-url.up.railway.app/health

# List integrations
curl https://your-railway-url.up.railway.app/api/v1/integrations
```

Expected response:
```json
{
  "integrations": [...],
  "total": 56
}
```

## Step 5: Update Dashboard

Update your dashboard environment variables:

```env
VITE_UCS_API_URL=https://your-railway-url.up.railway.app
```

Redeploy the dashboard on Netlify/Vercel.

## Troubleshooting

### Build Failed
- Check `requirements.txt` has all dependencies
- Verify Python version in `runtime.txt` is 3.11.0
- Check Railway logs for specific error

### CORS Errors
- Add your dashboard URL to `CORS_ORIGINS`
- Include both production and preview URLs
- Redeploy after changing environment variables

### OpenAI API Errors
- Verify API key is valid on OpenAI dashboard
- Check API key has GPT-4 access
- Ensure OpenAI account has credits

## Next Steps

1. ✅ Deploy to Railway
2. ✅ Test all endpoints
3. ✅ Update dashboard environment variables
4. ✅ Test integration marketplace in dashboard
5. ✅ Test connector generation with sample API docs

## Support

Questions? Check the full deployment guide:
- [RAILWAY_DEPLOYMENT_GUIDE.md](https://github.com/eritger1110/brikk-platform/blob/main/RAILWAY_DEPLOYMENT_GUIDE.md)
- Email: support@getbrikk.com
