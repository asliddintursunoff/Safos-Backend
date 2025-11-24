# Safos-Backend

**Backend service for a Telegram-based order management bot**

Safos-Backend is a robust server-side application for a Telegram bot that **manages orders** for a business. It supports multiple user roles — **Admin**, **Agent**, and **Dostavchik** (delivery) — allowing them to create, update, delete, and track orders while managing company finances and user operations.

---

## 📌 Table of Contents

* [Overview](#overview)
* [Key Features](#key-features)
* [Technology Stack](#technology-stack)
* [Architecture & Roles](#architecture--roles)
* [Getting Started](#getting-started)

  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
  * [Environment Variables](#environment-variables)
  * [Running Locally](#running-locally)
* [API Documentation](#api-documentation)
* [Data Models & Database](#data-models--database)
* [Business Logic](#business-logic)
* [Deployment](#deployment)
* [Potential Improvements](#potential-improvements)
* [Contributing](#contributing)
* [License](#license)

---

## 🧾 Overview

Safos-Backend is a **FastAPI** backend supporting a Telegram bot for **order management**. The system allows:

* User registration via Telegram (Telegram ID + contact info)
* **Admins**: manage all orders, monitor users, and oversee company finances
* **Agents & Dostavchiks**: create, update, delete, and complete orders
* Track **order lifecycle**, user performance, and compute financial data automatically

The goal is **efficient order management and processing**.

---

## 🚀 Key Features

* 🔐 **Role-based access**: Admin, Agent, Dostavchik
* 📲 **Telegram authentication** (ID + contact)
* 📦 **Order management**: create, update, delete, complete
* 💰 **Financial management**: track revenues, cancellations, and salaries
* 📊 **Analytics & reporting**: orders per user, performance tracking
* 🧩 **Business logic**: handle cancellations, salary calculations, order validations
* 🛡️ **Secure and validated API**: FastAPI + Pydantic

---

## 🛠 Technology Stack

| Component         | Technology                   |
| ----------------- | ---------------------------- |
| Backend Framework | FastAPI                      |
| Language          | Python                       |
| Database          | PostgreSQL                   |
| ORM               | SQLAlchemy                   |
| Validation        | Pydantic / Pydantic Settings |
| Config            | python-dotenv                |
| Server            | Uvicorn                      |
| Deployment        | Railway                      |

🔗 **Production API**: [https://safos-backend-production.up.railway.app](https://safos-backend-production.up.railway.app)
🔗 **Swagger Docs**: [https://safos-backend-production.up.railway.app/docs](https://safos-backend-production.up.railway.app/docs)
🔗 **Local Docs**: `/backend/docs` (if running locally)

---

## 🏗 Architecture & Roles

```
+-------------------+       +-----------------+       +-------------------+
|   Telegram Bot     | <---> |   Safos Backend  | <--> |  Database Layer   |
|  (Admin/Agent/Del) |       |  (FastAPI + API) |       | (PostgreSQL + ORM)|
+-------------------+       +-----------------+       +-------------------+
```

* 🤖 **Telegram Bot**: Interface for Admins, Agents, and Dostavchiks
* ⚙️ **Backend (FastAPI)**: Business logic, validation, and API endpoints
* 🗄 **Database**: Stores users, orders, financial data, and roles

---

## 🔧 Getting Started

### 📌 Prerequisites

* Python 3.9+
* PostgreSQL
* Git

### 📥 Installation

```bash
git clone https://github.com/asliddintursunoff/Safos-Backend.git
cd Safos-Backend
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# OR
venv\Scripts\activate      # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

### 🔑 Environment Variables

Create a `.env` file:

```ini
DATABASE_URL=postgresql://user:password@host:port/dbname
SECRET_KEY=your_secret_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

---

### ▶️ Running Locally

```bash
uvicorn app.main:app --reload
```

Server URL:

```
http://127.0.0.1:8000
```

---

## 📚 API Documentation

* **Online Docs**: [`/docs`](https://safos-backend-production.up.railway.app/docs)
* **Local Docs**: `/backend/docs`

---

## 🗃 Data Models & Database

### 📌 User Model

* Telegram ID
* Contact phone
* Role: Admin / Agent / Dostavchik

### 📌 Order Model

* Status: active / canceled / completed
* Assigned agent/delivery person
* Price and financial metadata

### 📌 Finance Model

* Salary/commission tracking
* Revenue & cancellation logic

---

## 🧠 Business Logic

* Create, update, delete, and complete orders
* Track which user handled each order
* Calculate salaries and commissions
* Handle cancellations and financial impacts
* Admins can view all order statistics and reports

---

## 🚀 Deployment

* **Railway deployment**: [https://safos-backend-production.up.railway.app](https://safos-backend-production.up.railway.app)
* Uses environment variables for configuration
* Runs on **Uvicorn** in production

---

## 📈 Potential Improvements

* JWT authentication for API security
* Unit & integration tests
* Dockerized deployment
* Background task processing (Celery / RQ)
* Logging, monitoring, and error tracking

---

## 🤝 Contributing

```bash
1. Fork the repository
2. Create a new branch: git checkout -b feature/NewFeature
3. Commit: git commit -m "Add new feature"
4. Push: git push origin feature/NewFeature
5. Open a Pull Request
```

---

## 📄 License

This project is licensed under the **MIT License**.
