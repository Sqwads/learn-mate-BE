from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.modules.auth.router import router as auth_router
from app.modules.profiles.router import router as profiles_router
from app.modules.classes.router import router as classes_router
from app.modules.attendance.router import router as attendance_router
from app.modules.assignments.router import router as assignments_router
from app.modules.submissions.router import router as submissions_router
from app.modules.grades.router import router as grades_router
from app.modules.admin.router import router as admin_router
from app.modules.schools.router import router as schools_router
from app.modules.superuser.router import router as superuser_router

app = FastAPI(
    title="LearnMate Backend MVP",
    description="Education platform backend with role-based access control",
    version="1.0.0"
)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="LearnMate Backend MVP",
        version="1.0.0",
        description="Education platform backend with role-based access control",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
def root():
    return {"message": "Hello World from LearnMate!"}

# Leapcell health check endpoints (both spellings used by the proxy)
@app.get("/kaithheathcheck")
@app.get("/kaithhealthcheck")
def leapcell_health_check():
    return {"status": "ok"}

# Health check route
@app.get("/health")
def health_check():
    """Check if the service and database connection are healthy"""
    try:
        from app.db.supabase import supabase
        test_response = supabase.table('profiles').select('id').limit(1).execute()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2026-01-09T23:14:00Z"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": f"error: {str(e)}",
            "timestamp": "2026-01-09T23:14:00Z"
        }

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(profiles_router, prefix="/profiles", tags=["Profiles"])
app.include_router(classes_router, prefix="/classes", tags=["Classes"])
app.include_router(attendance_router, prefix="/attendance", tags=["Attendance"])
app.include_router(assignments_router, prefix="/assignments", tags=["Assignments"])
app.include_router(submissions_router, prefix="/submissions", tags=["Submissions"])
app.include_router(grades_router, prefix="/grades", tags=["Grades"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(schools_router, prefix="/schools", tags=["Schools"])
app.include_router(superuser_router, prefix="", tags=["Superuser"])