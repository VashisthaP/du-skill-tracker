# SkillHive – Functional & Technical Architecture Solution Document

**Document Version:** 1.0  
**Date:** February 12, 2026  
**Project:** SkillHive – DU Demand & Supply Tracker  
**Classification:** Internal  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Functional Architecture](#2-functional-architecture)
3. [Technical Architecture](#3-technical-architecture)
4. [Azure Integration Services](#4-azure-integration-services)
5. [Data Architecture](#5-data-architecture)
6. [Application Architecture](#6-application-architecture)
7. [Security Architecture](#7-security-architecture)
8. [Deployment Architecture](#8-deployment-architecture)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Technology Stack Summary](#10-technology-stack-summary)

---

## 1. Executive Summary

### 1.1 Purpose

SkillHive is an enterprise-grade web portal designed for Delivery Unit (DU) level **Demand & Supply tracking**. It bridges the gap between project demand (raised by PMO teams) and resource supply (employees with matching skills), streamlining the evaluation and allocation pipeline.

### 1.2 Business Problem

- PMO teams lack a centralized, self-service platform to raise project resource demands with specific skill requirements.
- Resources (employees) have no visibility into open demands matching their skill set.
- Evaluators/managers spend significant time coordinating demand-to-resource matching manually via emails and spreadsheets.
- No audit trail exists for application status transitions.

### 1.3 Solution Overview

SkillHive provides:
- A **Demand Management** module for PMO teams to publish resource requirements with skill tags.
- A **Self-Service Application** module for resources to apply for open demands.
- An **Evaluation Workflow** with status tracking (Applied → Under Evaluation → Selected/Rejected).
- A **Trending Skill Cloud** for real-time skill demand analytics.
- **Excel Export** capabilities for reporting.
- **Email Notifications** at every workflow stage.
- **Admin Panel** for user management and system-wide statistics.

---

## 2. Functional Architecture

### 2.1 Functional Modules

```
┌─────────────────────────────────────────────────────────────────┐
│                     SkillHive Portal                            │
├──────────┬──────────┬──────────┬──────────┬─────────────────────┤
│  Auth    │  Demand  │ Applica- │  Admin   │   Analytics &       │
│  Module  │  Mgmt    │  tions   │  Panel   │   Reporting         │
├──────────┼──────────┼──────────┼──────────┼─────────────────────┤
│• Login   │• Create  │• Apply   │• User    │• Skill Cloud        │
│• Logout  │• Edit    │• Track   │  Mgmt    │• Dashboard Stats    │
│• Session │• List    │• Review  │• Role    │• Excel Export       │
│  Mgmt    │• Filter  │• Status  │  Assign  │• Demand Trends      │
│• Role    │• Search  │  Update  │• System  │• Priority Analytics  │
│  Based   │• Export  │• Resume  │  Stats   │• Career Level Stats  │
│  Access  │• Status  │  Upload  │• Skill   │                     │
│          │  Mgmt    │• History │  Mgmt    │                     │
└──────────┴──────────┴──────────┴──────────┴─────────────────────┘
```

### 2.2 User Roles & Permissions

| Role         | Code         | Permissions                                                          |
|--------------|--------------|----------------------------------------------------------------------|
| Administrator| `admin`      | Full access: user management, demand CRUD, application review, system configuration |
| PMO Team     | `pmo`        | Create/edit/manage demands, review applications, export data, update statuses |
| Evaluator    | `evaluator`  | Review applications, update application status, download resumes      |
| Resource     | `resource`   | View open demands, apply for evaluation, track own applications       |

### 2.3 Core Workflows

#### 2.3.1 Demand Lifecycle

```
                    ┌─────────┐
                    │  PMO    │
                    │ Creates │
                    │ Demand  │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │  OPEN   │◄────────────────────┐
                    └────┬────┘                     │
                         │ Resource Applies         │ Reopen
                    ┌────▼────────┐                 │
                    │ IN_PROGRESS │─────────────────►┘
                    └────┬────────┘
                         │
              ┌──────────┼──────────┐
              │                     │
         ┌────▼───┐          ┌──────▼────┐
         │ FILLED │          │ CANCELLED │
         └────────┘          └───────────┘
```

#### 2.3.2 Application Workflow

```
   Resource            PMO/Evaluator
      │                      │
      │  Submit Application  │
      ├─────────────────────►│
      │                      │
      │    Status: APPLIED   │
      │◄─────────────────────┤
      │                      │
      │  UNDER EVALUATION    │
      │◄─────────────────────┤
      │                      │
      │   SELECTED           │
      │◄─────────────────────┤
      │       or             │
      │   REJECTED           │
      │◄─────────────────────┤
      │                      │
  [Email Notification at each status change]
```

### 2.4 Functional Features Detail

| # | Feature                    | Description                                                                                           |
|---|----------------------------|-------------------------------------------------------------------------------------------------------|
| 1 | Demand Creation            | PMO creates demands with project info, skills (tag input), career level, priority, evaluator details  |
| 2 | Skill Tag Input            | Interactive tag-based skill selection with autocomplete from skill taxonomy + custom skill entry       |
| 3 | Demand Filtering           | Filter by status, priority, career level, skill; Text search across project names                     |
| 4 | Demand Pagination          | 12 demands per page with paginated navigation                                                         |
| 5 | Application Submission     | Resources fill form (name, EID, experience, skills) + upload resume (.docx/.pptx)                     |
| 6 | Application Status Tracking| Full audit trail with ApplicationHistory model recording every status change                          |
| 7 | Resume Management          | Local storage (dev) / Azure Blob Storage (prod) with unique filename generation                       |
| 8 | Email Notifications        | SMTP-based notifications for demand creation, application received, status updates                    |
| 9 | Excel Export               | Formatted .xlsx export for demands and applications with branded styling                              |
| 10| Trending Skill Cloud       | Real-time skill demand cloud visualization using Chart.js                                             |
| 11| Dashboard                  | Role-based dashboard with KPIs, charts, latest demands, personal application tracker                  |
| 12| Admin Panel                | User management (CRUD, role assignment), system statistics, skill management                          |

---

## 3. Technical Architecture

### 3.1 High-Level Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ HTML/CSS    │  │ JavaScript   │  │ Chart.js     │                  │
│  │ Bootstrap 5 │  │ DOM/Events   │  │ DataViz      │                  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘                  │
└─────────┼────────────────┼─────────────────┼──────────────────────────┘
          │  HTTPS          │  HTTPS           │  REST API (JSON)
          ▼                 ▼                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    AZURE APP SERVICE (Linux B1)                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                    Gunicorn WSGI Server                         │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │                Flask Application (Python 3.11)           │  │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ │  │   │
│  │  │  │  Auth    │ │ Demands  │ │Applications│ │   Admin   │ │  │   │
│  │  │  │Blueprint │ │Blueprint │ │ Blueprint  │ │ Blueprint │ │  │   │
│  │  │  └──────────┘ └──────────┘ └───────────┘ └───────────┘ │  │   │
│  │  │  ┌──────────────────────────────────────────────────────┐│  │   │
│  │  │  │  Services: Email | Export | Blob Upload              ││  │   │
│  │  │  └──────────────────────────────────────────────────────┘│  │   │
│  │  │  ┌──────────────────────────────────────────────────────┐│  │   │
│  │  │  │  ORM Layer: SQLAlchemy + Flask-Migrate               ││  │   │
│  │  │  └──────────────────────────────────────────────────────┘│  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────┘   │
└──────┬──────────────────┬──────────────────┬──────────────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐  ┌───────────────┐  ┌──────────────────┐
│  PostgreSQL  │  │ Azure Blob    │  │ Application      │
│  Flexible    │  │ Storage       │  │ Insights +       │
│  Server v14  │  │ (Resumes)     │  │ Log Analytics    │
│  Standard    │  │ Standard LRS  │  │ Workspace        │
│  B1ms        │  │               │  │                  │
└──────────────┘  └───────────────┘  └──────────────────┘
       │
       ▼
┌──────────────┐
│  SMTP Server │
│  (Office 365)│
│  Port 587    │
│  TLS         │
└──────────────┘
```

### 3.2 Application Layer Architecture (Flask)

The application follows the **Application Factory** pattern with **Blueprint-based modular routing**.

```
app/
├── __init__.py              # App factory: create_app(), extension init
├── config.py                # Config classes: Dev/Prod/Test
├── models.py                # SQLAlchemy ORM models (5 models)
├── forms.py                 # WTForms form definitions
├── auth.py                  # Authentication blueprint (login/logout)
├── routes/
│   ├── main.py              # Landing page, dashboard, API endpoints
│   ├── demands.py           # Demand CRUD, filtering, export
│   ├── applications.py      # Application workflow, status mgmt
│   └── admin.py             # Admin panel, user management
├── services/
│   ├── email_service.py     # SMTP email notifications
│   └── export_service.py    # Excel file generation
├── utils/
│   └── decorators.py        # @pmo_required, @admin_required, @evaluator_required
├── templates/               # Jinja2 HTML templates
└── static/                  # CSS, JS, images
```

### 3.3 Design Patterns Used

| Pattern                  | Implementation                                                  |
|--------------------------|------------------------------------------------------------------|
| Application Factory      | `create_app(config_name)` in `__init__.py`                      |
| Blueprint Modular Routing | 5 blueprints: auth, main, demands, applications, admin          |
| Repository/ORM            | SQLAlchemy models with relationships and properties             |
| Service Layer             | Dedicated services for email, export, blob upload               |
| Decorator-based Auth      | `@login_required`, `@pmo_required`, `@admin_required`           |
| Observer (Email)          | Email notifications triggered on entity state changes           |
| Strategy (Storage)        | Resume upload: Azure Blob (prod) vs Local filesystem (dev)      |
| Audit Trail               | ApplicationHistory model tracks all status transitions          |

---

## 4. Azure Integration Services

### 4.1 Services Overview

| # | Azure Service                          | SKU / Tier         | Purpose                                         |
|---|----------------------------------------|--------------------|-------------------------------------------------|
| 1 | **Azure App Service**                  | Linux B1 (Basic)   | Host Flask web application with Gunicorn WSGI    |
| 2 | **Azure Database for PostgreSQL**      | Flexible, B1ms     | Relational database for all application data     |
| 3 | **Azure Blob Storage**                 | StorageV2, LRS     | Resume file storage (`.docx`, `.pptx`)           |
| 4 | **Azure Application Insights**         | Web component      | Application performance monitoring & diagnostics |
| 5 | **Azure Log Analytics Workspace**      | PerGB2018          | Centralized log aggregation & querying           |
| 6 | **Azure Resource Manager (ARM)**       | IaC Templates      | Infrastructure-as-Code deployment                |
| 7 | **Office 365 SMTP**                    | Port 587 / TLS     | Transactional email notifications                |

### 4.2 Azure App Service Configuration

| Setting                           | Value                                     |
|-----------------------------------|-------------------------------------------|
| Runtime                           | Python 3.11                               |
| Web Server                        | Gunicorn (2 workers, 600s timeout)        |
| App Service Plan                  | Linux B1 (1 core, 1.75 GB RAM)            |
| Always On                         | Enabled                                   |
| HTTPS Only                        | Enforced                                  |
| Build System                      | Oryx (SCM_DO_BUILD_DURING_DEPLOYMENT)     |
| Startup Command                   | `gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 wsgi:app` |

**Key App Settings:**

| Name                              | Description                               |
|-----------------------------------|-------------------------------------------|
| `SECRET_KEY`                      | Flask session encryption key              |
| `DATABASE_URL`                    | PostgreSQL connection string (SSL)        |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob Storage access credentials           |
| `AZURE_STORAGE_CONTAINER`         | Blob container name ("resumes")           |
| `APPINSIGHTS_INSTRUMENTATIONKEY`  | Application Insights telemetry key        |
| `MAIL_SERVER`                     | SMTP server hostname                      |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | SMTP authentication credentials           |
| `SCM_DO_BUILD_DURING_DEPLOYMENT`  | Enables Oryx build pipeline               |

### 4.3 Azure Database for PostgreSQL – Flexible Server

| Parameter          | Value                                          |
|--------------------|------------------------------------------------|
| Engine Version     | PostgreSQL 14                                  |
| SKU                | Standard_B1ms (Burstable, 1 vCore, 2 GB RAM)  |
| Storage            | 32 GB                                          |
| Backup Retention   | 7 days                                         |
| Geo-Redundancy     | Disabled                                       |
| SSL                | Required (`sslmode=require`)                   |
| Firewall           | Allow Azure Services (0.0.0.0)                 |
| Database Name      | `skillhive`                                    |
| Charset/Collation  | UTF8 / en_US.utf8                              |
| Driver             | psycopg2-binary 2.9.9                          |

### 4.4 Azure Blob Storage

| Parameter          | Value                                          |
|--------------------|------------------------------------------------|
| Kind               | StorageV2 (General Purpose v2)                 |
| Redundancy         | Standard LRS (Locally Redundant)               |
| Min TLS Version    | TLS 1.2                                        |
| HTTPS Only         | Enforced                                       |
| Container          | `resumes`                                      |
| SDK                | azure-storage-blob 12.19.0                     |

**Upload Flow:**
1. Resource submits `.docx`/`.pptx` resume via form
2. Application generates unique filename: `resume_{demand_id}_{user_id}_{uuid8}.{ext}`
3. **Production:** Uploads to Azure Blob Storage container using `BlobServiceClient`
4. **Development:** Falls back to local `uploads/` directory
5. Blob URL stored in `Application.resume_blob_url` for download

### 4.5 Azure Application Insights + Log Analytics

| Component              | Purpose                                        |
|------------------------|------------------------------------------------|
| Application Insights   | APM: request telemetry, exceptions, dependencies |
| Log Analytics Workspace| Centralized log storage with KQL query support   |
| Retention              | 30 days                                          |
| Integration            | Instrumentation key injected via App Settings    |

### 4.6 ARM Template (Infrastructure as Code)

The project includes a comprehensive ARM template (`infrastructure/azuredeploy.json`) that provisions all Azure resources in a single deployment:

**Resources Provisioned:**
1. Log Analytics Workspace
2. Application Insights (linked to Log Analytics)
3. App Service Plan (Linux B1)
4. App Service (with all app settings pre-configured)
5. PostgreSQL Flexible Server
6. PostgreSQL Database (`skillhive`)
7. PostgreSQL Firewall Rule (Allow Azure Services)
8. Storage Account (for resume uploads)

**Deployment Parameters:**
- `appName` – Unique application name (used across all resource names)
- `location` – Azure region (defaults to resource group location)
- `postgresAdminUser` – Database admin username
- `postgresAdminPassword` – Database admin password (secure)
- `mailServer` – SMTP server hostname
- `mailUsername` / `mailPassword` – SMTP credentials

---

## 5. Data Architecture

### 5.1 Entity Relationship Diagram

```
┌──────────────┐       ┌───────────────────┐       ┌──────────────┐
│    USERS     │       │  DEMAND_SKILLS    │       │    SKILLS    │
├──────────────┤       │  (Association)    │       ├──────────────┤
│ id (PK)      │       ├───────────────────┤       │ id (PK)      │
│ email        │       │ demand_id (FK)    │──────►│ name         │
│ display_name │       │ skill_id (FK)     │       │ category     │
│ password_hash│       └───────────────────┘       │ created_at   │
│ enterprise_id│               ▲                   └──────────────┘
│ role         │               │
│ is_active    │       ┌───────┴──────┐
│ created_at   │       │   DEMANDS    │
│ updated_at   │       ├──────────────┤
└──────┬───────┘       │ id (PK)      │
       │               │ project_name │
       │ created_by    │ project_code │
       │(FK)           │ du_name      │
       │               │ client_name  │
       ├──────────────►│ career_level │
       │               │ num_positions│
       │               │ priority     │
       │               │ status       │
       │               │ evaluator_*  │
       │               │ description  │
       │               │ created_by(FK)│
       │               │ created_at   │
       │               └──────┬───────┘
       │                      │ 1:N
       │               ┌──────▼───────────┐
       │ user_id (FK)  │  APPLICATIONS    │
       ├──────────────►├──────────────────┤
       │               │ id (PK)          │
       │               │ demand_id (FK)   │
       │               │ user_id (FK)     │
       │               │ applicant_name   │
       │               │ enterprise_id    │
       │               │ skills_text      │
       │               │ resume_filename  │
       │               │ resume_blob_url  │
       │               │ status           │
       │               │ remarks          │
       │               │ applied_at       │
       │               └──────┬───────────┘
       │                      │ 1:N
       │               ┌──────▼───────────────┐
       │ changed_by(FK)│ APPLICATION_HISTORY  │
       └──────────────►├──────────────────────┤
                       │ id (PK)              │
                       │ application_id (FK)  │
                       │ old_status           │
                       │ new_status           │
                       │ changed_by (FK)      │
                       │ remarks              │
                       │ changed_at           │
                       └──────────────────────┘
```

### 5.2 Database Models Summary

| Model               | Table                  | Records | Key Fields                               |
|----------------------|------------------------|---------|------------------------------------------|
| User                 | `users`                | Dynamic | email, display_name, password_hash, role |
| Skill                | `skills`               | 30+     | name, category                           |
| Demand               | `demands`              | Dynamic | project_name, career_level, priority, status |
| Application          | `applications`         | Dynamic | demand_id, user_id, status, resume_blob_url |
| ApplicationHistory   | `application_history`  | Dynamic | application_id, old_status, new_status   |
| (Association)        | `demand_skills`        | Dynamic | demand_id, skill_id                      |

### 5.3 Default Skill Taxonomy

The system seeds 30+ default skills across categories:
- **Programming:** Python, Java, JavaScript, TypeScript, C#, Go, SQL
- **Cloud:** Azure, AWS, GCP
- **Frameworks:** React, Angular, Node.js, Django, Flask, Spring Boot, .NET
- **Data:** Power BI, Tableau, Pandas, Spark, Databricks
- **DevOps:** Docker, Kubernetes, Terraform, Jenkins, GitHub Actions
- **AI/ML:** Machine Learning, GenAI, NLP, Computer Vision
- **Other:** SAP, Salesforce, ServiceNow, Agile/Scrum

---

## 6. Application Architecture

### 6.1 Frontend Architecture

| Technology      | Version | Purpose                                     |
|-----------------|---------|---------------------------------------------|
| Bootstrap       | 5.3.2   | Responsive layout, components, grid system  |
| Bootstrap Icons | 1.11.2  | Iconography throughout the UI               |
| Chart.js        | 4.4.1   | Dashboard charts and skill cloud visualization |
| Vanilla JS      | ES6+    | DOM manipulation, form interactions, AJAX   |
| Inter Font      | Google  | Typography (clean, modern sans-serif)       |

**Design Theme:**
- Primary Color: `#A100FF` (Purple)
- Dark Background: `#1A002E`
- Gradient: `linear-gradient(135deg, #A100FF, #7B00E0)`
- Card-based layout with shadow elevation
- Responsive (mobile-first via Bootstrap grid)

### 6.2 REST API Endpoints

| Method  | Endpoint                              | Auth     | Description                          |
|---------|---------------------------------------|----------|--------------------------------------|
| GET     | `/`                                   | Public   | Landing page / Dashboard redirect    |
| GET     | `/dashboard`                          | Login    | Authenticated dashboard              |
| GET/POST| `/auth/login`                         | Public   | Login form                           |
| GET     | `/auth/logout`                        | Login    | Logout + session clear               |
| GET     | `/demands/`                           | Login    | List demands (filtered, paginated)   |
| GET     | `/demands/<id>`                       | Login    | Demand detail + applications         |
| GET/POST| `/demands/create`                     | PMO      | Create new demand                    |
| GET/POST| `/demands/<id>/edit`                  | PMO      | Edit existing demand                 |
| POST    | `/demands/<id>/status`                | PMO      | Update demand status                 |
| GET     | `/demands/export`                     | PMO      | Export demands to Excel              |
| GET/POST| `/applications/apply/<demand_id>`     | Login    | Apply for a demand                   |
| GET     | `/applications/my`                    | Login    | My applications list                 |
| GET     | `/applications/manage`                | Evaluator| Manage all applications              |
| GET     | `/applications/<id>`                  | Login*   | Application detail                   |
| POST    | `/applications/<id>/status`           | Evaluator| Update application status            |
| GET     | `/applications/<id>/resume`           | Login*   | Download resume                      |
| GET     | `/applications/export`                | Evaluator| Export applications to Excel         |
| GET     | `/admin/`                             | Admin    | Admin dashboard                      |
| GET     | `/admin/users`                        | Admin    | User management list                 |
| POST    | `/admin/users/<id>/role`              | Admin    | Update user role                     |
| GET     | `/api/skill-cloud`                    | Public   | Skill cloud data (JSON)              |
| GET     | `/api/stats`                          | Login    | Dashboard statistics (JSON)          |
| GET     | `/api/skills/search?q=`               | Public   | Skill autocomplete (JSON)            |

### 6.3 Email Notification Architecture

| Event                    | Recipients                    | Template                      |
|--------------------------|-------------------------------|-------------------------------|
| Demand Created           | Demand raiser (PMO user)      | `DEMAND_CREATED_TEMPLATE`     |
| Application Received     | Demand raiser + Evaluator     | `APPLICATION_RECEIVED_TEMPLATE`|
| Status Updated           | Applicant                     | `STATUS_UPDATE_TEMPLATE`      |

- SMTP: Office 365 (port 587, TLS)
- HTML email templates with branded styling
- Graceful failure: email errors logged but don't block workflow

---

## 7. Security Architecture

### 7.1 Authentication & Authorization

| Layer              | Mechanism                                                |
|--------------------|----------------------------------------------------------|
| Authentication     | Email + Password (Werkzeug PBKDF2-SHA256 password hashing) |
| Session Management | Flask-Login with server-side sessions                    |
| CSRF Protection    | Flask-WTF CSRF tokens on all POST forms                  |
| Role-Based Access  | Custom decorators: `@pmo_required`, `@admin_required`, `@evaluator_required` |
| Future SSO         | Azure AD / Entra ID (MSAL) – code preserved as comments  |

### 7.2 Data Security

| Control                | Implementation                                            |
|------------------------|------------------------------------------------------------|
| Transport Encryption   | HTTPS enforced (`httpsOnly: true`)                        |
| Database SSL           | `sslmode=require` on PostgreSQL connection                 |
| Storage TLS            | Minimum TLS 1.2 on Azure Blob Storage                     |
| Password Storage       | Werkzeug `generate_password_hash` (PBKDF2, salted)        |
| Secret Management      | App Settings (environment variables), not in code          |
| File Upload Validation | Extension whitelist (`.docx`, `.pptx`), 10MB max size     |
| SQL Injection Prevention| SQLAlchemy ORM parameterized queries                      |
| XSS Prevention         | Jinja2 auto-escaping + CSRF tokens                        |
| Upload Filename Safety | `werkzeug.utils.secure_filename` + UUID-based renaming     |

---

## 8. Deployment Architecture

### 8.1 Deployment Pipeline

```
Developer Workstation
        │
        │  git push origin main
        ▼
┌───────────────┐
│   GitHub      │
│   Repository  │
│   (main)      │
└───────┬───────┘
        │  Zip Deploy / az webapp deploy
        ▼
┌───────────────────────────────────┐
│   Azure App Service (Oryx Build) │
│   ┌───────────────────────────┐  │
│   │  1. Detect Python 3.11    │  │
│   │  2. Create venv (antenv)  │  │
│   │  3. pip install -r req.txt│  │
│   │  4. Compress → tar.gz    │  │
│   │  5. Deploy to /home/site │  │
│   └───────────────────────────┘  │
│                                   │
│   Startup: gunicorn wsgi:app      │
└───────────────────────────────────┘
```

### 8.2 Environment Configuration

| Environment   | Database      | Auth           | Storage       | Debug |
|---------------|---------------|----------------|---------------|-------|
| Development   | SQLite (local)| DB Login       | Local filesystem | ON    |
| Testing       | SQLite (memory)| Disabled CSRF | N/A           | OFF   |
| Production    | PostgreSQL    | DB Login       | Azure Blob    | OFF   |

### 8.3 Azure Resource Naming Convention

| Resource                | Name Pattern                        | Example                         |
|-------------------------|-------------------------------------|---------------------------------|
| Resource Group          | `rg-{appname}`                      | `rg-skillhive`                  |
| App Service Plan        | `{appname}-plan`                    | `skillhive-accenture-plan`      |
| App Service             | `{appname}`                         | `skillhive-accenture`           |
| PostgreSQL Server       | `{appname}-pg`                      | `skillhive-accenture-pg`        |
| Storage Account         | `{appname}store`                    | `skillhiveaccenturestore`       |
| Application Insights    | `{appname}-insights`                | `skillhive-accenture-insights`  |
| Log Analytics Workspace | `{appname}-logs`                    | `skillhive-accenture-logs`      |

---

## 9. Non-Functional Requirements

### 9.1 Performance

| Metric                 | Target                          | Mechanism                        |
|------------------------|---------------------------------|----------------------------------|
| Page Load Time         | < 2 seconds                     | Gunicorn multi-worker, Always On |
| Concurrent Users       | 50–100                          | B1 plan (scale up to S1/P1)     |
| Database Queries       | < 100ms per request             | SQLAlchemy lazy loading, indexes |
| File Upload Limit      | 10 MB                           | `MAX_CONTENT_LENGTH` config      |

### 9.2 Availability & Scalability

| Aspect               | Current                         | Path to Scale                    |
|-----------------------|---------------------------------|----------------------------------|
| App Service           | B1 (single instance)            | Scale UP to S1/P1v3; Scale OUT via plan |
| Database              | B1ms Burstable                  | Scale to GP/MO tiers             |
| Storage               | LRS (single region)             | Upgrade to GRS/ZRS               |
| Monitoring            | App Insights + Log Analytics    | Add Alerts, Workbooks            |

### 9.3 Backup & Recovery

| Component    | Backup Strategy                                              |
|--------------|--------------------------------------------------------------|
| Database     | Azure-managed backup, 7-day retention, point-in-time restore |
| Blob Storage | LRS (3 copies within datacenter)                             |
| Application  | GitHub repository (source of truth)                          |
| Secrets      | App Settings (regenerate from Azure Portal if needed)        |

---

## 10. Technology Stack Summary

### 10.1 Backend

| Component         | Technology             | Version   |
|-------------------|------------------------|-----------|
| Language          | Python                 | 3.11      |
| Web Framework     | Flask                  | 3.0.0     |
| WSGI Server       | Gunicorn               | 21.1.0    |
| ORM               | Flask-SQLAlchemy       | 3.1.1     |
| Migrations        | Flask-Migrate (Alembic)| 4.0.5     |
| Authentication    | Flask-Login            | 0.6.3     |
| Forms             | Flask-WTF + WTForms    | 1.2.1     |
| Email             | Flask-Mail             | 0.9.1     |
| Excel Export      | openpyxl               | 3.1.2     |
| CSRF Protection   | Flask-WTF CSRFProtect  | 1.2.1     |
| Email Validation  | email-validator        | 2.1.0     |
| Environment       | python-dotenv          | 1.0.0     |

### 10.2 Azure SDKs

| SDK                    | Version | Purpose                         |
|------------------------|---------|----------------------------------|
| azure-storage-blob     | 12.19.0 | Blob Storage operations          |
| azure-identity         | 1.15.0  | Azure credential management      |
| psycopg2-binary        | 2.9.9   | PostgreSQL driver                |

### 10.3 Frontend

| Technology       | Version | Purpose                          |
|------------------|---------|----------------------------------|
| Bootstrap        | 5.3.2   | CSS framework                    |
| Bootstrap Icons  | 1.11.2  | Icon library                     |
| Chart.js         | 4.4.1   | Data visualization               |
| Inter Font       | Latest  | Typography                       |
| Vanilla JavaScript | ES6+ | Client-side interactions          |

### 10.4 DevOps & Infrastructure

| Tool / Service                | Purpose                          |
|-------------------------------|----------------------------------|
| GitHub                        | Source code repository           |
| ARM Templates (JSON)          | Infrastructure-as-Code           |
| Azure Oryx Build System       | Automated Python build pipeline  |
| Azure App Service Deployment  | Zip deploy + Oryx integration    |
| pytest                        | Unit & integration testing       |

---

*End of Document*
