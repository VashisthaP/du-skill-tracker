# SkillHive

> **DU Demand & Supply Tracker** — An Accenture-branded web portal for tracking Delivery Unit skill demands, resource evaluations, and talent supply.

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FVashisthaP%2Fdu-skill-tracker%2Fmain%2Finfrastructure%2Fazuredeploy.json)

---

## Features

| Feature | Description |
|---|---|
| **Skill Demand Board** | PMO creates demands with project details, required skills, career level (CL8-12), and evaluator info |
| **Get Evaluated** | Resources apply for demands with a one-page resume (DOCX/PPTX) |
| **Status Tracking** | Applied → Under Evaluation → Selected / Rejected with full audit trail |
| **Trending Skills** | Visual skill cloud and bar charts showing most-demanded skills |
| **Email Notifications** | Automated emails to demand raiser and evaluator on key events |
| **Excel Export** | Download demands and applications as Accenture-themed Excel files |
| **Role-Based Access** | Admin, PMO, Evaluator, and Resource roles with granular permissions |
| **Azure AD SSO** | Single sign-on via Microsoft Entra ID (Azure Active Directory) |

---

## Tech Stack

- **Backend**: Python 3.11, Flask 3.0, SQLAlchemy ORM
- **Frontend**: Bootstrap 5.3, Chart.js, Bootstrap Icons
- **Auth**: MSAL (Microsoft Authentication Library) for Azure AD
- **Database**: SQLite (dev) / PostgreSQL Flexible Server (prod)
- **Storage**: Azure Blob Storage for resume uploads
- **Email**: Flask-Mail (Office 365 SMTP)
- **Monitoring**: Application Insights
- **Deployment**: Azure App Service B1 (Linux)

---

## Quick Start (Local Development)

### 1. Clone & Set Up

```bash
git clone https://github.com/VashisthaP/du-skill-tracker.git
cd du-skill-tracker

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
```

Edit `.env` and set:
```
DEV_MODE=true
SECRET_KEY=any-random-string-here
```

> **DEV_MODE=true** enables local login without Azure AD. Set to `false` for production.

### 3. Seed Sample Data (Optional)

```bash
python scripts/seed_data.py
```

### 4. Run

```bash
python app/app.py
```

Open **http://localhost:5000** in your browser.

Use Dev Login with any email (e.g., `admin@accenture.com`) to test different roles.

---

## Deploy to Azure

### Prerequisites

1. An Azure subscription
2. An Azure AD App Registration (for SSO)
3. A GitHub account

### Option A: One-Click Deploy (Recommended)

Click the **Deploy to Azure** button at the top of this README. Fill in:

| Parameter | Value |
|---|---|
| **App Name** | A unique name (e.g., `skillhive-mydu`) |
| **Location** | `Central India` (or your nearest region) |
| **Postgres Admin Password** | A strong password (8+ chars, mixed case + digit) |
| **Azure AD Client ID** | From your App Registration |
| **Azure AD Client Secret** | From your App Registration |
| **Azure AD Tenant ID** | Your Azure AD Tenant ID |
| **Mail Username** | Your Office 365 email (optional) |
| **Mail Password** | Your email password (optional) |

Deployment takes ~10 minutes. Your app will be live at `https://<app-name>.azurewebsites.net`.

### Option B: GitHub Actions CI/CD

1. Fork this repository
2. Add these **GitHub Secrets** (Settings → Secrets → Actions):
   - `AZURE_WEBAPP_NAME` — Your App Service name
   - `AZURE_CREDENTIALS` — Service principal JSON (see below)

3. Push to `main` branch — the workflow will auto-deploy.

**Creating Azure Credentials:**
```bash
# In Azure Cloud Shell
az ad sp create-for-rbac --name "skillhive-deploy" \
  --role contributor \
  --scopes /subscriptions/<YOUR-SUBSCRIPTION-ID>/resourceGroups/<YOUR-RG> \
  --sdk-auth
```

Copy the JSON output as the `AZURE_CREDENTIALS` secret.

---

