# ShelterTree

<div align="left">
  
  **The Definitive Pan-African Property Intelligence & Review Platform**
  
  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg?logo=python&logoColor=white)](#)
  [![Django](https://img.shields.io/badge/Django-5.2+-092E20.svg?logo=django&logoColor=white)](#)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Advanced-316192.svg?logo=postgresql&logoColor=white)](#)
  [![HTMX](https://img.shields.io/badge/HTMX-Reactive-336699.svg)](#)
  [![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED.svg?logo=docker&logoColor=white)](#)

</div>

## Overview

**ShelterTree** bridges the massive trust deficit in the African real estate market. It operates as a dual-sided platform:
1. **B2C Community Engine:** A crowdsourced, hyper-detailed review platform empowering tenants and buyers to share authentic, ground-truth data about properties, utilities, and neighborhoods.
2. **B2B / Premium Intelligence:** A high-ticket, tech-enabled forensic due diligence service (ShelterTree Intelligence) allowing high-net-worth individuals to commission rigorous structural, environmental, and legal audits before purchasing real estate.

Designed with a "First-Principles" architectural mindset, the platform prioritizes absolute data integrity, sub-100ms UI reactivity without SPA bloat, and enterprise-grade scalability.

---

## Core Architectural Highlights

This repository demonstrates advanced full-stack engineering, straying far from basic CRUD applications. 

### 1. "Lazy Registration" (Advanced State Management)
To eliminate conversion friction, the platform implements a sophisticated "Draft & Claim" pattern. Anonymous users can write comprehensive reviews or add properties without logging in. 
* **The Mechanism:** Data is immediately persisted to the PostgreSQL database in a `PENDING_SIGNUP` ghost state to prevent data loss. A session-based ledger tracks the asset ID.
* **The Handoff:** Upon manual or OAuth (Google) authentication, Django Signals (`user_signed_up`, `user_logged_in`) instantly execute a "Trusted Handoff," transferring data ownership to the verified user.
* **Traffic Control:** A custom `OnboardingMiddleware` and extended `AccountAdapter` intelligently route users to specific success/claim handlers post-login, safely bypassing standard onboarding flows to preserve the user's intended task context.

### 2. High-Performance Database Engineering
* **Zero N+1 Queries:** Heavy reliance on Django’s `OuterRef`, `Subquery`, and `Coalesce` within custom Model Managers to perform complex analytical aggregations (e.g., aggregating 1-5 star ratings across multiple categories, filtering only by `APPROVED` statuses) in single, highly optimized database hits.
* **Hybrid Search Engine:** Engineered a proprietary search algorithm combining **PostgreSQL Full-Text Search** (`SearchVector`, `SearchRank`) for high-relevance lexical matching with a broad substring fallback. Results are unified and returned as a single, chainable QuerySet utilizing `Case/When` preserved database ordering.

### 3. Service Layer Abstraction & Event-Driven Analytics
* **Decoupled Integrations:** Third-party APIs (ZeptoMail, Twilio, Paystack) are abstracted into isolated Service Layers (e.g., `NotificationService`). Views never handle raw API calls.
* **Backend-Driven Analytics:** Instead of fragile frontend tracking, conversions are tracked via a custom `EventBus`. The Django backend pushes verified conversion events to the frontend `dataLayer` asynchronously, ensuring a single source of truth for GA4 and Meta Pixel tracking.

### 4. SPA-Like Reactivity (Without the JavaScript Bloat)
* **HTMX Architecture:** Leveraged HTMX for complex DOM mutations, dynamic dependent dropdowns, and asynchronous form submissions. This achieved the UX of a modern React/Vue application while keeping the state securely managed on the server and reducing the JavaScript bundle size by over 80%.
* **Smart Place Autocomplete:** A custom, debounced JavaScript integration with the Google Maps/Places API that normalizes unstructured African address data into clean backend database fields seamlessly.

---

## The Business Verticals

* **ShelterTree Reviews:** The core UGC engine with rigorous multi-stage moderation queues, brute-force-protected phone verification (OTP), and dynamic reputation scoring.
* **ShelterTree Intelligence:** A lead-capture and operational workflow engine for forensic property audits, featuring dynamic pricing tiers, honeypot bot-protection, and instant SLA-driven internal alerts.
* **Xylem Logistics (Asset-Light Brokerage):** An integrated logistics pipeline to facilitate premium relocations, featuring an "Ecosystem Flywheel" that incentivizes users to leave property reviews in exchange for moving discounts.

---

## Tech Stack

**Backend:**
* Python 3.12+
* Django 5.2+ (Strict Class-Based Views, Custom Middleware)
* PostgreSQL (Managed DB, pg_trgm, Full-Text Search)

**Frontend:**
* HTMX (AJAX, CSS Transitions, WebSockets)
* Bootstrap 5 (Customized)
* SCSS (Compiled on-the-fly via `django-sass-processor`)
* Vanilla JavaScript (ES6+ for specific API bridges)

**Infrastructure & DevOps:**
* Docker & Docker Compose
* AWS S3 (Media Storage via `django-storages`)
* WhiteNoise (Static file serving)
* Render (Production IaaS hosting)
* `python-decouple` (Environment & Secrets Management)

---

## Local Development Setup

The project is fully containerized for a frictionless development experience.

### Prerequisites
* [Docker](https://docs.docker.com/get-docker/) & Docker Compose
* Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Marrtinerz/sheltertree.git
   cd sheltertree
   ```

2. **Configure Environment Variables**
   Copy the example environment file and populate it with your local/test keys.
   ```bash
   cp .env.example .env
   ```
   *(Ensure you add your Google Maps API key to utilize the smart location search).*

3. **Build and Run the Docker Containers**
   ```bash
   docker-compose up --build
   ```

4. **Run Database Migrations**
   Open a new terminal window/tab:
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. **Create a Superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

6. **Access the Application**
   * Web App: `http://localhost:8000`
   * Django Admin: `http://localhost:8000/admin`

---

## Security
* Absolute separation of configuration and code. No secrets are committed to version control.
* Built-in Content Security Policy (CSP) headers to mitigate XSS.
* Custom user authentication enforcing account email verification and robust lockout mechanisms against brute-force OTP guessing.
* Development and Production environments are cleanly separated via distinct settings files (`settings/base.py`, `settings/development.py`, `settings/production.py`).

---

<div align="center">
  <p>Architected and Built by <strong>Martins Nnamchi</strong></p>
  <p>
    <a href="mailto:mnnamchi@gmail.com">Email</a> •
    <a href="https://linkedin.com/in/mnnamchi/">LinkedIn</a> •
    <a href="https://marrtinerz.github.io/">Portfolio</a>
  </p>
</div>