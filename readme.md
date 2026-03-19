# CareerNest: Centralized Opportunity Management

CareerNest is a full-stack platform designed to help students discover and track job opportunities while providing administrators with a streamlined portal to manage listings.
 
##  Key Features

* **Job Discovery:** Search and filter by category, job type, location, and salary.
* **Google Authentication:** Secure sign-in for students to track applications and for admins to manage the board.
* **Application Tracking:** Students can view the live status of their applications (Pending, Reviewing, Shortlisted, etc.).
* **Admin Dashboard:** Restricted portal for posting jobs, managing company profiles, and toggling listing visibility.
* **Persistence:** MongoDB integration ensures all data survives server restarts.
* **Responsive UI:** Fully optimized for mobile and desktop with a premium dark-themed design.

---

##  Technology Stack

* **Frontend:** HTML5, CSS3 (Custom Variables, Animations), Vanilla JavaScript (ES6+).
* **Backend:** Python 3.9+, FastAPI, Pydantic, Uvicorn.
* **Database:** MongoDB (Local or Atlas) via `pymongo`.
* **Authentication:** Google Identity Services (GIS).

---

## 📂 Project Structure

```text
├── main.py            # FastAPI Backend API & Database Logic
├── index.html         # Main Student/User Frontend
├── admin.html         # Administrator Management Portal
├── config.js          # Frontend Configuration (API URLs & Auth IDs)
└── .env               # Environment variables (Backend credentials)

```

---

## ⚙️ Setup & Installation

### 1. Prerequisites

* **Python 3.9+** installed.
* **MongoDB** installed locally or a **MongoDB Atlas** connection string.
* **Google Cloud Console Account** (to generate a Client ID).

### 2. Backend Setup

1. **Install Dependencies:**
```bash
pip install fastapi uvicorn pymongo motor certifi python-dotenv requests

```


2. **Configure Environment:** Create a `.env` file in the root directory:
```env
MONGO_URI=mongodb://localhost:27017/careernest

```


3. **Run the Server:**
```bash
uvicorn main:app --reload
```


The API will be available at `http://localhost:8000`. You can view the interactive documentation at `http://localhost:8000/docs`.

### 3. Frontend Setup

1. **Google Client ID:** * Go to the [Google Cloud Console](https://console.cloud.google.com/).
* Create a "Web Application" OAuth Client ID.
* Add `http://localhost` and `http://127.0.0.1` to the **Authorized JavaScript origins**.


2. **Configure `config.js`:** Open `config.js` and paste your credentials:
```javascript
const CONFIG = {
  GOOGLE_CLIENT_ID: "YOUR_GOOGLE_CLIENT_ID_HERE.apps.googleusercontent.com",
  ADMIN_EMAIL: "your-email@gmail.com", // This email will have Admin access
  API_BASE: "http://localhost:8000",
};

```



---

## 📖 Usage Guide

### For Students (`index.html`)

* **Browse:** Scroll through listings or use the sidebar to filter for "Internships" or "Remote" roles.
* **Sign In:** Use the "Sign In" button to connect your Google account.
* **Apply:** Click "Apply Now." If signed in, your details will auto-fill.
* **Track:** Visit the "My Apps" tab to see the current status of your applications retrieved directly from the backend.

### For Administrators (`admin.html`)

* **Access:** Only the user matching `ADMIN_EMAIL` in `config.js` can pass the Auth Gate.
* **Post Jobs:** Select a company (or create a new one via the modal) and fill out the job details.
* **Manage:** Toggle jobs between "Active" and "Inactive" or delete old listings. Inactive jobs are automatically hidden from the main student board.

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/jobs` | List all active jobs with filters/search. |
| `POST` | `/jobs` | Create a new job listing (Admin). |
| `POST` | `/applications` | Submit a new job application. |
| `GET` | `/students/{email}/applications` | Fetch applications for a specific user. |
| `POST` | `/companies` | Register a new company profile. |
| `GET` | `/stats` | Get platform-wide metrics (Jobs, Apps, etc.). |

---

## ⚠️ Security Notes

* **config.js:** Ensure this file is added to your `.gitignore` before pushing to a public repository to protect your `GOOGLE_CLIENT_ID`.
* **Admin Access:** The current admin check is email-based on the frontend. For production, implement JWT verification on the backend `/jobs` POST/PATCH/DELETE routes.

Would you like me to help you write a deployment script for this project?