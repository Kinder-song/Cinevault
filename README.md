# CineVault

A beautifully designed local video management and streaming website.

## Setup

1. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   - Copy `.env.example` to `.env` and adjust settings
   - Ensure MySQL database is running

4. Initialize database:
   - First run will auto-create admin user

5. Run the application:
   ```bash
   python app.py
   ```

6. Access at `http://localhost:55300`

## Default Credentials
- Username: `admin`
- Password: `admin123`