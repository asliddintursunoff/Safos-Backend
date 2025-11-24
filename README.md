

```markdown
# Safos-Backend

**Backend service for a Telegram-based order management bot**  
Safos-Backend is the server-side application for a Telegram bot that **manages orders** for a business. It allows multiple user roles — **admin**, **agent**, and **dostavchik** (delivery) — to create, update, delete, and track orders, while handling company finances and user management.

---

## 📌 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Architecture & Roles](#architecture--roles)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running Locally](#running-locally)
- [API Documentation](#api-documentation)
- [Data Models & Database](#data-models--database)
- [Business Logic](#business-logic)
- [Deployment](#deployment)
- [Potential Improvements](#potential-improvements)
- [Contributing](#contributing)
- [License](#license)

---

## 🧾 Overview

Safos-Backend is a **FastAPI** backend that supports a Telegram bot for **order management**.  
The system allows:

- Users to **register via Telegram** (using Telegram ID and contact info).  
- **Admins** to manage all orders, monitor users (agents/delivery), and oversee company financials.  
- **Agents and Dostavchiks** to create, update, delete, and complete orders via the bot.  
- Tracking **order lifecycle**, user performance, and computing financial data automatically.

The main purpose of this backend is **efficient order management and processing** for the business.

---

## 🚀 Key Features

- 🔐 **Role-based access**: Admin, Agent, Dostavchik  
- 📲 **Telegram-based authentication** (ID + contact)  
- 📦 **Order management**: create, update, delete, complete  
- 💰 **Financial management**: track revenues, cancellations, and salaries  
- 📊 **Analytics & reporting**: orders per user, performance tracking  
- 🧩 **Business logic**: handle cancellations, salary calculations, and order validations  
- 🛡️ **Secure and validated API** using FastAPI + Pydantic

---

## 🛠 Technology Stack

| Component        | Technology |
|-----------------|------------|
| Backend Framework | FastAPI |
| Language         | Python |
| Database         | PostgreSQL |
| ORM              | SQLAlchemy |
| Validation       | Pydantic / Pydantic Settings |
| Config           | python-dotenv |
| Server           | Uvicorn |
| Deployment       | Railway |

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

````

- 🤖 **Telegram Bot**: User interface for admins, agents, and delivery users  
- ⚙️ **Backend (FastAPI)**: Handles all business logic, validation, and API endpoints  
- 🗄 **Database**: Stores users, orders, financial data, and roles

---

## 🔧 Getting Started

### 📌 Prerequisites

- Python 3.9+  
- PostgreSQL  
- Git  

### 📥 Installation

```bash
git clone https://github.com/asliddintursunoff/Safos-Backend.git
cd Safos-Backend
````

📌 Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# OR
venv\Scripts\activate      # Windows
```

📌 Install dependencies:

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

Interactive Swagger documentation:

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
* Calculate salaries and commissions based on order activity
* Handle cancellations and their financial impact
* Admin can view all order statistics and financial reports

---

## 🚀 Deployment

* Deployed on **Railway**: [https://safos-backend-production.up.railway.app](https://safos-backend-production.up.railway.app)
* Uses environment variables for configuration
* Runs on **Uvicorn** in production

---

## 📈 Potential Improvements

* JWT authentication for API security
* Unit & integration tests
* Dockerized deployment
* Background task processing (Celery / RQ)
* Logging, monitoring, error tracking

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

```

