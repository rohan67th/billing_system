Smart POS & Retail Billing System

A robust, role-based Point of Sale (POS) and Inventory Management System built with Django 5 and PostgreSQL. This application facilitates seamless billing, stock management, and sales analytics for retail businesses, featuring integrated Razorpay payments and PDF invoicing.

🚀 Features

👤 Role-Based Access Control

Superuser/Admin: Manage system users (Managers, Cashiers), view global system stats, and configure application settings.

Manager: Access detailed sales dashboards, manage product inventory, view profit/margin reports, and upload bulk stock via JSON.

Cashier: Dedicated POS interface for fast billing, multi-tab cart management, and checkout.

🛒 Point of Sale (POS)

Multi-Cart Functionality: Cashiers can handle multiple customers simultaneously by switching between active carts.

Real-time Stock Check: Prevents billing items that exceed current stock levels.

Customer Lookup: Quick search for existing customers by phone number.

Payment Modes: Support for Cash and Online Payments (UPI/Card via Razorpay).

📦 Inventory Management

CRUD Operations: Add, edit, and soft-delete products.

Stock Alerts: Visual indicators for low-stock items.

Bulk Upload: Import products efficiently using JSON files.

Automated SKU: Auto-generation of product codes (e.g., PRD001).

📊 Analytics & Reporting

Interactive Dashboards: Weekly, Monthly, and 6-Month sales trends.

Financial Reports: Profit margins, category revenue, and cashier performance.

PDF Invoicing: Automatic generation of professional PDF invoices upon checkout.

🛠️ Tech Stack

Backend: Python 3.10+, Django 5.2

Database: PostgreSQL

Configuration: Python-Decouple (Environment variables)

Payments: Razorpay Integration

Frontend: HTML5, CSS3, JavaScript (AJAX for dynamic POS interactions)

⚙️ Installation & Setup

1. Clone the Repository

git clone [https://github.com/rohan67th/billing_system.git]
cd billing-system


2. Create and Activate Virtual Environment

# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate


3. Install Dependencies

pip install -r requirements.txt


(Ensure django, psycopg2-binary, python-decouple, and razorpay are included)

4. Configure Environment Variables

Create a .env file in the root directory (next to manage.py) and add the following configurations:

# Django Settings
DEBUG=True
SECRET_KEY=your_secret_key_here

# Database Configuration (PostgreSQL)
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Razorpay Payment Gateway
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret_key


5. Database Setup

python manage.py makemigrations
python manage.py migrate


6. Create Superuser (Admin)

python manage.py createsuperuser


7. Run the Server

python manage.py runserver


Visit http://127.0.0.1:8000/ in your browser.