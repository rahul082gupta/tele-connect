# Deployment Guide - Retention Agent to Streamlit Cloud

## Quick Deploy (Recommended)

### Prerequisites
- GitHub account with your project repository
- Streamlit Community Cloud account (free at share.streamlit.io)

### Steps

1. **Push to GitHub**
```bash
cd /home/rahul/wipro
git add .
git commit -m "Add retention agent with evaluation suite"
git push origin main
```

2. **Connect to Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Sign in with GitHub
   - Click "Create app"
   - Select your repository
   - Choose branch: `main`
   - Set main file path: `streamlit_agent_app.py`
   - Click "Deploy"

3. **Access Your App**
   - Live URL: `https://[username]-[repo-name].streamlit.app`
   - Share this URL with stakeholders
   - App updates automatically on new commits

### Configuration (Streamlit Cloud)
- No secrets needed (uses mock data)
- No additional setup required
- Automatic scaling for up to 1 concurrent user (free tier)

---

## Docker Deployment (for Production)

### Build and Run Locally
```bash
# Build image
docker build -t retention-agent:latest .

# Run container
docker run -p 8501:8501 retention-agent:latest

# Access at http://localhost:8501
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "streamlit_agent_app.py", "--server.port=8501"]
```

### Deploy to Production Services

**Railway.app** (Simplest)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

**Render.com**
```bash
# Connect GitHub repo at render.com
# Set build command: pip install -r requirements.txt
# Set start command: streamlit run streamlit_agent_app.py
# Deploy
```

**AWS EC2**
```bash
# SSH into instance
ssh -i key.pem ubuntu@instance-ip

# Install dependencies
sudo apt-get update
sudo apt-get install python3-pip
pip install -r requirements.txt

# Run with systemd or supervisor for persistence
systemctl start retention-agent
```

---

## Configuration for Real LLM (Future)

When integrating real LLM providers, add secrets to Streamlit Cloud:

### Settings → Secrets (Streamlit Cloud)
```toml
[llm]
provider = "anthropic"  # or "openai"
api_key = "sk-..."

[database]
url = "postgresql://..."

[monitoring]
enabled = true
sentry_dsn = "..."
```

### Access in app
```python
import streamlit as st

api_key = st.secrets["llm"]["api_key"]
db_url = st.secrets["database"]["url"]
```

---

## Performance Optimization

### Current Performance
- Load time: ~2-3 seconds
- Response time: ~500ms (mock LLM)
- Test suite: ~30 seconds (14 tests)

### With Real LLM (Expected)
- Response time: ~2-3 seconds (Anthropic API)
- Cost per interaction: $0.01-0.05 (depending on model)
- Throughput: 10-20 requests/second

### Optimization Strategies
1. **Cache model responses** for repeated customers
2. **Async tool execution** for parallel API calls
3. **Token optimization** - remove verbose explanations
4. **Response streaming** - show results as they arrive

---

## Monitoring & Logging

### Streamlit Cloud Logs
```bash
# View logs in Streamlit Cloud dashboard
# Or stream real-time:
streamlit logs https://[your-app].streamlit.app
```

### Self-Hosted Monitoring
```python
# In your app:
import logging
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=1.0
)

logger = logging.getLogger(__name__)
logger.info(f"User interaction: {test_id}, Pass: {passed}")
```

### Metrics to Track
- API response latency
- Error rates by tool
- Hallucination occurrences
- Token usage (cost)
- User feedback

---

## Health Check

### Test Production Deployment
```bash
# Check if app is responsive
curl https://[your-app].streamlit.app

# Run evaluation suite against deployed app
python scripts/test_deployed.py --url https://[your-app].streamlit.app

# Expected: All tests pass, <2s per interaction
```

---

## Rollback Procedures

**If deployment breaks:**
```bash
# Rollback to previous commit
git revert HEAD
git push

# Streamlit Cloud auto-deploys
# Or manually redeploy from dashboard
```

**Manual version management:**
- Tag releases: `git tag v1.0.0`
- Streamlit Cloud can deploy specific tags
- Keep last 3 versions live for A/B testing

---

## Load Testing

```python
import concurrent.futures
import requests

def load_test(app_url, num_requests=100):
    def make_request(i):
        data = {
            "user_input": f"Analyze CUST001",
            "test_id": i
        }
        return requests.post(f"{app_url}/api/analyze", json=data).elapsed.total_seconds()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        times = list(executor.map(make_request, range(num_requests)))
    
    print(f"Avg latency: {sum(times)/len(times):.2f}s")
    print(f"P99 latency: {sorted(times)[int(len(times)*0.99)]:.2f}s")
    print(f"Errors: {sum(1 for t in times if t > 10)}")

# Run: load_test("https://your-app.streamlit.app")
```

---

## Support & Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'src'"**
- Ensure you're in project root when deploying
- Check requirements.txt includes all dependencies

**"Agent returns errors"**
- Check that churn model exists at `models/churn_model.joblib`
- Verify `src/predict.py` can load the model

**"Streamlit Cloud deployment fails"**
- Check requirements.txt format (no extra spaces)
- Ensure main file path is correct
- Look at deployment logs for Python errors

**"High latency with real LLM"**
- Consider response caching
- Use model-specific optimizations (e.g., Claude token batching)
- Implement result streaming

---

## Getting Help

- **Streamlit Docs**: https://docs.streamlit.io
- **Community Cloud Setup**: https://docs.streamlit.io/deploy/streamlit-community-cloud
- **GitHub Issues**: [project repo]/issues
- **LLM API Docs**: 
  - Anthropic: https://docs.anthropic.com
  - OpenAI: https://platform.openai.com/docs

---

**Status**: ✅ Ready for deployment

**Deployment Options**: Streamlit Cloud (easiest), Railway, Render, Docker, AWS

**Time to Deploy**: <5 minutes (Streamlit Cloud) to <30 minutes (self-hosted)
