# Safos-Backend

**Backend service for a Telegram-based order management bot**\
This backend powers a Telegram bot used by multiple roles --- **admin**,
**agent**, and **dostavchik** (delivery) --- to manage orders, handle
financials, and drive business logic.

------------------------------------------------------------------------

## 📌 Table of Contents

-   [Overview](#overview)
-   [Key Features](#key-features)
-   [Technology Stack](#technology-stack)
-   [Architecture & Roles](#architecture--roles)
-   [Getting Started](#getting-started)
    -   [Prerequisites](#prerequisites)
    -   [Installation](#installation)
    -   [Environment Variables](#environment-variables)
    -   [Running Locally](#running-locally)
-   [API Documentation](#api-documentation)
-   [Data Models & Database](#data-models--database)
-   [Business Logic](#business-logic)
-   [Deployment](#deployment)
-   [Potential Improvements](#potential-improvements)
-   [Contributing](#contributing)
-   [License](#license)

------------------------------------------------------------------------

## 🧾 Overview

Safos-Backend is a **FastAPI** service that supports a Telegram bot for
managing orders in a business. Through this backend:

-   📱 **Users register via Telegram** (with Telegram contact and ID).
    If the user already exists in the database, they are granted access.
-   🧑‍💼 **Admins** run the business: they manage orders, oversee agent
    performance, and control company financials (revenues,
    cancellations, salaries).
-   🚚 **Agents & Dostavchiks** (delivery users) take, cancel, or update
    orders via the bot.
-   💰 The backend tracks every order's status, financial data, and
    computes employee payouts according to internal business logic.

🔗 This ensures a strong integration between Telegram UI and trusted
backend automation.

------------------------------------------------------------------------

## 🚀 Key Features

-   🔐 **Role-based access**: Admin, Agent, Dostavchik
-   📲 **Telegram authentication** via Telegram ID + contact info
-   📦 **Order lifecycle management**: creation, cancellation, updates
-   💵 **Financial calculations**: revenues, cancellations, salaries
-   📊 **Analytics**: orders per user, order status, compensation
-   🔎 **Complex business logic** (e.g., cancellation effects)
-   🛡️ **Secure validation using FastAPI + Pydantic**

------------------------------------------------------------------------

## 🛠 Technology Stack

  Component           Technology
  ------------------- ------------------------------
  Backend Framework   FastAPI
  Language            Python
  Database            PostgreSQL
  ORM                 SQLAlchemy
  Validation          Pydantic / Pydantic Settings
  Config              python-dotenv
  Server              Uvicorn
  Deployment          Railway

🔗 Production: `https://safos-backend-production.up.railway.app`

------------------------------------------------------------------------

## 🏗 Architecture & Roles

+-------------------+ +-----------------+ +-------------------+ \|
Telegram Bot \| \<---\> \| Safos Backend \| \<--\> \| Database Layer \|
\| (Admin/Agent/Del) \| \| (FastAPI + API) \| \| (PostgreSQL + ORM)\|
+-------------------+ +-----------------+ +-------------------+

-   🤖 **Telegram Bot**: User interface for business\
-   ⚙️ **Backend (FastAPI)**: Processes requests, validates logic,
    exposes REST APIs\
-   🗄 **Database**: Stores users, orders, finances, roles, metrics

------------------------------------------------------------------------

## 🔧 Getting Started

### 📌 Prerequisites

-   Python 3.9+
-   PostgreSQL
-   Git

### 📥 Installation

``` bash
git clone https://github.com/asliddintursunoff/Safos-Backend.git
cd Safos-Backend
```

Create a virtual environment:

``` bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# OR
venv\Scripts\activate      # Windows
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

### 🔑 Environment Variables

Create a `.env` file with:

    DATABASE_URL=postgresql://user:password@host:port/dbname
    SECRET_KEY=your_secret_key
    TELEGRAM_BOT_TOKEN=your_telegram_bot_token

------------------------------------------------------------------------

### ▶️ Running Locally

Start server:

``` bash
uvicorn app.main:app --reload
```

Server will run on:

    http://127.0.0.1:8000

------------------------------------------------------------------------

## 📚 API Documentation

Swagger Docs:

    https://safos-backend-production.up.railway.app/docs

------------------------------------------------------------------------

## 🗃 Data Models & Database

### 📌 User Model

-   Telegram ID\
-   Contact Phone\
-   Role (Admin / Agent / Dostavchik)

### 📌 Order Model

-   Status (active / canceled / completed)\
-   Assigned agent/driver\
-   Price & financial metadata

### 📌 Finance Model

-   Salary/commission tracking\
-   Revenue & cancellation logic

------------------------------------------------------------------------

## 🧠 Business Logic

-   When an order is created, it's assigned to an agent/delivery.\
-   When canceled, business rules process refund/penalties.\
-   Admin sees how many orders each person has taken, delivered, or
    canceled.\
-   Salaries/commissions are computed automatically based on business
    model.

------------------------------------------------------------------------

## 🚀 Deployment

Deployed on Railway with Uvicorn + PostgreSQL.

Live Server:

    https://safos-backend-production.up.railway.app

------------------------------------------------------------------------

## 📈 Potential Improvements

-   JWT Authentication\
-   Tests (Pytest)\
-   Docker containerization\
-   Background workers (Celery/RQ)\
-   Better logging + monitoring

------------------------------------------------------------------------

## 🤝 Contributing

    1. Fork repo
    2. git checkout -b feature/NewFeature
    3. git commit -m "Add new feature"
    4. git push origin feature/NewFeature
    5. Open Pull Request

------------------------------------------------------------------------

## 📄 License

MIT License
