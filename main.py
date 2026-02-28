from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
import uuid
import os
import requests
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
import certifi

load_dotenv()

# ──────────────────────────────────────────────
# MongoDB Connection
# ──────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/careernest")
_client   = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
_db       = _client["careernest"]

col_companies:    Collection = _db["companies"]
col_jobs:         Collection = _db["jobs"]
col_applications: Collection = _db["applications"]
col_bookmarks:    Collection = _db["bookmarks"]

# Indexes for fast querying
col_companies.create_index("id", unique=True)
col_jobs.create_index("id", unique=True)
col_jobs.create_index("is_active")
col_jobs.create_index("company_id")
col_applications.create_index("id", unique=True)
col_applications.create_index(
    [("job_id", ASCENDING), ("applicant_email", ASCENDING)]
)
col_bookmarks.create_index(
    [("student_email", ASCENDING), ("job_id", ASCENDING)]
)

# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────
app = FastAPI(
    title="CareerNest Job Board API",
    description="""
## Centralized Opportunity Management — Job Board API

This API powers the CareerNest platform with **persistent MongoDB storage**.

### Features
- Browse & Search listings with filters
- Apply directly (with optional Google Auth verification)
- Bookmark opportunities
- Company profiles
- Application tracking per student
- Data persists across server restarts

### Quick Start
1. `POST /companies` — register a company, note its `id`
2. `POST /jobs` — post a listing using that company `id`
3. `GET /jobs` — browse
4. `POST /applications` — apply (frontend-friendly)
""",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────
class JobType(str, Enum):
    full_time  = "Full-Time"
    part_time  = "Part-Time"
    internship = "Internship"
    contract   = "Contract"
    remote     = "Remote"
    hybrid     = "Hybrid"


class ExperienceLevel(str, Enum):
    entry      = "Entry Level"
    mid        = "Mid Level"
    senior     = "Senior Level"
    internship = "Internship / No Experience"


class ApplicationStatus(str, Enum):
    pending     = "Pending"
    reviewing   = "Reviewing"
    shortlisted = "Shortlisted"
    rejected    = "Rejected"
    accepted    = "Accepted"


class JobCategory(str, Enum):
    technology  = "Technology"
    finance     = "Finance"
    marketing   = "Marketing"
    design      = "Design"
    operations  = "Operations"
    hr          = "Human Resources"
    sales       = "Sales"
    engineering = "Engineering"
    healthcare  = "Healthcare"
    education   = "Education"
    other       = "Other"


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name:        str
    industry:    str
    website:     Optional[str] = None
    description: Optional[str] = None
    logo_url:    Optional[str] = None
    location:    str

    class Config:
        json_schema_extra = {"example": {
            "name": "TechNova Solutions", "industry": "Software Development",
            "website": "https://technova.io",
            "description": "Building next-gen cloud platforms.",
            "logo_url": "https://technova.io/logo.png",
            "location": "Bangalore, India",
        }}


class JobCreate(BaseModel):
    title:                str
    company_id:           str
    category:             JobCategory
    job_type:             JobType
    experience_level:     ExperienceLevel
    location:             str
    is_remote:            bool = False
    description:          str
    responsibilities:     List[str]
    requirements:         List[str]
    nice_to_have:         Optional[List[str]] = []
    salary_min:           Optional[int]       = None
    salary_max:           Optional[int]       = None
    salary_currency:      str                 = "INR"
    application_deadline: Optional[date]      = None
    openings:             int                 = 1
    tags:                 Optional[List[str]] = []


class JobUpdate(BaseModel):
    title:                Optional[str]       = None
    description:          Optional[str]       = None
    responsibilities:     Optional[List[str]] = None
    requirements:         Optional[List[str]] = None
    nice_to_have:         Optional[List[str]] = None
    salary_min:           Optional[int]       = None
    salary_max:           Optional[int]       = None
    application_deadline: Optional[date]      = None
    openings:             Optional[int]       = None
    is_active:            Optional[bool]      = None
    tags:                 Optional[List[str]] = None


class ApplicationCreate(BaseModel):
    """Used by POST /jobs/{id}/apply"""
    applicant_name:      str
    applicant_email:     str
    google_access_token: Optional[str]   = None
    phone:               Optional[str]   = None
    resume_url:          str
    cover_letter:        Optional[str]   = None
    linkedin_url:        Optional[str]   = None
    portfolio_url:       Optional[str]   = None
    years_of_experience: Optional[float] = 0
    current_institution: Optional[str]   = None
    graduation_year:     Optional[int]   = None


class ApplicationCreateCompat(BaseModel):
    """
    Frontend-friendly shape for POST /applications.
    Maps field names sent by the UI to the internal ApplicationCreate model.
    """
    job_id:              str
    full_name:           str
    email:               EmailStr
    google_access_token: Optional[str]   = None
    phone:               Optional[str]   = None
    resume_url:          str
    cover_letter:        Optional[str]   = None
    linkedin_url:        Optional[str]   = None
    portfolio_url:       Optional[str]   = None
    years_experience:    Optional[float] = 0
    institution:         Optional[str]   = None
    graduation_year:     Optional[int]   = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes:  Optional[str] = None


class BookmarkCreate(BaseModel):
    student_email: str
    job_id:        str


# ──────────────────────────────────────────────
# MongoDB Helpers
# ──────────────────────────────────────────────
def _clean(doc: dict) -> dict:
    """Strip MongoDB internal _id."""
    if doc and "_id" in doc:
        doc = dict(doc)
        del doc["_id"]
    return doc


def _enrich_job(job: dict) -> dict:
    """Attach the company sub-document to a job dict."""
    job = _clean(job)
    company = col_companies.find_one({"id": job.get("company_id")})
    job["company"] = _clean(company) if company else None
    return job


# ──────────────────────────────────────────────
# Seed Data (skipped if DB already has data)
# ──────────────────────────────────────────────
def _seed():
    if col_companies.count_documents({}) > 0:
        print("MongoDB already seeded — skipping.")
        return

    print("Seeding MongoDB with initial data...")
    c1, c2, c3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    now = datetime.utcnow()

    col_companies.insert_many([
        {"id": c1, "name": "TechNova Solutions",  "industry": "Software Development",
         "website": "https://technova.io",   "logo_url": "https://placehold.co/100x100?text=TN",
         "description": "Building next-gen cloud platforms for enterprises.",
         "location": "Bangalore, India",  "created_at": now, "total_jobs_posted": 2},
        {"id": c2, "name": "FinEdge Capital",      "industry": "Finance & Fintech",
         "website": "https://finedge.in",    "logo_url": "https://placehold.co/100x100?text=FE",
         "description": "Democratizing investment for retail investors.",
         "location": "Mumbai, India",     "created_at": now, "total_jobs_posted": 1},
        {"id": c3, "name": "DesignPulse Agency",   "industry": "Design & Creative",
         "website": "https://designpulse.co","logo_url": "https://placehold.co/100x100?text=DP",
         "description": "Award-winning UI/UX agency.",
         "location": "Hyderabad, India",  "created_at": now, "total_jobs_posted": 1},
    ])

    seeds = [
        {"title": "Backend Engineering Intern", "company_id": c1,
         "category": "Technology", "job_type": "Internship",
         "experience_level": "Internship / No Experience",
         "location": "Bangalore, India", "is_remote": True,
         "description": "Join our core backend team and build production-grade REST APIs using Python and FastAPI.",
         "responsibilities": ["Develop REST APIs using FastAPI", "Write unit tests", "Participate in standups"],
         "requirements": ["Pursuing B.Tech/BE in CS", "Proficiency in Python", "Understands HTTP/REST"],
         "nice_to_have": ["Docker experience", "Open-source contributions"],
         "salary_min": 15000, "salary_max": 25000, "salary_currency": "INR",
         "application_deadline": "2025-09-30", "openings": 3,
         "tags": ["python", "fastapi", "backend", "intern"]},
        {"title": "Full Stack Developer", "company_id": c1,
         "category": "Technology", "job_type": "Full-Time",
         "experience_level": "Mid Level",
         "location": "Bangalore, India", "is_remote": False,
         "description": "We're looking for a Full Stack Developer to join our product team.",
         "responsibilities": ["Ship product features", "Collaborate with designers", "Mentor junior engineers"],
         "requirements": ["2+ years experience", "React + Node.js or Python", "PostgreSQL experience"],
         "nice_to_have": ["AWS/GCP experience", "TypeScript"],
         "salary_min": 800000, "salary_max": 1400000, "salary_currency": "INR",
         "application_deadline": "2025-10-15", "openings": 2,
         "tags": ["react", "nodejs", "fullstack", "postgres"]},
        {"title": "Finance & Investment Intern", "company_id": c2,
         "category": "Finance", "job_type": "Internship",
         "experience_level": "Internship / No Experience",
         "location": "Mumbai, India", "is_remote": False,
         "description": "Get real-world exposure to equity research and financial modelling.",
         "responsibilities": ["Equity research", "Build financial models", "Prepare investment memos"],
         "requirements": ["MBA (Finance) or B.Com final year", "Strong Excel skills"],
         "nice_to_have": ["CFA Level 1", "Bloomberg Terminal"],
         "salary_min": 20000, "salary_max": 30000, "salary_currency": "INR",
         "application_deadline": "2025-09-20", "openings": 2,
         "tags": ["finance", "equity", "excel", "intern"]},
        {"title": "UI/UX Design Intern", "company_id": c3,
         "category": "Design", "job_type": "Internship",
         "experience_level": "Internship / No Experience",
         "location": "Hyderabad, India", "is_remote": True,
         "description": "Work alongside senior designers on real client projects.",
         "responsibilities": ["Create wireframes and prototypes", "User research", "Dev handoff"],
         "requirements": ["Degree in Design/HCI", "Proficient in Figma", "Portfolio required"],
         "nice_to_have": ["Motion design", "Design systems experience"],
         "salary_min": 12000, "salary_max": 18000, "salary_currency": "INR",
         "application_deadline": "2025-10-01", "openings": 1,
         "tags": ["figma", "ux", "ui", "design", "intern"]},
    ]

    for s in seeds:
        col_jobs.insert_one({
            **s, "id": str(uuid.uuid4()),
            "is_active": True, "views": 0, "applications_count": 0,
            "created_at": now, "updated_at": now,
        })
    print(f"Seeded 3 companies and {len(seeds)} jobs.")


_seed()


# ══════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════

@app.get("/", tags=["General"], summary="Health Check")
def root():
    return {
        "status": "CareerNest API running (MongoDB)",
        "total_companies":    col_companies.count_documents({}),
        "total_jobs":         col_jobs.count_documents({}),
        "active_jobs":        col_jobs.count_documents({"is_active": True}),
        "total_applications": col_applications.count_documents({}),
        "docs": "/docs",
    }


# ── Companies ─────────────────────────────────
@app.post("/companies", tags=["Companies"], status_code=201)
def create_company(data: CompanyCreate):
    cid = str(uuid.uuid4())
    doc = {**data.model_dump(), "id": cid,
           "created_at": datetime.utcnow(), "total_jobs_posted": 0}
    col_companies.insert_one(doc)
    return _clean(doc)


@app.get("/companies", tags=["Companies"])
def list_companies():
    return {"companies": [_clean(c) for c in col_companies.find()],
            "total": col_companies.count_documents({})}


@app.get("/companies/{company_id}", tags=["Companies"])
def get_company(company_id: str):
    c = col_companies.find_one({"id": company_id})
    if not c:
        raise HTTPException(404, "Company not found")
    jobs = [_clean(j) for j in col_jobs.find({"company_id": company_id, "is_active": True})]
    return {"company": _clean(c), "active_jobs": jobs, "active_jobs_count": len(jobs)}


# ── Jobs ──────────────────────────────────────
@app.post("/jobs", tags=["Jobs"], status_code=201)
def create_job(data: JobCreate):
    if not col_companies.find_one({"id": data.company_id}):
        raise HTTPException(404, "Company not found. Create the company first.")
    jid = str(uuid.uuid4())
    now = datetime.utcnow()
    doc = {
        **data.model_dump(),
        "application_deadline": str(data.application_deadline) if data.application_deadline else None,
        "id": jid, "is_active": True, "views": 0, "applications_count": 0,
        "created_at": now, "updated_at": now,
    }
    col_jobs.insert_one(doc)
    col_companies.update_one({"id": data.company_id}, {"$inc": {"total_jobs_posted": 1}})
    return {"message": "Job posted successfully", "job": _enrich_job(doc)}


@app.get("/jobs", tags=["Jobs"])
def list_jobs(
    search:           Optional[str]  = Query(None),
    category:         Optional[str]  = Query(None),
    job_type:         Optional[str]  = Query(None),
    experience_level: Optional[str]  = Query(None),
    location:         Optional[str]  = Query(None),
    is_remote:        Optional[bool] = Query(None),
    salary_min:       Optional[int]  = Query(None),
    active_only:      bool           = Query(True),
    sort_by:          str            = Query("newest"),
    page:             int            = Query(1, ge=1),
    page_size:        int            = Query(10, ge=1, le=50),
):
    q: dict = {}
    if active_only:        q["is_active"]        = True
    if search:             q["$or"] = [
        {"title":       {"$regex": search.strip(), "$options": "i"}},
        {"description": {"$regex": search.strip(), "$options": "i"}},
        {"tags":        {"$elemMatch": {"$regex": search.strip(), "$options": "i"}}},
    ]
    if category:           q["category"]         = {"$regex": category.strip(),         "$options": "i"}
    if job_type:           q["job_type"]          = {"$regex": job_type.strip(),          "$options": "i"}
    if experience_level:   q["experience_level"]  = {"$regex": experience_level.strip(),  "$options": "i"}
    if location:           q["location"]          = {"$regex": location.strip(),           "$options": "i"}
    if is_remote is not None: q["is_remote"]      = is_remote
    if salary_min is not None: q["salary_max"]    = {"$gte": salary_min}

    sort_map = {
        "newest":       [("created_at",        DESCENDING)],
        "oldest":       [("created_at",        ASCENDING)],
        "salary_high":  [("salary_max",        DESCENDING)],
        "salary_low":   [("salary_min",        ASCENDING)],
        "most_applied": [("applications_count", DESCENDING)],
    }
    sort_order = sort_map.get(sort_by, [("created_at", DESCENDING)])

    total  = col_jobs.count_documents(q)
    skip   = (page - 1) * page_size
    jobs   = [_enrich_job(j) for j in col_jobs.find(q).sort(sort_order).skip(skip).limit(page_size)]

    return {
        "jobs": jobs,
        "pagination": {
            "total":       total, "page": page, "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@app.get("/jobs/{job_id}", tags=["Jobs"])
def get_job(job_id: str):
    job = col_jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(404, "Job not found")
    col_jobs.update_one({"id": job_id}, {"$inc": {"views": 1}})
    job["views"] = job.get("views", 0) + 1
    return _enrich_job(job)


@app.patch("/jobs/{job_id}", tags=["Jobs"])
def update_job(job_id: str, data: JobUpdate):
    if not col_jobs.find_one({"id": job_id}):
        raise HTTPException(404, "Job not found")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.utcnow()
    col_jobs.update_one({"id": job_id}, {"$set": updates})
    return {"message": "Job updated", "job": _enrich_job(col_jobs.find_one({"id": job_id}))}


@app.delete("/jobs/{job_id}", tags=["Jobs"])
def delete_job(job_id: str):
    if col_jobs.delete_one({"id": job_id}).deleted_count == 0:
        raise HTTPException(404, "Job not found")
    return {"message": "Job deleted successfully"}


# ── Application core logic ─────────────────────
def _submit_application(job_id: str, data: ApplicationCreate) -> dict:
    job = col_jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.get("is_active", True):
        raise HTTPException(400, "This job listing is no longer active")

    # Optional Google token verification
    if data.google_access_token:
        try:
            resp = requests.get(
                "https://www.googleapis.com/oauth2/v3/tokeninfo",
                params={"access_token": data.google_access_token},
                timeout=5,
            )
            if resp.status_code != 200:
                raise HTTPException(401, "Invalid Google authentication token.")
            if resp.json().get("email") != data.applicant_email:
                raise HTTPException(403, "Email mismatch with Google account.")
        except HTTPException:
            raise
        except Exception:
            pass  # Don't block apply if Google API is unreachable

    # Duplicate check
    if col_applications.find_one({"job_id": job_id, "applicant_email": data.applicant_email}):
        raise HTTPException(409, "You have already applied for this job")

    company = col_companies.find_one({"id": job.get("company_id")})
    now     = datetime.utcnow()
    app_doc = {
        **data.model_dump(),
        "id":           str(uuid.uuid4()),
        "job_id":       job_id,
        "job_title":    job["title"],
        "company_name": company.get("name", "Unknown") if company else "Unknown",
        "status":       ApplicationStatus.pending,
        "applied_at":   now,
        "updated_at":   now,
        "notes":        None,
    }
    col_applications.insert_one(app_doc)
    col_jobs.update_one({"id": job_id}, {"$inc": {"applications_count": 1}})
    return _clean(app_doc)


# ── Applications ──────────────────────────────
@app.post("/jobs/{job_id}/apply", tags=["Applications"], status_code=201)
def apply_for_job(job_id: str, data: ApplicationCreate):
    app_doc = _submit_application(job_id, data)
    return {"message": "Application submitted successfully!",
            "application_id": app_doc["id"], "application": app_doc}


@app.post("/applications", tags=["Applications"], status_code=201,
          summary="Apply for a job (frontend compat)")
def apply_for_job_compat(data: ApplicationCreateCompat):
    """Frontend sends this shape; we map it to the canonical model."""
    mapped = ApplicationCreate(
        applicant_name=      data.full_name,
        applicant_email=     str(data.email),
        google_access_token= data.google_access_token,
        phone=               data.phone,
        resume_url=          data.resume_url,
        cover_letter=        data.cover_letter,
        linkedin_url=        data.linkedin_url,
        portfolio_url=       data.portfolio_url,
        years_of_experience= data.years_experience,
        current_institution= data.institution,
        graduation_year=     data.graduation_year,
    )
    app_doc = _submit_application(data.job_id, mapped)
    return {"message": "Application submitted successfully!",
            "application_id": app_doc["id"], "application": app_doc}


@app.get("/jobs/{job_id}/applications", tags=["Applications"])
def get_job_applications(job_id: str, status: Optional[ApplicationStatus] = Query(None)):
    if not col_jobs.find_one({"id": job_id}):
        raise HTTPException(404, "Job not found")
    q: dict = {"job_id": job_id}
    if status:
        q["status"] = status
    apps = [_clean(a) for a in col_applications.find(q)]
    return {"applications": apps, "total": len(apps)}


@app.get("/applications/{application_id}", tags=["Applications"])
def get_application(application_id: str):
    a = col_applications.find_one({"id": application_id})
    if not a:
        raise HTTPException(404, "Application not found")
    return _clean(a)


@app.patch("/applications/{application_id}/status", tags=["Applications"])
def update_application_status(application_id: str, data: ApplicationStatusUpdate):
    if not col_applications.find_one({"id": application_id}):
        raise HTTPException(404, "Application not found")
    updates = {"status": data.status, "updated_at": datetime.utcnow()}
    if data.notes:
        updates["notes"] = data.notes
    col_applications.update_one({"id": application_id}, {"$set": updates})
    return {"message": f"Status updated to '{data.status}'",
            "application": _clean(col_applications.find_one({"id": application_id}))}


@app.get("/students/{email}/applications", tags=["Applications"],
         summary="Get all applications by a student email")
def get_student_applications(email: str):
    apps = [_clean(a) for a in col_applications.find({"applicant_email": email})]
    return {"applications": apps, "total": len(apps),
            "message": None if apps else "No applications found for this email"}


# ── Bookmarks ─────────────────────────────────
@app.post("/bookmarks", tags=["Bookmarks"], status_code=201)
def bookmark_job(data: BookmarkCreate):
    if not col_jobs.find_one({"id": data.job_id}):
        raise HTTPException(404, "Job not found")
    if col_bookmarks.find_one({"student_email": data.student_email, "job_id": data.job_id}):
        raise HTTPException(409, "Job already bookmarked")
    col_bookmarks.insert_one({
        "student_email": data.student_email,
        "job_id":        data.job_id,
        "saved_at":      datetime.utcnow(),
    })
    return {"message": "Job bookmarked successfully"}


@app.delete("/bookmarks", tags=["Bookmarks"])
def remove_bookmark(data: BookmarkCreate):
    if col_bookmarks.delete_one(
        {"student_email": data.student_email, "job_id": data.job_id}
    ).deleted_count == 0:
        raise HTTPException(404, "Bookmark not found")
    return {"message": "Bookmark removed"}


@app.get("/students/{email}/bookmarks", tags=["Bookmarks"])
def get_bookmarks(email: str):
    jobs = []
    for bm in col_bookmarks.find({"student_email": email}):
        job = col_jobs.find_one({"id": bm["job_id"]})
        if job:
            jobs.append(_enrich_job(job))
    return {"bookmarks": jobs, "total": len(jobs)}


# ── Stats ─────────────────────────────────────
@app.get("/stats", tags=["Dashboard"])
def get_stats():
    jobs = list(col_jobs.find())
    apps = list(col_applications.find())

    cat_breakdown: dict = {}
    type_breakdown: dict = {}
    for j in jobs:
        cat  = j.get("category", "Other")
        cat_breakdown[cat]            = cat_breakdown.get(cat, 0) + 1
        jt   = j.get("job_type", "Other")
        type_breakdown[jt]            = type_breakdown.get(jt, 0) + 1

    status_breakdown: dict = {}
    for a in apps:
        st = str(a.get("status", "Pending"))
        status_breakdown[st] = status_breakdown.get(st, 0) + 1

    return {
        "overview": {
            "total_companies":    col_companies.count_documents({}),
            "total_jobs":         len(jobs),
            "active_jobs":        col_jobs.count_documents({"is_active": True}),
            "total_applications": len(apps),
            "total_bookmarks":    col_bookmarks.count_documents({}),
        },
        "jobs_by_category":       cat_breakdown,
        "jobs_by_type":           type_breakdown,
        "applications_by_status": status_breakdown,
        "most_viewed_jobs":  [_clean(j) for j in sorted(jobs, key=lambda x: x.get("views", 0), reverse=True)[:5]],
        "most_applied_jobs": [_clean(j) for j in sorted(jobs, key=lambda x: x.get("applications_count", 0), reverse=True)[:5]],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)