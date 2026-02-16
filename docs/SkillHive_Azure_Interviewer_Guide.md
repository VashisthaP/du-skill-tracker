# SkillHive – Azure Integration Services Interviewer Guide

**Document Version:** 1.2  
**Date:** February 14, 2026  
**Project:** SkillHive – DU Demand & Supply Tracker  
**Purpose:** Interview preparation guide covering all Azure services used in this project  

---

## Table of Contents

1. [Azure App Service](#1-azure-app-service)
2. [Azure Database for PostgreSQL – Flexible Server](#2-azure-database-for-postgresql--flexible-server)
3. [Azure Blob Storage](#3-azure-blob-storage)
4. [Azure Application Insights](#4-azure-application-insights)
5. [Azure Log Analytics Workspace](#5-azure-log-analytics-workspace)
6. [Azure Resource Manager (ARM) Templates](#6-azure-resource-manager-arm-templates)
7. [Azure App Service Build & Deployment (Oryx)](#7-azure-app-service-build--deployment-oryx)
8. [Azure Identity & Authentication](#8-azure-identity--authentication)
9. [Azure Networking & Security in App Service](#9-azure-networking--security-in-app-service)
10. [Cross-Service Integration Scenarios](#10-cross-service-integration-scenarios)
11. [Troubleshooting & Real-World Scenarios](#11-troubleshooting--real-world-scenarios)
12. [Bulk Excel Upload & Resource Evaluation (v1.1)](#12-bulk-excel-upload--resource-evaluation-v11)
13. [RRD Refactoring & Expanded Evaluation Workflow (v1.2)](#13-rrd-refactoring--expanded-evaluation-workflow-v12)

---

## 1. Azure App Service

### Q1: What is Azure App Service and why did you choose it for SkillHive?

**Answer:**  
Azure App Service is a fully managed PaaS (Platform as a Service) that allows hosting web applications, REST APIs, and backend services without managing underlying infrastructure. We chose it for SkillHive because:

- **Managed Infrastructure:** No need to manage OS patches, load balancers, or web servers — Azure handles it.
- **Built-in Python Support:** Native Python 3.11 runtime with Oryx build system that auto-installs pip dependencies.
- **Always On:** B1 tier supports Always On to prevent cold start delays.
- **Integrated Deployment:** Supports zip deploy, Git deploy, GitHub Actions CI/CD.
- **Built-in Monitoring:** Seamless integration with Application Insights for APM.
- **SSL/TLS:** Free managed certificates or custom domain SSL.
- **Cost-Effective:** B1 (Basic) tier at ~$13/month is sufficient for internal DU-level tools.

---

### Q2: Explain the App Service Plan tiers. Why did you use B1?

**Answer:**  
App Service Plans define the compute resources:

| Tier     | Features                                           | Use Case                        |
|----------|----------------------------------------------------|---------------------------------|
| **Free/Shared (F1/D1)** | Shared infra, no custom domains, no SSL | Development/testing only        |
| **Basic (B1/B2/B3)**    | Dedicated VMs, custom domains, SSL, Always On | Low-traffic internal apps       |
| **Standard (S1/S2/S3)** | Auto-scale, staging slots, daily backups | Production workloads            |
| **Premium (P1v3/P2v3)** | Better perf, VNet integration, more scale | High-traffic, enterprise        |
| **Isolated (I1v2)**     | Fully isolated in ASE, compliance workloads | Regulated industries            |

We used **B1** (1 core, 1.75 GB RAM, ~$13/month) because:
- SkillHive is an **internal DU-level tool** with < 100 concurrent users.
- B1 supports **Always On** (critical to avoid cold starts with Gunicorn).
- B1 supports **custom domains** and **SSL**.
- If traffic grows, we can scale UP to S1/P1v3 or scale OUT with multiple instances on Standard/Premium tier.

---

### Q3: What is the Gunicorn WSGI server? Why not use the built-in Flask development server?

**Answer:**  
Gunicorn (Green Unicorn) is a production-grade **Python WSGI HTTP server** that:
- Supports **multiple worker processes** for handling concurrent requests (we use 2 workers).
- Is the **recommended WSGI server** for Flask/Django on Azure App Service Linux.
- Handles **process management** (auto-restarts crashed workers).

Flask's built-in `app.run()` server is **single-threaded and not production-safe** — it can't handle concurrent requests, has no process supervision, and has security vulnerabilities.

Our startup command:
```
gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 wsgi:app
```

- `--bind=0.0.0.0:8000`: App Service routes traffic to port 8000
- `--timeout 600`: 10-minute timeout for long Excel exports
- `--workers 2`: 2 pre-forked worker processes (recommended: `2 × CPU cores + 1`)
- `wsgi:app`: entry point module (`wsgi.py`) and Flask `app` object

---

### Q4: What is the "Always On" setting and why is it important?

**Answer:**  
Always On sends periodic HTTP requests to keep the app loaded in memory. Without it:
- App Service **unloads the app after 20 minutes** of inactivity.
- The next request triggers a **cold start** (Gunicorn startup + module loading = 10–30 seconds).
- Available only on B1 tier and above (not on Free/Shared).

For SkillHive, Always On prevents unacceptable delays for the first user login in the morning.

---

### Q5: Explain the `SCM_DO_BUILD_DURING_DEPLOYMENT` setting.

**Answer:**  
This app setting tells the **Kudu/Oryx build system** to run a full build during zip deployment:

1. Detects the Python version from runtime config.
2. Creates a virtual environment (`antenv`).
3. Runs `pip install -r requirements.txt`.
4. Compresses the output into `/home/site/wwwroot/output.tar.gz`.

Without this setting, the deployment would just extract the zip without installing dependencies — causing `ModuleNotFoundError` at runtime because packages like Flask, SQLAlchemy, gunicorn wouldn't be installed.

---

### Q6: How does the Flask Application Factory pattern work in SkillHive?

**Answer:**  
The Application Factory pattern defers Flask app creation to a function (`create_app()`), rather than creating it at module import time. Benefits:

1. **Multiple configurations:** Same code can instantiate development, production, or testing apps.
2. **Testability:** Test suite creates fresh app instances with `TestingConfig`.
3. **Circular import prevention:** Extensions (`db`, `login_manager`, `mail`) are declared globally but bound to the app inside `create_app()`.

```python
# __init__.py
db = SQLAlchemy()          # Created without app
login_manager = LoginManager()

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    db.init_app(app)        # Bound to app here
    login_manager.init_app(app)
    # Register blueprints, error handlers, etc.
    return app
```

---

## 2. Azure Database for PostgreSQL – Flexible Server

### Q7: Why PostgreSQL over Azure SQL Database or Cosmos DB?

**Answer:**  

| Criteria                | PostgreSQL Flexible     | Azure SQL DB           | Cosmos DB              |
|-------------------------|-------------------------|------------------------|------------------------|
| **Data Model**          | Relational (perfect for structured demand/application data) | Relational | Document/NoSQL |
| **ORM Compatibility**   | Excellent with SQLAlchemy + psycopg2 | Good (pyodbc) | Custom SDK |
| **Cost (Dev/Test)**     | Burstable B1ms ~$12/mo  | Basic DTU ~$5/mo       | Min ~$25/mo            |
| **Open Source**         | Yes                     | No (proprietary)       | No                     |
| **Flask Ecosystem**     | First-class support     | Requires pyodbc driver | Different paradigm     |

We chose PostgreSQL because:
- **Strong relational model** for Demands ↔ Skills (M:N), Applications ↔ History (1:N).
- **SQLAlchemy + psycopg2** is the gold standard for Flask + PostgreSQL.
- **Flexible Server** is the latest Azure PostgreSQL offering with better cost, HA, and maintenance controls.

---

### Q8: What is the difference between Single Server and Flexible Server?

**Answer:**  

| Feature              | Single Server (Legacy)      | Flexible Server (Current)       |
|----------------------|-----------------------------|----------------------------------|
| **Status**           | Retirement: March 2025      | Actively developed              |
| **HA Options**       | No zone-redundant HA        | Zone-redundant & same-zone HA   |
| **Maintenance**      | Azure-controlled            | User-controlled window          |
| **Networking**       | VNet rules, Private Link    | VNet integration (delegated subnet) + Public |
| **Compute**          | Fixed tiers                 | Burstable / GP / Memory-Optimized |
| **Stop/Start**       | Not supported               | Supported (cost savings)        |
| **Major Upgrades**   | Manual dump/restore         | In-place major version upgrade  |

Single Server is **deprecated**. Flexible Server should always be used for new projects.

---

### Q9: Explain the Burstable tier. Is it suitable for production?

**Answer:**  
The **Burstable** tier (B-series) provides:
- **Baseline CPU** with the ability to **burst above baseline** when needed.
- Credits accumulate during low usage, expended during spikes.
- **B1ms:** 1 vCore, 2 GB RAM, ~$12/month.

**Suitable for production?**
- Yes, for **low-traffic internal apps** like SkillHive (< 100 users, intermittent queries).
- NOT for sustained high-CPU workloads (e.g., reporting-heavy apps) — use **General Purpose** tier instead.
- Key risk: If credits deplete, performance throttles to baseline.

---

### Q10: How does the application connect to PostgreSQL securely?

**Answer:**  
The connection string format:
```
postgresql://skillhiveadmin:Postgres1%402026@skillhive-accenture-pg.postgres.database.azure.com:5432/skillhive?sslmode=require
```

Security layers:
1. **SSL/TLS Required:** `sslmode=require` enforces encrypted transport.
2. **Firewall Rules:** `AllowAzureServices` (0.0.0.0/0.0.0.0) permits only Azure-internal traffic.
3. **Password in App Settings:** Stored as environment variable, not in code.
4. **URL Encoding:** Special characters in passwords (like `@`) must be percent-encoded (`%40`).
5. **psycopg2-binary:** Python driver that supports SSL natively.

---

### Q11: How does Flask-Migrate (Alembic) handle database migrations?

**Answer:**  
Flask-Migrate wraps Alembic for database schema versioning:

```bash
flask db init          # Create migrations directory (one-time)
flask db migrate -m "Add new column"  # Auto-generate migration script
flask db upgrade       # Apply pending migrations to database
flask db downgrade     # Rollback last migration
```

In SkillHive, we use `db.create_all()` in the app factory for initial setup (creates tables if they don't exist). For production schema changes, Flask-Migrate provides:
- **Version-controlled** migration scripts.
- **Reversible** schema changes.
- **Auto-detection** of model changes.

---

## 3. Azure Blob Storage

### Q12: Why use Azure Blob Storage instead of storing files on the App Service filesystem?

**Answer:**  

| Aspect              | App Service Filesystem        | Azure Blob Storage              |
|---------------------|-------------------------------|----------------------------------|
| **Persistence**     | Lost on redeployment/scale    | Permanent, independent of compute |
| **Scalability**     | Limited to disk size          | Virtually unlimited (5 PB/account) |
| **Cost**            | Included in plan but limited  | ~$0.018/GB/month (Hot LRS)       |
| **CDN Integration** | Not built-in                  | Seamless CDN integration         |
| **Concurrent Access**| Single instance only          | Multi-instance safe              |
| **SAS Tokens**      | N/A                           | Time-limited secure access URLs  |

For SkillHive, resumes must survive redeployments and be accessible if the app scales to multiple instances. Blob Storage provides this durability.

---

### Q13: Explain the resume upload flow in SkillHive.

**Answer:**  
```
User submits form with .docx/.pptx file
         │
         ▼
┌─────────────────────────────┐
│  1. Validate file extension │  (.docx, .pptx only)
│  2. Check size < 10 MB      │
│  3. Sanitize filename        │  (secure_filename)
│  4. Generate unique name     │  resume_{demand}_{user}_{uuid8}.ext
└──────────────┬──────────────┘
               │
      ┌────────┴────────────┐
      │ DEV_MODE?           │
      │                     │
   Yes│                  No │
      ▼                     ▼
┌───────────┐      ┌──────────────────┐
│ Save to   │      │ BlobServiceClient │
│ local     │      │ .from_connection_ │
│ uploads/  │      │  string()         │
│ directory │      │ Upload to         │
│           │      │ "resumes" container│
└───────────┘      └──────────────────┘
                          │
                   Store blob URL in
                   Application.resume_blob_url
```

Key code pattern:
```python
from azure.storage.blob import BlobServiceClient

blob_service = BlobServiceClient.from_connection_string(conn_str)
container_client = blob_service.get_container_client("resumes")
blob_client = container_client.get_blob_client(unique_filename)
blob_client.upload_blob(file.read(), overwrite=True)
blob_url = blob_client.url  # Stored in DB
```

Fallback: If Blob upload fails, the system gracefully falls back to local storage.

---

### Q14: What are the different Blob Storage access tiers?

**Answer:**  

| Tier     | Access Frequency | Storage Cost | Access Cost | Use Case                        |
|----------|------------------|--------------|-------------|---------------------------------|
| **Hot**  | Frequent         | Higher       | Lower       | Active data, frequently accessed |
| **Cool** | Infrequent       | Lower        | Higher      | 30+ day retention, backups       |
| **Cold** | Rare             | Even Lower   | Even Higher | 90+ day retention                |
| **Archive** | Rare/Compliance| Lowest       | Highest     | Long-term archive, compliance    |

SkillHive uses Hot tier (default for StorageV2) since resumes are accessed by evaluators shortly after upload.

---

### Q15: What is the difference between StorageV1 and StorageV2?

**Answer:**  
- **StorageV2 (General Purpose v2):** Recommended for all scenarios. Supports Blob, File, Queue, Table. Supports access tiers (Hot/Cool/Cold/Archive). Lower transaction costs.
- **StorageV1 (General Purpose v1):** Legacy. No access tiers for blobs. May be cheaper for specific classic workloads.
- SkillHive uses **StorageV2** — it's the Azure-recommended default for all new storage accounts.

---

### Q16: What redundancy options are available? Why did you choose LRS?

**Answer:**  

| Redundancy | Copies | Durability         | Use Case                        |
|------------|--------|--------------------|---------------------------------|
| **LRS** (Locally Redundant) | 3 copies in one datacenter | 99.999999999% | Dev/test, non-critical |
| **ZRS** (Zone Redundant)    | 3 copies across 3 zones   | 99.9999999999% | HA within region       |
| **GRS** (Geo Redundant)     | 6 copies (3 local + 3 paired region) | 16 9's | DR across regions |
| **RA-GRS** (Read-Access GRS)| 6 copies + read access to secondary | 16 9's | Read HA + DR     |

We chose **LRS** because:
- Resumes are non-critical documents (originals exist with the employee).
- LRS is the **cheapest** option (~$0.018/GB/month for Hot).
- For production at scale, upgrade to **ZRS** or **GRS** for better durability.

---

## 4. Azure Application Insights

### Q17: What is Application Insights and how is it used in SkillHive?

**Answer:**  
Application Insights is an **Application Performance Management (APM)** service that provides:

- **Request Telemetry:** Track every HTTP request (duration, status code, URL).
- **Exception Tracking:** Auto-capture unhandled exceptions with stack traces.
- **Dependency Tracking:** Monitor calls to PostgreSQL, Blob Storage, SMTP.
- **Custom Metrics:** Track business metrics (demands created, applications count).
- **Live Metrics:** Real-time request rate, failure rate, resource utilization.
- **Application Map:** Visual dependency graph of service interactions.

In SkillHive:
- The **Instrumentation Key** is injected via App Settings.
- Azure App Service auto-collects basic HTTP telemetry.
- Application logs are forwarded to the linked Log Analytics Workspace.
- Used for diagnosing production issues (500 errors, slow queries, deployment health).

---

### Q18: What is the difference between Instrumentation Key and Connection String?

**Answer:**  
- **Instrumentation Key (ikey):** A GUID used traditionally to identify the AI resource. Being deprecated in favor of Connection String.
- **Connection String:** Contains the ikey plus the ingestion endpoint URL. Recommended for new setups as it's more flexible (supports regional endpoints, private link).

Example:
```
InstrumentationKey=abc123;IngestionEndpoint=https://centralindia-0.in.applicationinsights.azure.com/
```

SkillHive currently uses the ikey (`APPINSIGHTS_INSTRUMENTATIONKEY`). For enhanced monitoring, migrate to Connection String with `azure-monitor-opentelemetry` SDK.

---

### Q19: How would you set up alerting in Application Insights?

**Answer:**  
Configure **Alert Rules** in Azure Portal:

1. **Metric Alerts:**
   - Server response time > 5 seconds → Email/SMS notification
   - Failed requests (5xx) > 10 in 5 minutes → PagerDuty/Slack webhook
   - Exception count > 0 → Immediate alert

2. **Log-based Alerts (KQL):**
   ```kusto
   requests
   | where resultCode >= 500
   | summarize count() by bin(timestamp, 5m)
   | where count_ > 10
   ```

3. **Smart Detection:** AI-powered anomaly detection for:
   - Response time degradation
   - Failure rate increases
   - Memory leaks

4. **Action Groups:** Define notification channels (email, SMS, webhook, Azure Function, Logic App).

---

## 5. Azure Log Analytics Workspace

### Q20: What is Log Analytics Workspace and how does it relate to Application Insights?

**Answer:**  
Log Analytics Workspace is a **centralized log data store** in Azure Monitor. It:

- Stores log data from Application Insights, Azure resources, VMs, containers.
- Uses **Kusto Query Language (KQL)** for powerful log analysis.
- Supports **retention policies** (30 days default in SkillHive).
- Enables **cross-resource queries** (correlate app logs with database metrics).

Relationship with Application Insights:
- Modern Application Insights is **workspace-based** (logs stored in Log Analytics).
- Classic Application Insights had its own storage (deprecated).
- SkillHive's ARM template links them: AI resource → Log Analytics Workspace.

---

### Q21: Write a KQL query to find the slowest API endpoints in SkillHive.

**Answer:**  
```kusto
requests
| where timestamp > ago(24h)
| where success == true
| summarize 
    avg_duration = avg(duration),
    p95_duration = percentile(duration, 95),
    request_count = count()
  by name
| order by p95_duration desc
| take 10
```

This returns the top 10 slowest endpoints by P95 response time in the last 24 hours.

---

### Q22: How would you query failed requests for the demands module?

**Answer:**  
```kusto
requests
| where timestamp > ago(7d)
| where success == false
| where url contains "/demands/"
| project timestamp, url, resultCode, duration, 
          operation_Id, client_IP
| order by timestamp desc
| take 50
```

To correlate with exceptions:
```kusto
exceptions
| where timestamp > ago(7d)
| where operation_Name contains "demands"
| project timestamp, type, message, outerMessage, 
          innermostMessage, operation_Id
| order by timestamp desc
```

---

## 6. Azure Resource Manager (ARM) Templates

### Q23: What are ARM templates and why did you use them for SkillHive?

**Answer:**  
ARM templates are **JSON-based Infrastructure-as-Code (IaC)** files that declaratively define Azure resources. Benefits:

1. **Repeatability:** Deploy identical environments (dev/staging/prod) from the same template.
2. **Version Control:** Templates stored in Git alongside application code.
3. **Idempotent:** Running the same deployment multiple times doesn't create duplicates.
4. **Dependency Management:** `dependsOn` ensures resources deploy in correct order.
5. **Parameterized:** Passwords, names, regions are parameters — not hardcoded.
6. **Complete Deployment:** All 8 resources provisioned in a single `az deployment group create` command.

SkillHive's ARM template provisions: App Service Plan, App Service, PostgreSQL Flexible Server + Database + Firewall Rule, Storage Account, Application Insights, Log Analytics Workspace.

---

### Q24: Explain the ARM template structure used in SkillHive.

**Answer:**  
```json
{
  "$schema": "...",            // ARM schema URL (validates template)
  "contentVersion": "1.0.0.0", // Template version
  "metadata": {},              // Description, SSO notes
  "parameters": {             // User inputs at deploy time
    "appName": {},
    "postgresAdminPassword": {"type": "securestring"} // Encrypted
  },
  "variables": {              // Computed names
    "planName": "[concat(parameters('appName'), '-plan')]"
  },
  "resources": [              // 8 Azure resources defined
    // Log Analytics → App Insights → App Service Plan → 
    // App Service → PostgreSQL → DB → Firewall → Storage
  ],
  "outputs": {                // Return values after deployment
    "webAppUrl": "..."
  }
}
```

Key ARM functions used:
- `concat()` — String concatenation for naming.
- `uniqueString()` — Deterministic hash for SECRET_KEY.
- `resourceId()` — Get resource ID for dependency references.
- `reference()` — Get properties of deployed resources (e.g., App Insights ikey).
- `listKeys()` — Retrieve storage account access keys.

---

### Q25: What is the difference between ARM templates, Bicep, and Terraform?

**Answer:**  

| Aspect           | ARM Templates       | Bicep                  | Terraform                |
|------------------|---------------------|------------------------|--------------------------|
| **Language**     | JSON (verbose)      | DSL (concise, transpiles to ARM) | HCL                |
| **Provider**     | Azure-native        | Azure-native           | Multi-cloud              |
| **State File**   | No (Azure manages)  | No (Azure manages)     | Yes (terraform.tfstate)  |
| **Learning Curve**| Moderate           | Lower                  | Moderate                 |
| **Modularity**   | Linked templates    | Modules                | Modules                  |
| **Tooling**      | Azure CLI/Portal    | Azure CLI + VS Code ext| Terraform CLI            |

We used ARM templates because:
- **No additional tooling** required (works with `az deployment group create`).
- **Native Azure format** — the Portal understanding and generates ARM.
- For new projects, **Bicep** is recommended (same capability, cleaner syntax).

---

### Q26: How do you handle secrets in ARM templates?

**Answer:**  
1. **`securestring` parameter type:** Values never logged, never visible in deployment history.
   ```json
   "postgresAdminPassword": { "type": "securestring" }
   ```
2. **Key Vault references:** Reference secrets from Azure Key Vault at deploy time:
   ```json
   "adminPassword": {
     "reference": {
       "keyVault": { "id": "/subscriptions/.../vaults/myVault" },
       "secretName": "dbPassword"
     }
   }
   ```
3. **Parameter files:** Use `.parameters.json` with Key Vault references (never commit plaintext passwords).
4. **Function-generated values:** `uniqueString()` for non-secret unique identifiers.

SkillHive uses `securestring` for `postgresAdminPassword` and `mailPassword`.

---

## 7. Azure App Service Build & Deployment (Oryx)

### Q27: What is Oryx? How does it build Python applications?

**Answer:**  
**Oryx** is Microsoft's **open-source build system** for Azure App Service. It auto-detects the application framework and builds it:

Python build process:
1. **Detection:** Finds `requirements.txt` or `setup.py` → identifies Python project.
2. **Runtime Selection:** Reads `linuxFxVersion: PYTHON|3.11` from App Service config.
3. **Virtual Environment:** Creates `/home/site/wwwroot/antenv/` (or specified name).
4. **Dependency Install:** `pip install -r requirements.txt` inside the venv.
5. **Compression:** Packages the build into `output.tar.gz` for faster deployment.
6. **Extraction:** On app startup, extracts the archive to serve the application.

Triggered by `SCM_DO_BUILD_DURING_DEPLOYMENT=true` app setting.

---

### Q28: What deployment methods are available for Azure App Service?

**Answer:**  

| Method             | Command / Tool                    | Best For                          |
|--------------------|-----------------------------------|-----------------------------------|
| **Zip Deploy**     | `az webapp deploy --src-path app.zip` | CI/CD pipelines, manual deploys |
| **Git Deploy**     | `git push azure main`            | Simple projects, direct push      |
| **GitHub Actions** | `.github/workflows/deploy.yml`   | Automated CI/CD                   |
| **Azure DevOps**   | Pipeline YAML                    | Enterprise CI/CD                  |
| **FTP/SFTP**       | FileZilla, WinSCP                | Legacy, not recommended           |
| **VS Code**        | Azure App Service extension      | Developer convenience             |
| **Azure CLI**      | `az webapp up`                   | Quick one-command deploy          |
| **Container**      | Docker image from ACR            | Custom runtime environments       |

SkillHive uses **Zip Deploy** via `az webapp deploy` from Cloud Shell.

---

### Q29: What is the Kudu SCM site and how do you use it for debugging?

**Answer:**  
Kudu is the **deployment engine** for App Service, accessible at `https://{app-name}.scm.azurewebsites.net`. It provides:

1. **SSH Console:** Run commands directly in the container (`/home/site/wwwroot/`).
2. **Process Explorer:** View running processes, memory, CPU.
3. **Log Stream:** Real-time application log output.
4. **REST API:** Programmatic access to deployments, logs, process info.
5. **Environment Variables:** View all app settings and connection strings.
6. **File Browser:** Navigate and edit files on the container filesystem.

In SkillHive, we used SSH to:
- Manually extract `output.tar.gz` after Oryx build.
- Activate the virtual environment (`source antenv/bin/activate`).
- Seed database users via Python scripts.
- Debug `ModuleNotFoundError` and connection issues.

---

## 8. Azure Identity & Authentication

### Q30: What Azure AD / Entra ID authentication options exist for web apps?

**Answer:**  

| Option                        | Implementation                          | Use Case                        |
|-------------------------------|------------------------------------------|---------------------------------|
| **Azure AD (MSAL)**          | Application Registration + MSAL SDK     | Enterprise SSO, corporate tenants |
| **Easy Auth**                | Built-in App Service Authentication     | Zero-code auth for simple apps   |
| **Azure AD B2C**             | Customer-facing identity management     | External users (consumers)       |
| **Managed Identity**         | No credentials needed for Azure services| Service-to-service auth          |

SkillHive was originally designed for **MSAL-based SSO** with Azure AD App Registration, but was **switched to database-based email/password authentication** due to corporate tenant restrictions. The SSO code is preserved as comments for future re-enablement.

---

### Q31: What is Managed Identity? How could SkillHive use it?

**Answer:**  
Managed Identity provides an **Azure AD identity for the App Service** — no credentials stored in code or config.

Types:
- **System-assigned:** Created with the resource, deleted when resource is deleted.
- **User-assigned:** Independent lifecycle, can be shared across resources.

SkillHive could use Managed Identity for:
1. **PostgreSQL Authentication:** Passwordless connection using AAD token auth (replaces connection string password).
2. **Blob Storage Access:** Use `DefaultAzureCredential` instead of storage account keys.
3. **Key Vault Access:** Retrieve secrets dynamically at runtime.

**Example (Blob Storage with Managed Identity):**
```python
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

credential = DefaultAzureCredential()
blob_service = BlobServiceClient(
    account_url="https://skillhivestore.blob.core.windows.net",
    credential=credential
)
```

This eliminates the `AZURE_STORAGE_CONNECTION_STRING` secret entirely.

---

### Q32: Explain the difference between `azure-identity` and MSAL (msal4py).

**Answer:**  

| Aspect           | azure-identity                     | MSAL (msal4py)                    |
|------------------|------------------------------------|------------------------------------|
| **Purpose**      | Azure service authentication       | User authentication (OAuth2/OIDC)  |
| **Use Case**     | App → Azure resources              | User → App (SSO login)            |
| **Credential**   | DefaultAzureCredential (chain)     | ConfidentialClientApplication      |
| **Flows**        | Client credentials, managed identity | Auth code, device code, client cred |
| **Token Target** | Azure Resource Manager, Storage, etc. | Microsoft Graph, custom APIs      |

SkillHive includes `azure-identity` for Blob Storage access, and had `msal` (commented out) for Azure AD SSO.

---

## 9. Azure Networking & Security in App Service

### Q33: How do you secure an App Service for production workloads?

**Answer:**  

1. **HTTPS Only:** `httpsOnly: true` — redirects HTTP to HTTPS.
2. **TLS 1.2 Minimum:** Enforce minimum TLS version.
3. **IP Restrictions:** Whitelist corporate IPs or VPN ranges.
4. **VNet Integration:** Route outbound traffic through a VNet.
5. **Private Endpoints:** Make the app accessible only within a VNet.
6. **Managed Identity:** Eliminate credential storage.
7. **Key Vault References:** Store secrets in Key Vault, reference in App Settings.
8. **CORS Configuration:** Restrict allowed origins for API endpoints.
9. **Custom Domain + SSL:** Use organization's domain with managed certificate.
10. **Authentication:** Enable App Service Authentication or in-app auth.

SkillHive implements: HTTPS enforced, TLS 1.2, database SSL, CSRF protection, password hashing, input validation.

---

### Q34: How does the PostgreSQL firewall rule `AllowAzureServices` work?

**Answer:**  
The firewall rule with `startIpAddress: 0.0.0.0` and `endIpAddress: 0.0.0.0` is a **special Azure rule** that:
- Allows connections from **any Azure service** (including App Service).
- Does NOT allow connections from the public internet.
- Is the simplest way to enable App Service → PostgreSQL connectivity.

**More secure alternative:** Use **VNet Integration** + **Private Endpoint** for PostgreSQL, which:
- Routes traffic through a private network.
- No public internet exposure for the database.
- Requires Standard/Premium App Service Plan.

---

## 10. Cross-Service Integration Scenarios

### Q35: Describe the end-to-end flow when a resource applies for a demand.

**Answer:**  
```
1. [Browser] User fills application form + uploads resume
                    │
2. [App Service/Flask] Validate form (WTForms) + authenticate (Flask-Login)
                    │
3. [App Service/Python] Generate unique filename + upload resume
                    │
          ┌─────────┴──────────┐
          │ Production         │ Development
          ▼                    ▼
4a. [Blob Storage]          4b. [Local Disk]
    Upload .docx to             Save to uploads/
    "resumes" container
          │
5. [PostgreSQL] INSERT Application record + ApplicationHistory audit entry
          │
6. [PostgreSQL] UPDATE Demand status → 'in_progress'
          │
7. [SMTP/Office 365] Send email notification to:
     - Demand raiser (PMO user)
     - Evaluator (from demand record)
          │
8. [App Insights] Log request telemetry (duration, status, URL)
          │
9. [Browser] Flash success message, redirect to My Applications
```

This single user action touches **5 Azure services** (App Service, PostgreSQL, Blob Storage, SMTP, Application Insights).

---

### Q36: How do you handle failures across multiple services?

**Answer:**  
SkillHive uses a **graceful degradation** pattern:

1. **Email failures are non-blocking:**
   ```python
   try:
       send_application_notification(application, demand)
   except Exception as e:
       current_app.logger.warning(f"Failed to send email: {e}")
   # Application is still saved even if email fails
   ```

2. **Blob upload fallback:**
   ```python
   try:
       # Upload to Azure Blob Storage
       blob_client.upload_blob(file.read())
   except Exception:
       # Fallback to local filesystem
       file.save(local_path)
   ```

3. **Database errors rollback:**
   ```python
   try:
       db.session.add(application)
       db.session.commit()
   except Exception:
       db.session.rollback()
       flash('Failed to submit application.', 'danger')
   ```

4. **Application Insights degraded gracefully** — if instrumentation key is missing, app runs without monitoring.

---

### Q37: How would you implement a notification to Microsoft Teams when a new demand is created?

**Answer:**  
Use **Azure Functions** (serverless) with an **HTTP trigger** or **Event Grid trigger**:

**Option 1: Direct Webhook from Flask**
```python
import requests

def notify_teams(demand):
    webhook_url = os.environ.get('TEAMS_WEBHOOK_URL')
    card = {
        "@type": "MessageCard",
        "summary": f"New Demand: {demand.project_name}",
        "sections": [{
            "activityTitle": f"New Demand: {demand.project_name}",
            "facts": [
                {"name": "DU", "value": demand.du_name},
                {"name": "Skills", "value": demand.skills_display},
                {"name": "Priority", "value": demand.priority.upper()},
            ]
        }]
    }
    requests.post(webhook_url, json=card)
```

**Option 2: Azure Function (decoupled)**
- Flask sends event to Azure Service Bus / Event Grid.
- Azure Function triggers on the event.
- Function posts Adaptive Card to Teams via webhook.
- Benefit: Decoupled, retries on failure, no latency for the user.

SkillHive has a `functions/teams_notification/` directory placeholder for this future integration.

---

## 11. Troubleshooting & Real-World Scenarios

### Q38: The deployment succeeded but the app shows "Application Error". How do you debug?

**Answer:**  
Step-by-step debugging:

1. **Check App Service Logs:**
   ```bash
   az webapp log tail --name skillhive-accenture --resource-group rg-skillhive
   ```

2. **Check Startup Logs in Kudu:**
   - Go to `https://skillhive-accenture.scm.azurewebsites.net`
   - Navigate to Log stream → Docker logs

3. **Common Exit Codes:**
   - **Exit Code 127:** Command not found (gunicorn not installed → `SCM_DO_BUILD_DURING_DEPLOYMENT=true`).
   - **Exit Code 3:** Gunicorn worker boot failure (module import error, DB connection failure).
   - **Exit Code 1:** General Python exception during startup.

4. **SSH into the container:**
   ```bash
   az webapp ssh --name skillhive-accenture --resource-group rg-skillhive
   cd /home/site/wwwroot
   source antenv/bin/activate
   python -c "from app import create_app; app = create_app('production')"
   ```

5. **Check if build output was extracted:**
   ```bash
   ls -la /home/site/wwwroot/
   # If only output.tar.gz exists, run:
   tar xzf output.tar.gz
   ```

---

### Q39: The database connection fails with "password authentication failed". What do you check?

**Answer:**  

1. **Special characters in password:** If password contains `@`, `#`, `/`, etc., they must be **URL-encoded** in the connection string.
   - `@` → `%40`, `#` → `%23`, `/` → `%2F`
   - Example: `Postgres1@2026` → `Postgres1%402026`

2. **Firewall rules:** Ensure "Allow Azure Services" is enabled or the App Service outbound IPs are whitelisted.

3. **SSL mode:** Connection string must include `?sslmode=require`.

4. **Username format:** For Flexible Server, just the username (e.g., `skillhiveadmin`). For Single Server, use `user@servername`.

5. **Server name:** Must be the FQDN: `servername.postgres.database.azure.com`.

6. **Test from SSH:**
   ```bash
   psql "postgresql://skillhiveadmin:Postgres1%402026@skillhive-accenture-pg.postgres.database.azure.com:5432/skillhive?sslmode=require"
   ```

---

### Q40: How do you monitor and optimize query performance?

**Answer:**  

1. **Flask-SQLAlchemy logging:** Set `SQLALCHEMY_ECHO=True` to log all SQL queries.

2. **Application Insights dependencies:** Track database call durations in the Dependencies blade.

3. **PostgreSQL Query Store:** Enable on Flexible Server to track slow queries:
   ```sql
   SELECT * FROM pg_stat_statements 
   ORDER BY total_exec_time DESC 
   LIMIT 10;
   ```

4. **Index optimization:** Add indexes on frequently filtered columns:
   ```python
   email = db.Column(db.String(255), index=True)  # Already indexed
   status = db.Column(db.String(20), index=True)   # Already indexed
   ```

5. **Connection pooling:** SQLAlchemy's default pool (QueuePool, size=5) is sufficient for B1ms. For higher load, configure:
   ```python
   SQLALCHEMY_POOL_SIZE = 10
   SQLALCHEMY_MAX_OVERFLOW = 20
   ```

---

### Q41: A user reports "500 Internal Server Error" on the demand export page. Walk through your investigation.

**Answer:**  

1. **Application Insights → Failures blade:** Filter by URL `/demands/export`, look at exception details.

2. **KQL Query:**
   ```kusto
   exceptions
   | where timestamp > ago(1h)
   | where operation_Name == "GET /demands/export"
   | project timestamp, type, innermostMessage, details
   ```

3. **Common causes for export failures:**
   - **Memory:** Large Excel file exceeds B1's 1.75 GB RAM → paginate export.
   - **Timeout:** Gunicorn's 600s timeout exceeded → optimize query or stream response.
   - **openpyxl version:** Incompatible version → check `requirements.txt`.
   - **Database connection:** Pool exhausted → increase pool size or check for leaked connections.

4. **Fix:** If memory is the issue, implement streaming Excel generation:
   ```python
   from flask import Response, stream_with_context
   def export_large():
       def generate():
           # Yield Excel chunks
           yield workbook_chunk
       return Response(stream_with_context(generate()))
   ```

---

### Q42: How would you scale SkillHive to handle 1,000+ concurrent users?

**Answer:**  

| Layer           | Current                  | Scaled                                    |
|-----------------|--------------------------|--------------------------------------------|
| **App Service** | B1 (1 instance)          | P1v3 + Auto-scale (2–10 instances)        |
| **Database**    | B1ms Burstable           | GP (D2ds_v4) + Read replicas              |
| **Storage**     | LRS                      | ZRS + CDN for resume downloads             |
| **Caching**     | None                     | Azure Cache for Redis (session + skill data)|
| **Search**      | SQL LIKE queries         | Azure AI Search for full-text              |
| **Monitoring**  | Basic App Insights       | + Dashboards + Alert Rules + Workbooks     |
| **Session**     | Server-side (memory)     | Redis-backed sessions (multi-instance safe)|
| **Email**       | Direct SMTP from app     | Azure Communication Services or SendGrid   |
| **CI/CD**       | Manual zip deploy        | GitHub Actions with staging slots           |

Key architectural changes:
1. **Add Redis** for session storage and skill taxonomy caching.
2. **Use deployment slots** for zero-downtime deployments.
3. **VNet Integration** + **Private Endpoints** for database security.
4. **Azure Front Door / CDN** for global access and DDoS protection.
5. **Managed Identity** to eliminate all stored credentials.

---

### Q43: Compare Azure Communication Services vs SendGrid vs SMTP for email.

**Answer:**  

| Feature               | Office 365 SMTP         | Azure Communication Services | SendGrid (Azure)        |
|-----------------------|-------------------------|------------------------------|-------------------------|
| **Cost**              | Included with O365 license | Pay-per-message ($0.0025/email) | Free tier: 25K/month |
| **Setup Complexity**  | Low (standard SMTP)     | Moderate (SDK + domain verify) | Low (API key + SDK)    |
| **Sending Limit**     | 10,000/day per mailbox  | Scalable                     | Tiered                  |
| **Deliverability**    | Good (O365 reputation)  | Good (Azure managed)         | Excellent (dedicated IP)|
| **SDK**               | SMTP (any language)     | Python SDK available         | REST API + SDKs         |
| **Custom Domain**     | Via O365                | Required (DNS verification)  | Supported               |

SkillHive uses **Office 365 SMTP** — simplest option leveraging existing corporate email infrastructure. For high-volume production, migrate to **Azure Communication Services** or **SendGrid**.

---

### Q44: What is the Azure Well-Architected Framework? How does SkillHive align?

**Answer:**  
The Azure Well-Architected Framework has **5 pillars:**

| Pillar                | SkillHive Implementation                                    |
|-----------------------|-------------------------------------------------------------|
| **Reliability**       | Database backup (7-day), graceful error handling, health checks |
| **Security**          | HTTPS, SSL DB, CSRF, password hashing, input validation, RBAC |
| **Cost Optimization** | Burstable B1ms (DB), B1 (app), LRS storage — optimized for internal tool budget |
| **Operational Excellence** | Application Insights, Log Analytics, ARM IaC, structured logging |
| **Performance Efficiency** | Gunicorn multi-worker, SQLAlchemy connection pooling, Always On |

**Areas for improvement:**
- Add Azure Key Vault for secret management (Security pillar).
- Implement auto-scaling (Reliability + Performance).
- Add deployment slots (Operational Excellence).
- Implement caching with Redis (Performance).

---

### Q45: How do you estimate the monthly cost for SkillHive's Azure infrastructure?

**Answer:**  

| Resource                        | SKU              | Estimated Monthly Cost |
|---------------------------------|------------------|------------------------|
| App Service Plan (B1)           | Linux B1         | ~$13                   |
| PostgreSQL Flexible (B1ms)      | Burstable, 32GB  | ~$18                   |
| Storage Account (Hot LRS)       | < 1 GB data      | ~$0.50                 |
| Application Insights            | < 5 GB/month     | Free (first 5 GB)     |
| Log Analytics Workspace         | < 5 GB/month     | Free (first 5 GB)     |
| **Total Estimated**             |                  | **~$31.50/month**      |

This makes SkillHive extremely cost-effective for an internal DU tool. Scaling to Standard tier with more resources would increase to ~$80–120/month.

---

*End of Original Guide (v1.0 — Q1–Q45)*

---

## 12. Bulk Excel Upload & Resource Evaluation (v1.1)

> **Added:** February 13, 2026 — Questions covering the new PMO bulk-upload and evaluator feedback workflow.

---

### Q46: Explain the Resource Upload feature and the PMO → Evaluator workflow.

**Answer:**  
SkillHive now supports a **Supply Management** workflow alongside the existing Demand pipeline:

```
PMO prepares Excel list       PMO uploads Excel         Evaluators review &
of available resources  ──►  via SkillHive UI      ──►  evaluate resources
(bench/joiners)              (linked to a Demand/RRD)   (select / reject)
                                                              │
                                                              ▼
                                                     PMO reviews feedback
                                                     & manages/closes RRD
```

Workflow steps:
1. **PMO creates a Demand** with an RRD identifier (e.g., `RRD-2024-001`).
2. **PMO uploads an Excel file** (`.xlsx`) containing available resources (bench employees, joiners) against that demand.
3. The system **parses the Excel**, maps columns to model fields using flexible header matching, and stores each row as a `Resource` record linked to the demand.
4. **Evaluators** see the resource list with contact details — email (mailto: links with pre-filled JD) and phone (tel: links).
5. Evaluators **open an evaluation modal** and set the status (`Pending → Under Evaluation → Selected / Rejected`) with remarks.
6. **PMO views** evaluation feedback (status counts, remarks) on the demand detail page and the full resource list.
7. PMO can **export** the resource list with evaluation data back to Excel.

---

### Q47: How does the Excel parsing and flexible header mapping work?

**Answer:**  
The upload uses `openpyxl` (already in the project for export) to read the uploaded `.xlsx` file. The key design challenge is that PMOs may use **different header names** for the same column (e.g., `E_MAIL_ADDRESS` vs `EMAIL` vs `E MAIL ADDRESS`).

Solution — a **HEADER_MAP dictionary** with normalized lookup:

```python
HEADER_MAP = {
    'PERSONNEL_NO': 'personnel_no',
    'PRE HIRE ID': 'personnel_no',
    'PERSONNEL_NO/PRE HIRE ID': 'personnel_no',
    'NAME': 'name',
    'EMPLOYEE_PRIMARY_SKILL': 'primary_skill',
    'EMPLOYEE PRIMARY SKILL': 'primary_skill',
    'E_MAIL_ADDRESS': 'email',
    'EMAIL': 'email',
    'EMAIL ADDRESS': 'email',
    # ... more mappings
}

def _match_header(header_text):
    normalized = header_text.strip().upper()
    # 1. Exact match
    if normalized in HEADER_MAP:
        return HEADER_MAP[normalized]
    # 2. Partial / contains match (fallback)
    for key, field in HEADER_MAP.items():
        if key in normalized or normalized in key:
            return field
    return None
```

Parsing flow:
1. Read row 1 as headers → build `field_map` (column index → model field).
2. Iterate remaining rows → build a dict per row using `field_map`.
3. Skip rows without a `name` value (required field).
4. Create `Resource` objects and bulk-insert.
5. Count successes/errors and flash a summary message.

This approach handles real-world Excel files that rarely have perfectly consistent headers.

---

### Q48: Describe the Resource model and its relationship to the Demand model.

**Answer:**  
The `Resource` model represents an available person (supply) uploaded against a demand (RRD):

```python
class Resource(db.Model):
    __tablename__ = 'resources'

    id              = db.Column(db.Integer, primary_key=True)
    demand_id       = db.Column(db.Integer, ForeignKey('demands.id', ondelete='CASCADE'))

    # From Excel upload
    personnel_no        = db.Column(db.String(50))
    name                = db.Column(db.String(255), nullable=False)
    primary_skill       = db.Column(db.String(255))
    management_level    = db.Column(db.String(50))
    home_location       = db.Column(db.String(255))
    lock_status         = db.Column(db.String(100))
    availability_status = db.Column(db.String(100))   # e.g. "On bench"
    email               = db.Column(db.String(255))
    contact_details     = db.Column(db.String(100))
    joining_date        = db.Column(db.String(100))

    # Evaluation workflow
    evaluation_status   = db.Column(db.String(20), default='pending')
    evaluation_remarks  = db.Column(db.Text)
    evaluated_by        = db.Column(db.Integer, ForeignKey('users.id'))
    evaluated_at        = db.Column(db.DateTime)

    # Metadata
    uploaded_by         = db.Column(db.Integer, ForeignKey('users.id'))
    uploaded_at         = db.Column(db.DateTime, default=utcnow)
```

Relationships:
- **Demand ↔ Resource** — One-to-Many (`demand.resources`, cascade delete)
- **User ↔ Resource (evaluator)** — Many-to-One (`resource.evaluator`)
- **User ↔ Resource (uploader)** — Many-to-One (`resource.uploader`)

The `Demand` model gains a `resource_count` property:
```python
@property
def resource_count(self):
    return self.resources.count()
```

Database migration (`003_add_resources_table.sql`) creates the table with indexes on `demand_id` and `evaluation_status`.

---

### Q49: Why store `availability_status` and `joining_date` as strings instead of date/datetime?

**Answer:**  
The Excel data from the PMO contains **mixed-format values** in these columns:

- **ROLL_OFF_DATE column** often contains text like `"On bench"`, `"On notice"`, `"Available from March"` — not actual dates.
- **Joining Date** may be `"15-Jan-2026"`, `"Not mandatory"`, or blank.

Storing as `VARCHAR(100)` (String) is a deliberate design choice:
1. **No data loss:** Text values aren't discarded by date parsing failures.
2. **No upload errors:** PMOs don't need to reformat their Excel files.
3. **Display-friendly:** Values are shown exactly as the PMO entered them.

If strict date handling is needed later, a migration can parse and split the field into a `Date` column plus a separate `availability_notes` text field.

---

### Q50: How does the evaluation workflow work? Describe the status transitions.

**Answer:**  
The evaluation follows a simple state machine:

```
          ┌──────────────────────────────────────┐
          │                                      │
    ┌─────▼─────┐     ┌──────────────────┐       │
    │  Pending   │────►│ Under Evaluation │───┐   │
    │ (default)  │     └──────────────────┘   │   │
    └────────────┘              │              │   │
          │                    │              │   │
          │         ┌─────────┴─────────┐     │   │
          │         ▼                   ▼     │   │
          │   ┌──────────┐      ┌──────────┐  │   │
          └──►│ Selected │      │ Rejected │◄─┘   │
              │    ✅     │      │    ❌     │      │
              └──────────┘      └──────────┘      │
                   │                  │            │
                   └──────────────────┴────────────┘
                     (can be re-evaluated)
```

Implementation:
- Evaluator clicks the pencil icon on a resource row → Bootstrap modal opens.
- Modal pre-selects the current status and shows existing remarks.
- On submit, a `POST` request to `/resources/<id>/evaluate` updates the record.
- `evaluated_by` and `evaluated_at` are set to the current user and UTC timestamp.
- Status is **not locked** — evaluators can change from `rejected` back to `under_evaluation` if needed.

Access control:
- **PMO, Evaluator, Admin** can evaluate resources.
- Only **PMO** can upload or delete resources.

---

### Q51: How do the email and phone contact features work for evaluators?

**Answer:**  
The resource list template provides **clickable contact buttons** so evaluators can quickly reach out to resources:

**Email (mailto: link with pre-filled JD):**
```html
<a href="mailto:{{ r.email }}
    ?subject=Opportunity: {{ demand.project_name }} ({{ demand.rrd }})
    &body=Hi {{ r.name }},%0D%0A%0D%0A
    We have an open role that matches your profile:%0D%0A%0D%0A
    Project: {{ demand.project_name }}%0D%0A
    RRD: {{ demand.rrd }}%0D%0A
    Skills: {{ demand.skills|join(', ', attribute='name') }}%0D%0A%0D%0A
    Please let us know your availability.%0D%0A%0D%0ARegards">
    <i class="bi bi-envelope"></i>
</a>
```

This opens the user's default email client (Outlook) with:
- **To:** Resource's email address
- **Subject:** Pre-filled with the project name and RRD
- **Body:** Pre-filled with a template containing the JD details

**Phone (tel: link):**
```html
<a href="tel:{{ r.contact_details }}">
    <i class="bi bi-telephone"></i>
</a>
```

This triggers the dialer on mobile devices or softphone on desktop.

Both buttons use Bootstrap tooltips to show the contact details on hover.

---

### Q52: How does the drag-and-drop file upload work on the upload page?

**Answer:**  
The upload page uses **native HTML5 Drag-and-Drop API** combined with a hidden `<input type="file">`:

```javascript
const uploadArea = document.getElementById('uploadArea');
const fileInput  = document.getElementById('excel_file');

// Click anywhere on the styled area to trigger file picker
uploadArea.addEventListener('click', () => fileInput.click());

// Drag-over visual feedback
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('bg-light');
});

// Handle dropped file
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    fileInput.files = e.dataTransfer.files;  // Assign to input
    showFileName(e.dataTransfer.files[0].name);
});
```

Key points:
- The actual `<input type="file">` is hidden (`d-none`) — the visible area is a styled `<div>`.
- `e.preventDefault()` on `dragover` is **required** for `drop` to fire.
- `fileInput.files = e.dataTransfer.files` assigns the dropped file to the form input so the standard `<form>` submission works.
- The file name is displayed in a confirmation area after selection.
- **Server-side validation** via Flask-WTF `FileAllowed(['xlsx', 'xls'])` ensures only Excel files are accepted.

---

### Q53: How does the Resource export to Excel work? How does it differ from the import?

**Answer:**  
**Export** (read from DB → write to Excel):
```python
wb = openpyxl.Workbook()
ws = wb.active
ws.title = f'Resources - {demand.rrd}'

# Headers with purple styling
headers = ['Personnel No', 'Name', 'Primary Skill', ...]
ws.append(headers)
for cell in ws[1]:
    cell.font = Font(bold=True, color='FFFFFF')
    cell.fill = PatternFill(start_color='A100FF', fill_type='solid')

# Data rows
for r in resources:
    ws.append([r.personnel_no, r.name, r.primary_skill, ...
               r.status_display, r.evaluation_remarks,
               r.evaluator.display_name if r.evaluator else ''])

# Auto-width columns
for col in ws.columns:
    max_len = max(len(str(cell.value or '')) for cell in col) + 2
    ws.column_dimensions[col[0].column_letter].width = min(max_len, 40)

output = BytesIO()
wb.save(output)
output.seek(0)
return send_file(output, as_attachment=True, download_name=filename)
```

**Import** (read from Excel → write to DB):
```python
wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
ws = wb.active
# Map headers, iterate rows, create Resource objects
```

Key differences:

| Aspect         | Import (Upload)                  | Export (Download)                |
|----------------|----------------------------------|----------------------------------|
| **openpyxl mode** | `read_only=True, data_only=True` | Standard write mode             |
| **Memory**     | Streaming read (low memory)      | Full workbook in memory          |
| **Direction**  | File → Database                  | Database → File                  |
| **Headers**    | Flexible matching (HEADER_MAP)   | Fixed, styled headers            |
| **Extra data** | N/A                              | Adds evaluation status & remarks |
| **Error handling** | Per-row try/catch, skip bad rows | Simple iteration                |

---

### Q54: How does cascade delete work for resources when a demand is deleted?

**Answer:**  
When a demand is deleted, all associated resources are automatically removed via **cascade delete** at two levels:

**1. SQLAlchemy ORM level:**
```python
# On the Demand model's backref
demand = db.relationship('Demand', backref=db.backref(
    'resources', lazy='dynamic', cascade='all, delete-orphan'))
```
`cascade='all, delete-orphan'` means:
- `all` — propagate save, merge, refresh, expunge, delete to children.
- `delete-orphan` — delete resource if it's removed from `demand.resources`.

**2. Database level (DDL):**
```python
demand_id = db.Column(db.Integer,
    db.ForeignKey('demands.id', ondelete='CASCADE'))
```
```sql
-- In migration
demand_id INTEGER NOT NULL REFERENCES demands(id) ON DELETE CASCADE
```

This **defense-in-depth** approach ensures no orphaned resource records remain even if the ORM is bypassed (e.g., raw SQL cleanup). The test suite validates this:
```python
def test_resource_cascade_delete(self, app):
    # Create demand with 3 resources
    db.session.delete(demand)
    db.session.commit()
    assert Resource.query.count() == 0  # All gone
```

---

### Q55: How would you handle very large Excel files (10,000+ rows) in the upload?

**Answer:**  
The current implementation works well for typical PMO uploads (tens to hundreds of rows). For 10K+ rows, potential issues and solutions:

**1. Memory — openpyxl `read_only=True`:**  
Already implemented. This mode uses **streaming/iterating** instead of loading the entire workbook into memory. Memory usage is proportional to one row, not the whole file.

**2. Request Timeout:**
- Gunicorn timeout is `600s` (10 minutes) — sufficient for most uploads.
- For very large files, switch to **background processing**:
  ```python
  # Option A: Celery + Redis task queue
  @celery.task
  def process_upload(file_path, demand_id, user_id):
      # Parse and insert in batches
      ...
  
  # Option B: Azure Function triggered by Blob upload
  # 1. Save file to Blob Storage
  # 2. Azure Function triggers on new blob
  # 3. Function parses and inserts to DB
  ```

**3. Database Performance — Batch Inserts:**
```python
BATCH_SIZE = 500
batch = []
for row in ws.iter_rows(min_row=2):
    resource = Resource(...)
    batch.append(resource)
    if len(batch) >= BATCH_SIZE:
        db.session.bulk_save_objects(batch)
        db.session.flush()
        batch = []
if batch:
    db.session.bulk_save_objects(batch)
db.session.commit()
```

**4. Client-side Progress:**
- Use JavaScript `fetch` with `ReadableStream` or WebSocket for upload progress.
- Show a progress bar during the upload.

**5. Azure App Service Upload Limit:**
- Default max request body is **30 MB** (configurable via `maxRequestBodySize`).
- A 10K-row Excel file is typically 1–5 MB, well within limits.

---

### Q56: Compare the new Resource-based evaluation flow to the original Application self-service flow.

**Answer:**  

| Aspect              | Application Flow (Original, Removed) | Resource Flow (New)                   |
|---------------------|---------------------------------------|---------------------------------------|
| **Who initiates**   | Resource self-applies                 | PMO uploads resource list             |
| **Data entry**      | Resource fills web form               | PMO provides Excel from HR/bench data |
| **Resume**          | Uploaded by resource (.docx/.pptx)    | Not applicable (contact info only)    |
| **Contact method**  | Evaluator reviews resume              | Email (mailto:) / Phone (tel:) links  |
| **Scale**           | One-at-a-time                         | Bulk upload (hundreds at once)        |
| **User burden**     | Each resource must log in & apply     | PMO handles everything centrally      |
| **Evaluation**      | Status form per application           | Modal per resource (same workflow)    |
| **JD distribution** | Resource reads demand page            | Evaluator emails JD directly to resource |
| **Audit trail**     | ApplicationHistory model              | evaluated_by + evaluated_at fields    |

The resource flow is more practical for enterprise staffing where PMOs have bench/joiner lists in Excel and need evaluators to screen candidates before project allocation.

---

*End of Section 12 (v1.1 — Q46–Q56)*

---

## 13. RRD Refactoring & Expanded Evaluation Workflow (v1.2)

This section covers the v1.2 changes: renaming "Demands" to "RRDs" across the UI, removing the "Raise a Demand" feature, expanding evaluation statuses from 4 to 7, and fixing a production 500 error caused by a missing model import.

---

### Q57: What is an "RRD" in SkillHive, and why was the UI label changed from "Demands" to "RRDs"?

**Answer:**  

RRD stands for **Resource Request Detail** — the standard term used in enterprise staffing to describe an open requirement with a specific role, skill set, experience band, and project assignment.

The original codebase used the term "Demand" everywhere (navbar, dashboard stats, page titles, breadcrumbs, etc.), but business stakeholders referred to these records as RRDs in day-to-day communication. Renaming the UI to "RRDs" aligns the product with the language users already speak, reducing confusion.

**Key implementation details:**
- The **database model** is still named `Demand` (no schema migration needed — only UI labels changed).
- The **route blueprint** is still `demands` — URLs like `/demands/` and `/demands/<id>` remain unchanged.
- All **template labels** were updated: navbar, dashboard stat cards, breadcrumbs, page titles, hero section, empty-state messages, and "How It Works" steps on the landing page.
- This demonstrates a common pattern: **decoupling the domain model name from the user-facing label** to reduce refactoring risk while still improving UX.

---

### Q58: The "Raise a Demand" feature was removed from the UI. How was this done, and why keep the backend route?

**Answer:**  

**What was removed:**
- "Raise Demand" button from the **navbar** (was visible to PMO/Admin users)
- "Raise New Demand" button from the **dashboard header**
- "Raise Demand" button from the **demands list page**
- "Create your first Demand" empty-state link from the **dashboard** and **list page**

**What was kept:**
- The `demands.create` **Flask route** and the `CreateDemandForm` still exist in the codebase.
- The `demands/create.html` template is still present.

**Why keep the backend?**
1. **Admin backdoor**: An admin can still navigate directly to `/demands/new` if manual RRD creation is needed.
2. **API compatibility**: If a future API or bulk-import script calls the create endpoint, it will work.
3. **Minimal risk**: Removing UI entry points is sufficient to prevent accidental use. Deleting routes introduces merge conflicts and reduces flexibility.
4. **Reversibility**: If the business later wants to re-enable self-service RRD creation, it's a one-line template change.

This pattern is called **soft removal** — hide from the UI, keep in the backend, document the decision.

---

### Q59: Describe the expanded evaluation statuses in v1.2. What are they and why were 3 new ones added?

**Answer:**  

**v1.1 statuses (4):** `pending`, `under_evaluation`, `selected`, `rejected`

**v1.2 statuses (7):**

| Status             | Display Label                         | Badge Color | Use Case |
|--------------------|---------------------------------------|-------------|----------|
| `pending`          | Pending                               | Secondary   | Resource uploaded, not yet reviewed |
| `under_evaluation` | Under Evaluation                      | Primary     | Evaluator is actively reviewing |
| `accepted`         | Accepted                              | Success     | Resource is a good fit (replaced `selected`) |
| `rejected`         | Rejected                              | Danger      | Resource does not meet requirements |
| `skill_mismatch`   | Skill Mismatch                        | Info        | Skills don't align with RRD requirements |
| `unavailable`      | Unavailable                           | Dark        | Resource is not available (on leave, resigned, etc.) |
| `already_locked`   | Already Locked to Another DU/Project  | Warning     | Resource is committed to another engagement |

**Why the expansion?**
- `rejected` was a catch-all — evaluators couldn't distinguish *why* someone was rejected.
- `skill_mismatch` vs `unavailable` vs `already_locked` give clear, actionable reasons that help PMOs take different actions (e.g., reskill, defer, or look for alternatives).
- `selected` was renamed to `accepted` for clearer semantics — "selected" implies final placement, while "accepted" means the evaluator approves the candidate for the next step.

**Backward compatibility:** The `Resource` model's `status_display`, `status_color`, and `status_icon` properties include a **legacy fallback** for `selected` → maps to "Accepted" / green / check-circle, so any existing database records with `selected` render correctly without a data migration.

---

### Q60: The evaluation_status column is VARCHAR(20). Do the new status values fit? How would you handle it if they didn't?

**Answer:**  

**Current VARCHAR(20) analysis:**
| Value              | Length |
|--------------------|--------|
| `pending`          | 7      |
| `under_evaluation` | 16     |
| `accepted`         | 8      |
| `rejected`         | 8      |
| `skill_mismatch`   | 14     |
| `unavailable`      | 11     |
| `already_locked`   | 14     |

All values fit within VARCHAR(20). No database migration was needed.

**If they didn't fit**, the approach would be:
1. Create a new migration file (e.g., `004_widen_evaluation_status.sql`).
2. Use `ALTER TABLE resources ALTER COLUMN evaluation_status TYPE VARCHAR(50);` — PostgreSQL allows widening VARCHAR without rewriting the table.
3. Run the migration via `scripts/run_migrations.py` with a temporary firewall rule for the Azure PostgreSQL server.
4. Verify with `SELECT MAX(LENGTH(evaluation_status)) FROM resources;`.

---

### Q61: A 500 error occurred on the demand detail page (/demands/<id>). What was the root cause and how was it fixed?

**Answer:**  

**Symptom:** Visiting any demand detail page returned HTTP 500 (Internal Server Error).

**Root cause:** The `detail()` route in `app/routes/demands.py` used `Application.applied_at.desc()` to sort applications:

```python
applications = demand.applications.order_by(
    Application.applied_at.desc()
).all()
```

But the `Application` model was **not imported** in the file. The import line was:
```python
from app.models import Demand, Skill
```

This caused a `NameError: name 'Application' is not defined` at runtime.

**Fix:** Added `Application` to the import:
```python
from app.models import Demand, Skill, Application
```

**Why it wasn't caught earlier:**
- The route was added during the Application workflow phase but the import was missed.
- Python doesn't validate references at import time — the error only surfaces when the route is actually hit.
- The test suite tested demand listing (`/demands/`) but not the detail page (`/demands/<id>`).

**Lesson:** Always verify that every model/class referenced in a route is imported. A good practice is to run a linter like `flake8` with the `F821` (undefined name) check enabled.

---

### Q62: How were the filter cards on the resource list page updated for the new statuses?

**Answer:**  

**v1.1 (5 cards):** Total, Pending, In Review, Selected, Rejected

**v1.2 (8 cards):** Total, Pending, In Review, Accepted, Rejected, Skill Mismatch, Unavailable, Locked

Each card shows:
- A **count** from the stats dictionary (computed in the `list_resources()` route)
- A **Bootstrap badge color** matching the status
- An **icon** (Font Awesome) for visual distinction
- A **clickable filter** that highlights the card and filters the table

The stats dictionary in `resources.py` was expanded:
```python
stats = {
    'total': resources.count(),
    'pending': resources.filter_by(evaluation_status='pending').count(),
    'under_evaluation': resources.filter_by(evaluation_status='under_evaluation').count(),
    'accepted': resources.filter_by(evaluation_status='accepted').count(),
    'rejected': resources.filter_by(evaluation_status='rejected').count(),
    'skill_mismatch': resources.filter_by(evaluation_status='skill_mismatch').count(),
    'unavailable': resources.filter_by(evaluation_status='unavailable').count(),
    'already_locked': resources.filter_by(evaluation_status='already_locked').count(),
}
```

**Performance consideration:** Each `.count()` is a separate SQL query. For large datasets, this could be optimized with a single `GROUP BY evaluation_status` query using `db.session.query(Resource.evaluation_status, func.count()).group_by(Resource.evaluation_status).all()`.

---

### Q63: The evaluation modal in the resource list page now shows 7 status options with emoji indicators. How does this improve UX?

**Answer:**  

The evaluation modal `<select>` was updated from:
```html
<option value="selected">✅ Selected</option>
<option value="rejected">❌ Rejected</option>
```

To include all 7 statuses with visual emoji indicators:
```html
<option value="pending">⏳ Pending</option>
<option value="under_evaluation">🔍 Under Evaluation</option>
<option value="accepted">✅ Accepted</option>
<option value="rejected">❌ Rejected</option>
<option value="skill_mismatch">🔀 Skill Mismatch</option>
<option value="unavailable">🚫 Unavailable</option>
<option value="already_locked">🔒 Already Locked to Another DU/Project</option>
```

**UX improvements:**
1. **Emoji prefix** provides instant visual recognition — evaluators can scan options faster.
2. **Descriptive labels** reduce ambiguity — "Already Locked to Another DU/Project" is self-explanatory.
3. **All 7 options in one modal** eliminates the need for multiple evaluation steps.
4. **The evaluator sees the current status pre-selected** when opening the modal, so they know what's already assigned.

---

### Q64: How does legacy data with `selected` status render correctly after the rename to `accepted`?

**Answer:**  

The `Resource` model has three computed properties (`status_display`, `status_color`, `status_icon`) that use dictionary lookups with a **fallback chain**:

```python
@property
def status_display(self):
    status_map = {
        'pending': 'Pending',
        'under_evaluation': 'Under Evaluation',
        'accepted': 'Accepted',
        'rejected': 'Rejected',
        'skill_mismatch': 'Skill Mismatch',
        'unavailable': 'Unavailable',
        'already_locked': 'Already Locked',
        'selected': 'Accepted',      # Legacy support
    }
    return status_map.get(self.evaluation_status, self.evaluation_status.replace('_', ' ').title())
```

If `self.evaluation_status == 'selected'`, it returns `'Accepted'` as the display label, `'success'` as the badge color, and `'check-circle'` as the icon — identical to the new `accepted` status.

**This means:**
- No data migration needed for existing records.
- A future cleanup migration (`UPDATE resources SET evaluation_status = 'accepted' WHERE evaluation_status = 'selected'`) can be run at any convenient time.
- The final `.get()` fallback handles any unknown status by formatting the raw string (e.g., `some_future_status` → `Some Future Status`).

---

### Q65: What testing was done to validate the v1.2 changes? What would you add?

**Answer:**  

**Tests executed:**
- All **17 existing tests** passed after the changes (run via `pytest tests/ -v`).
- The `test_resource_evaluation` test was updated to use `accepted` instead of `selected`, verifying that `status_display` returns `'Accepted'`.
- Template rendering was validated visually on the deployed Azure App Service.

**What should be added:**
1. **Demand detail page test**: A test that hits `/demands/<id>` to prevent the `Application` import regression from recurring.
2. **All 7 evaluation status tests**: Parameterized test that evaluates a resource with each of the 7 statuses and verifies `status_display`, `status_color`, and `status_icon`.
3. **Legacy status test**: Test that a resource with `evaluation_status='selected'` still renders as `'Accepted'` with `'success'` color.
4. **Filter card count test**: API/view test that uploads resources with different statuses and verifies the stats dictionary counts.
5. **UI regression test** (Selenium/Playwright): Verify that no "Raise Demand" button appears on the dashboard, navbar, or list page.

---

### Q66: Describe the database migration strategy used throughout SkillHive's evolution (v1.0 → v1.1 → v1.2).

**Answer:**  

SkillHive uses a **numbered SQL migration** approach:

| Migration | Version | Description |
|-----------|---------|-------------|
| `001_initial.sql` | v1.0 | Initial schema: users, skills, demands, applications, application_history |
| `002_du_client_to_rrd.sql` | v1.0.1 | Replaced `du_name` + `client_name` columns with single `rrd` field on demands table |
| `003_create_resources.sql` | v1.1 | Created `resources` table for bulk Excel upload + evaluation workflow |
| *(none needed)* | v1.2 | No schema changes — all v1.2 changes are UI/code only |

**Migration execution:** Migrations are run via `scripts/run_migrations.py`, which:
1. Opens a direct `psycopg2` connection to Azure PostgreSQL (since `psql` is not installed locally).
2. Reads SQL files from `database/migrations/` in order.
3. Executes each migration idempotently (uses `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`).
4. Requires a temporary Azure firewall rule (`AllowLocalMigration`) that is removed after execution.

**Why no migration for v1.2?** The new evaluation status values (`skill_mismatch`, `unavailable`, `already_locked`) all fit within the existing `VARCHAR(20)` column, and the `selected` → `accepted` rename is handled at the application layer (legacy fallback in model properties), so no data migration is required.

---

*End of Interviewer Guide (v1.2 — Q1–Q66)*
---

## Section 10: Change Request — v1.3 (OTP Authentication, Super Admin & User Approval)

> **Scenario Context:** The client has raised a Change Request (CR) for SkillHive v1.3 with the following requirements:
> 1. Remove the "Manage Applications" tab — resources will no longer self-apply for open RRDs.
> 2. Replace password-based login with OTP-based authentication, restricted to `@accenture.com` emails only.
> 3. Only admin-approved users can log in. A designated Super Admin (`pratyush.vashistha@accenture.com`) controls all user roles, approvals, and deletions.
> 4. Add session security hardening (timeouts, cookie flags).
> 5. Update the test suite to cover the new authentication flow.

---

### Q67: As a developer, how would you approach removing the "Manage Applications" feature from a Flask portal without breaking existing data or routes?

**Answer:**  

The approach used in SkillHive v1.3 is a **soft removal** — the UI entry points are removed but the backend routes and database tables are preserved:

1. **Remove navigation items** from `base.html` (navbar link) and `dashboard.html` (quick action button).
2. **Remove export link** from the admin dropdown menu.
3. **Keep the routes in `app/routes/applications.py`** — they become inaccessible through the UI but are still functional if accessed directly. This is intentional:
   - Preserves historical application data in the database.
   - Avoids cascading code changes (forms, models, migrations).
   - Allows the feature to be re-enabled quickly if requirements change.

A more aggressive approach would be to remove the blueprint registration in `__init__.py` (returning 404 for all `/applications/*` routes), but this risks breaking any saved bookmarks or external integrations without providing a helpful error message.

---

### Q68: Explain the OTP authentication flow implemented in SkillHive v1.3. What are the key components?

**Answer:**  

The OTP flow is a two-step passwordless authentication:

**Step 1 — Email Submission (`/auth/login` POST):**
```
User enters email → Validate @accenture.com domain → Check user exists →
Check is_active → Check is_approved → Generate 6-digit OTP → Store in DB →
Send via Flask-Mail → Store email in session → Redirect to /auth/verify-otp
```

**Step 2 — OTP Verification (`/auth/verify-otp` POST):**
```
User enters 6-digit code → Retrieve email from session → Find user →
Call user.verify_otp(code) → If valid: clear OTP, set last_login_at,
login_user() → Redirect to dashboard
```

**Key components:**
| Component | Purpose |
|-----------|---------|
| `User.generate_otp()` | Generates random 6-digit code, sets 10-minute expiry via `datetime.utcnow() + timedelta(minutes=10)` |
| `User.verify_otp(code)` | Validates code + checks expiry + clears OTP after use (one-time) |
| `_send_otp_email()` | Uses Flask-Mail with HTML template; falls back to console logging in dev mode |
| `session['otp_email']` | Passes the email between login and verify steps across HTTP requests |
| `otp_email.html` | Branded HTML email template with large OTP display |

**Security features:**
- OTP is single-use (cleared after verification).
- 10-minute expiry prevents replay attacks.
- Domain restriction (`@accenture.com`) at the route level.
- Admin approval gate (`is_approved` flag) before OTP is even generated.

---

### Q69: Why was `datetime.utcnow()` used instead of `datetime.now(timezone.utc)` for OTP expiry in the model? What problem does this solve?

**Answer:**  

This is a practical decision driven by **database compatibility**:

- **SQLite** (used for testing and local development) stores datetimes as **naive** (no timezone info). When you read them back, they come back as naive `datetime` objects.
- **`datetime.now(timezone.utc)`** returns a **timezone-aware** datetime.
- Comparing aware vs. naive datetimes raises `TypeError: can't compare offset-naive and offset-aware datetimes`.

Using `datetime.utcnow()` (which returns a naive datetime in UTC) ensures consistent comparison across both SQLite (testing) and PostgreSQL (production). PostgreSQL's `TIMESTAMP` column also stores naive datetimes by default (as opposed to `TIMESTAMPTZ`).

**Trade-off:** `datetime.utcnow()` is deprecated in Python 3.12+. A more future-proof approach would be to use `TIMESTAMPTZ` in PostgreSQL and `datetime.now(timezone.utc)` everywhere, with a custom SQLAlchemy type decorator to ensure SQLite compatibility.

---

### Q70: How does the Super Admin pattern work in SkillHive? How is it protected from accidental changes?

**Answer:**  

The Super Admin (`pratyush.vashistha@accenture.com`) is protected at **four levels**:

1. **Model Level:** `User.SUPER_ADMIN_EMAIL` constant + `is_super_admin` property:
   ```python
   @property
   def is_super_admin(self):
       return self.email.lower() == self.SUPER_ADMIN_EMAIL.lower()
   ```

2. **App Startup (`__init__.py`):** `_ensure_super_admin()` runs on every application start:
   - Creates the super admin if not in DB (role=admin, is_active=True, is_approved=True).
   - If already exists, ensures role/active/approved flags are correct. This prevents the super admin from being locked out even if the database is manually modified.

3. **Route Level (`admin.py`):**
   - `delete_user`: Cannot delete the super admin.
   - `revoke_user`: Cannot deactivate the super admin.
   - `update_user_role`: Cannot change the super admin's role.
   - Only the super admin can assign the "admin" role or delete users.

4. **Template Level (`users.html`):**
   - Super admin gets an "SA" badge — no action buttons are rendered for that row.
   - "Admin" role option in Add User modal only visible to super admin.

---

### Q71: What database migration strategy was used for the OTP auth changes? How does it handle existing users?

**Answer:**  

**Migration 004 (`004_otp_auth_columns.sql`)** adds four columns:
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_code VARCHAR(6);
ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;
```

**Critical data migration for existing users:**
```sql
UPDATE users SET is_approved = TRUE WHERE is_active = TRUE;
```
This ensures all currently active users are not locked out when the approval gate is deployed. New users created after the migration will have `is_approved = FALSE` by default and must be approved by the admin.

**Super admin seeding via UPSERT:**
```sql
INSERT INTO users (...) VALUES ('pratyush.vashistha@accenture.com', ...)
ON CONFLICT (email) DO UPDATE SET role = 'admin', is_active = TRUE, is_approved = TRUE;
```

The migration script (`run_migrations.py`) checks `is_approved` column existence before running, making it idempotent.

---

### Q72: What session security hardening was applied in v1.3? Explain each setting.

**Answer:**  

Four settings were added to `config.py`:

| Setting | Value | Purpose |
|---------|-------|---------|
| `PERMANENT_SESSION_LIFETIME` | 3600 (1 hour) | Session expires after 1 hour of inactivity — forces re-authentication |
| `REMEMBER_COOKIE_DURATION` | 86400 (1 day) | "Remember me" cookie lasts 24 hours max |
| `SESSION_COOKIE_HTTPONLY` | `True` | Prevents JavaScript from accessing the session cookie (mitigates XSS) |
| `SESSION_COOKIE_SAMESITE` | `'Lax'` | Prevents CSRF by not sending the cookie on cross-origin POST requests |

**Combined with OTP auth**, this creates a defense-in-depth approach:
- Even if someone steals a session cookie (XSS), it expires in 1 hour.
- The `HttpOnly` flag makes it harder to steal via JavaScript injection.
- `SameSite=Lax` blocks cross-site form submissions from triggering authenticated actions.

---

### Q73: How does the user approval workflow interact with OTP authentication? Walk through a new user's journey.

**Answer:**  

**New User Journey:**

1. **User visits `/auth/login`** — enters their `@accenture.com` email.
2. **Not registered:** Flash message — "Your account is not registered. Please contact the administrator."
3. **Admin creates user:** Via `/admin/users` → "Add User" modal (enters display name, email, role). User is created with `is_approved = True` (admin-added users are pre-approved).
4. **User retries login:** Email found, `is_active = True`, `is_approved = True` → OTP generated and sent.
5. **User enters OTP** → Logged in, redirected to dashboard.

**Alternative flow (self-registration not implemented):** If self-registration were added later, a new user would:
1. Register → `is_approved = False` by default.
2. See "Your account is pending admin approval" message on login attempt.
3. Admin sees user in "Pending Approval" section of admin dashboard.
4. Admin clicks "Approve" → `is_approved = True`.
5. User can now log in via OTP.

---

### Q74: How were the existing test cases affected by the authentication rewrite? What new tests were added?

**Answer:**  

**Modified tests:**
- `test_login_page` — Updated assertion to check for `'accenture.com'` instead of password-related content.
- `test_login_invalid_creds` — Removed (password no longer used). Replaced with:
  - `test_login_non_accenture_email` — Verifies domain restriction.
  - `test_login_unregistered_accenture_email` — Verifies unknown user handling.
  - `test_login_unapproved_user` — Verifies approval gate.
  - `test_login_otp_flow` — Full end-to-end: create approved user → POST login → extract OTP from DB → POST verify-otp → assert logged in.

**New test classes:**
- **`TestOTPAuth`** (5 tests): `generate_otp`, `verify_otp_valid`, `verify_otp_invalid`, `verify_otp_expired`, `is_super_admin`.
- **`TestUserApproval`** (2 tests): `new_user_not_approved`, `approve_user`.

**Testing challenge:** The OTP flow test must extract the OTP from the database after the login POST (since it's randomly generated). In production, the OTP would arrive via email — but in testing, we bypass email and read directly from `User.otp_code`.

---

### Q75: If a team member asked you to add Multi-Factor Authentication (MFA) on top of OTP in SkillHive, how would you design it?

**Answer:**  

OTP is already single-factor (something you have — email access). True MFA would add a second factor:

**Option 1 — TOTP (Time-based OTP) via authenticator app:**
- Add `totp_secret` column to `User` model (encrypted).
- After email OTP verification, prompt for TOTP from Google Authenticator / Microsoft Authenticator.
- Use `pyotp` library for TOTP generation and verification.
- Enrollment: Admin enables MFA → user scans QR code → enters confirmation code.

**Option 2 — Passkey / WebAuthn (passwordless hardware key):**
- Use `py_webauthn` library.
- Register the user's security key or biometric (Windows Hello, Touch ID).
- After email OTP, prompt for passkey tap.

**Recommended for SkillHive:** TOTP via authenticator app — it's lightweight, doesn't require hardware, and integrates well with the existing flow. The email OTP becomes "first factor" and TOTP becomes "second factor."

---

### Q76: What are the risks of hardcoding the Super Admin email? How would you make it configurable?

**Answer:**  

**Current risks:**
- Changing the super admin requires a code deployment (not runtime configurable).
- If the email address changes (e.g., employee leaves), no one has super admin access until code is updated and redeployed.
- The email appears in multiple files (`models.py`, `auth.py`, `admin.py`, `__init__.py`).

**Better approaches (increasingly robust):**
1. **Environment variable:** `SUPER_ADMIN_EMAIL = os.environ.get('SUPER_ADMIN_EMAIL', 'pratyush.vashistha@accenture.com')` — configurable per deployment via Azure App Settings.
2. **Database flag:** Add `is_super_admin` boolean column instead of email comparison. Multiple super admins become possible.
3. **Role hierarchy:** Introduce `superadmin` as a distinct role above `admin`, managed via DB rather than code. The `_ensure_super_admin()` startup function could read from env var.

**Why hardcoding was chosen for v1.3:** Simplicity. The portal is small (< 50 users), has a single known admin, and the priority was rapid delivery. The env-var approach would be the first refactoring step.

---

*End of Interviewer Guide (v1.3 — Q1–Q76)*

---

## Section 11: Cost Optimization — Business Hours Access Control (v1.3.1)

> **Scenario Context:** The client wants to reduce Azure hosting costs by making the SkillHive portal unavailable during non-business hours (midnight to 8 AM IST). When users try to access the app during these hours, they should see a friendly maintenance message instead of the actual application.

---

### Q77: How would you implement time-based access control in a Flask application to block requests outside business hours?

**Answer:**  

The implementation uses Flask's `before_request` hook, which runs before every request:

```python
def _register_business_hours_check(app):
    from datetime import datetime, timedelta, timezone
    from flask import render_template, request

    # IST is UTC+5:30
    IST = timezone(timedelta(hours=5, minutes=30))
    BUSINESS_START_HOUR = 8   # 8:00 AM
    BUSINESS_END_HOUR = 24    # Midnight

    @app.before_request
    def check_business_hours():
        # Skip in dev/testing mode
        if app.config.get('DEV_MODE') or app.config.get('TESTING'):
            return None

        # Allow static files
        if request.path.startswith('/static/'):
            return None

        now_ist = datetime.now(IST)
        if now_ist.hour < BUSINESS_START_HOUR:
            return render_template('errors/maintenance.html'), 503

        return None  # Allow request to continue
```

**Key design decisions:**
- **`before_request` hook:** Runs before route handlers, allowing early interception.
- **Return `None` to allow:** Flask treats `None` as "continue to route handler."
- **Return response to block:** Returning a tuple `(html, status_code)` short-circuits the request.
- **503 status code:** "Service Unavailable" is semantically correct for temporary maintenance.
- **Skip static files:** CSS/JS/images on the maintenance page must still load.

---

### Q78: Why use `datetime.now(IST)` with an explicit timezone instead of `datetime.now()`? What timezone pitfalls should you watch out for?

**Answer:**  

**Why explicit timezone:**
- `datetime.now()` returns a **naive** datetime (no timezone info) in the server's local timezone.
- Azure App Service runs on UTC by default, so `datetime.now()` returns UTC time, not IST.
- Using `datetime.now(IST)` creates a **timezone-aware** datetime in IST regardless of server location.

**Implementation:**
```python
from datetime import datetime, timedelta, timezone

# Define IST as UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

# This is always in IST, regardless of server timezone
now_ist = datetime.now(IST)
```

**Pitfalls to avoid:**
1. **Relying on server timezone:** Azure App Service defaults to UTC; don't assume IST.
2. **Naive vs. aware comparison:** Mixing naive and aware datetimes raises `TypeError`.
3. **DST confusion:** IST doesn't observe DST, but other timezones do — always use `timezone` objects, not magic strings.
4. **`pytz` vs. `zoneinfo`:** Python 3.9+ has `zoneinfo` for named timezones, but for simple fixed offsets, `timezone(timedelta(...))` is sufficient.

---

### Q79: What HTTP status code should the maintenance page return, and why does it matter for SEO and monitoring?

**Answer:**  

**Recommended: 503 Service Unavailable**

| Status Code | Meaning                               | Impact                                      |
|-------------|---------------------------------------|---------------------------------------------|
| **200 OK**  | Success                               | Search engines index maintenance page as content — BAD |
| **503**     | Service Unavailable (temporary)       | Search engines know to retry later — GOOD    |
| **500**     | Internal Server Error                 | Indicates a bug — alerts fire — BAD          |
| **403**     | Forbidden                             | Implies auth failure — wrong semantics       |

**Why 503 matters:**
- **Search engines:** Google respects 503 and will retry the original URL later. Returning 200 would make Google think the maintenance page *is* your content.
- **Monitoring:** Application Insights / Log Analytics can alert on 5xx spikes. 503 during known maintenance windows can be excluded from alerts via KQL filtering.
- **Retry-After header (optional):** You can include `Retry-After: 28800` (8 hours in seconds) to tell clients when to retry.

---

### Q80: How does skipping `DEV_MODE` and `TESTING` in the business hours check help development and testing workflows?

**Answer:**  

```python
if app.config.get('DEV_MODE') or app.config.get('TESTING'):
    return None  # Skip business hours check
```

**Development benefits:**
- Developers can access the app at any time during local development.
- `DEV_MODE=true` is set in development config, so `flask run` at 2 AM still works.
- No need to mock the system clock or modify code for off-hours work.

**Testing benefits:**
- `TESTING=True` is set by the pytest fixture.
- All 27 tests pass regardless of what time the CI/CD pipeline runs.
- Tests don't need to stub `datetime.now()` — the check is simply bypassed.

**Production safety:**
- In production, `DEV_MODE` is false (not set in Azure App Settings).
- The check runs only in production, where cost savings matter.

---

### Q81: What are the trade-offs of implementing business hours at the application layer vs. using Azure's built-in auto-stop features?

**Answer:**  

| Approach                          | Pros                                        | Cons                                           |
|-----------------------------------|---------------------------------------------|------------------------------------------------|
| **App-layer `before_request`**    | Instant response, custom UX, no cold start  | App still running (still costs compute)        |
| **Azure App Service Stop/Start**  | Zero compute cost when stopped              | ~30-60s cold start when restarting             |
| **Azure Automation Runbooks**     | Scheduled stop/start, zero compute          | Complex setup, delayed restart                 |
| **Always On = Off + Traffic-based**| Auto-stop after idle, auto-restart on hit  | Cold starts, not truly "blocked"               |

**Why SkillHive uses app-layer:**
1. **User experience:** Users see a friendly page immediately, not a connection timeout.
2. **Zero cold start:** App stays "warm" — when 8 AM hits, requests are instant.
3. **Simpler implementation:** No Automation Accounts, Logic Apps, or scheduled tasks.
4. **Partial cost savings:** DB connections are idle during maintenance, reducing DTU usage.

**Hybrid approach (future enhancement):**
- Use app-layer check for UX during maintenance.
- Additionally, scale App Service Plan to B1 (1 instance) during off-hours via Automation.
- Scale back to S1 (auto-scale) during business hours.

---

### Q82: How would you allow admin users to bypass the business hours restriction for emergency access?

**Answer:**  

**Option 1 — Session-based bypass (simple):**
```python
@app.before_request
def check_business_hours():
    from flask_login import current_user

    # Allow authenticated admins through
    if current_user.is_authenticated and current_user.is_admin:
        return None

    # Regular business hours check follows...
```
**Problem:** Can't log in if blocked before login page!

**Option 2 — Query parameter with secret key:**
```python
BYPASS_KEY = os.environ.get('MAINTENANCE_BYPASS_KEY', 'secret123')

@app.before_request
def check_business_hours():
    # Allow bypass with secret key
    if request.args.get('bypass') == BYPASS_KEY:
        session['bypass_maintenance'] = True

    if session.get('bypass_maintenance'):
        return None

    # Regular check...
```
**Usage:** `https://skillhive.../auth/login?bypass=secret123`

**Option 3 — IP allowlist:**
```python
ALLOWED_IPS = ['10.0.0.1', '192.168.1.100']  # Admin VPN IPs

@app.before_request
def check_business_hours():
    if request.remote_addr in ALLOWED_IPS:
        return None
```

**Recommended for SkillHive:** Option 2 (query param) for simplicity + Option 1 for logged-in admins.

---

### Q83: What monitoring or alerting would you set up around the business hours feature?

**Answer:**  

**Metrics to track:**
1. **503 response count:** Should spike at midnight, drop to zero at 8 AM.
2. **Request count during maintenance:** Should be near-zero (only blocked requests).
3. **Time-of-day distribution:** Validate that no legitimate traffic is blocked.

**Azure Application Insights KQL query:**
```kusto
requests
| where resultCode == 503
| summarize count() by bin(timestamp, 1h)
| render timechart
```

**Alerts to configure:**
- **Unexpected 503 during business hours:** If 503s occur between 8 AM – midnight, something is wrong.
- **High 503 volume during maintenance:** If many users are being blocked, consider extending hours.

**Log entry in app:**
```python
app.logger.info(
    f"Access blocked outside business hours: "
    f"{now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST"
)
```
This creates a traceable audit trail in Application Insights for each blocked request.

---

### Q84: How would you make the business hours configurable without redeploying the application?

**Answer:**  

**Option 1 — Azure App Settings (recommended):**
```python
BUSINESS_START_HOUR = int(os.environ.get('BUSINESS_START_HOUR', 8))
BUSINESS_END_HOUR = int(os.environ.get('BUSINESS_END_HOUR', 24))
```

**Set in Azure Portal:**
- App Service → Configuration → Application Settings
- `BUSINESS_START_HOUR = 8`
- `BUSINESS_END_HOUR = 24`

**Option 2 — Database configuration table:**
```sql
CREATE TABLE app_config (
    key VARCHAR(100) PRIMARY KEY,
    value VARCHAR(255)
);
INSERT INTO app_config VALUES ('business_start_hour', '8');
INSERT INTO app_config VALUES ('business_end_hour', '24');
```

**Option 3 — Azure App Configuration service:**
- Managed key-value store with feature flags.
- Real-time updates without restart.
- Integrated with Python SDK (`azure-appconfiguration`).

**SkillHive's approach:** Currently hardcoded for simplicity. App Settings would be the first refactor for multi-client deployments.

---

### Q85: Explain the cost savings model for business hours access control. What components of Azure are affected?

**Answer:**  

**Cost components in SkillHive's architecture:**

| Component                    | During Business Hours       | During Maintenance         | Savings                      |
|------------------------------|-----------------------------|----------------------------|------------------------------|
| **App Service (B1)**         | Active, serving requests    | Active, but idle           | Minimal (still running)      |
| **PostgreSQL Flexible (B1ms)**| Active connections          | Idle connections           | ~10-20% DTU/vCore savings    |
| **Blob Storage**             | No difference               | No difference              | None (storage is static)     |
| **Application Insights**     | Logging requests            | Logging 503s (minimal)     | Minor reduction in log volume|
| **Outbound bandwidth**       | Full HTML pages             | Small maintenance page     | Minor savings                |

**Estimated monthly savings (B1 plan):**
- App Service B1: ~$13/month → No direct savings (still running)
- PostgreSQL B1ms: ~$15/month → ~$2-3/month savings (idle connections)
- **Total:** ~15-20% reduction in database costs

**To maximize savings (future):**
- Use Azure Automation to **stop** the App Service Plan during maintenance → **~33% savings on compute**.
- Use PostgreSQL serverless tier (when available) → **near-zero cost when idle**.

---

*End of Interviewer Guide (v1.3.1 — Q1–Q85)*