## Azure AD App Registration

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**
2. **Name**: SkillHive
3. **Redirect URI**: `https://<your-app-name>.azurewebsites.net/auth/callback`
   - For local dev, also add: `http://localhost:5000/auth/callback`
4. **Certificates & secrets** → **New client secret** → Copy the value
5. Note down:
   - **Application (client) ID**
   - **Directory (tenant) ID**
   - **Client secret value**

---

## Project Structure

```
skilltracker/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── app.py               # Dev server runner
│   ├── config.py            # Configuration
│   ├── models.py            # SQLAlchemy models
│   ├── forms.py             # WTForms definitions
│   ├── auth.py              # Azure AD authentication
│   ├── routes/
│   │   ├── main.py          # Dashboard & APIs
│   │   ├── demands.py       # Demand CRUD
│   │   ├── applications.py  # Application workflow
│   │   └── admin.py         # Admin panel
│   ├── services/
│   │   ├── email_service.py # Email notifications
│   │   └── export_service.py# Excel export
│   ├── utils/
│   │   └── decorators.py    # Role-based access
│   ├── static/              # CSS, JS, images
│   └── templates/           # Jinja2 HTML templates
├── infrastructure/
│   └── azuredeploy.json     # ARM template
├── .github/workflows/
│   └── deploy.yml           # CI/CD pipeline
├── database/migrations/     # SQL schema
├── scripts/
│   └── seed_data.py         # Sample data seeder
├── tests/                   # Test suite
├── requirements.txt
└── README.md
```

---

## Roles & Permissions

| Role | Can Do |
|---|---|
| **Admin** | Everything + user role management + skill taxonomy |
| **PMO** | Create/edit/cancel demands, manage applications, update status, export |
| **Evaluator** | View assigned demands, update application status |
| **Resource** | Browse demands, apply for evaluation, track own applications |

---

## Estimated Azure Cost

| Resource | SKU | ~Monthly Cost (INR) |
|---|---|---|
| App Service Plan | B1 (Linux) | ₹1,100 |
| PostgreSQL Flexible Server | Burstable B1ms | ₹1,300 |
| Storage Account | Standard LRS | ₹50 |
| Application Insights | Free tier | Free |
| **Total** | | **~₹2,450/month** |

Well within ₹4,000/month budget.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Azure Deployment Commands

After making any code changes, use the following commands to deploy to Azure. Run these in **Azure Cloud Shell** (Bash).

### Block 1 — Set Variables & Deploy

```bash
export RG_NAME="rg-skillhive"
export APP_NAME="skillhive-accenture"
export SUBSCRIPTION_ID="2f0676e3-d88a-4118-93c9-5c05c8da156f"
az account set --subscription "$SUBSCRIPTION_ID"

cd /tmp
rm -rf /tmp/skillhive
git clone https://github.com/VashisthaP/du-skill-tracker.git skillhive
cd /tmp/skillhive

rm -f /tmp/deploy.zip
zip -r /tmp/deploy.zip . -x ".git/*" "pvenv/*" "__pycache__/*" "*.pyc" ".env" "tests/*"

az webapp deployment source config-zip \
  --resource-group "$RG_NAME" \
  --name "$APP_NAME" \
  --src /tmp/deploy.zip \
  --timeout 600
```

### Block 2 — Extract Compressed Build & Restart

Once Block 1 finishes, SSH into the App Service to extract the Oryx build output:

```bash
az webapp ssh --resource-group "rg-skillhive" --name "skillhive-accenture"
```

**Inside SSH, run (check which file exists and use the matching command):**

If `output.tar.gz` exists:
```bash
cd /home/site/wwwroot
tar xzf output.tar.gz
exit
```

If `output.tar.zst` exists:
```bash
cd /home/site/wwwroot
tar --zstd -xf output.tar.zst
exit
```

### Block 3 — Restart the App

```bash
az webapp restart --resource-group "rg-skillhive" --name "skillhive-accenture"
```

The app will be live at **https://skillhive-accenture.azurewebsites.net** after restart.
