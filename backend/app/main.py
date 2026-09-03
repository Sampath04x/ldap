from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config import get_settings
from app.middleware.audit import AuditMiddleware
from app.api import health, search, users, firewalls, diagnostics

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Firewall Identity & LDAP Diagnostics",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    if settings.api_key:
        @app.middleware("http")
        async def api_key_middleware(request: Request, call_next):
            if request.url.path == "/api/v1/health" or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
                return await call_next(request)
            key = request.headers.get("X-API-Key", "")
            if key != settings.api_key:
                return JSONResponse({"error": {"code": "UNAUTHORIZED", "message": "Invalid or missing API key"}}, status_code=401)
            return await call_next(request)
    
    app.add_middleware(AuditMiddleware)
    
    prefix = "/api/v1"
    app.include_router(health.router, prefix=prefix, tags=["health"])
    app.include_router(search.router, prefix=prefix, tags=["search"])
    app.include_router(users.router, prefix=prefix, tags=["users"])
    app.include_router(firewalls.router, prefix=prefix, tags=["firewalls"])
    app.include_router(diagnostics.router, prefix=prefix, tags=["diagnostics"])
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(exc.detail, status_code=exc.status_code)
        return JSONResponse(
            {"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
            status_code=exc.status_code
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import logging, traceback
        logging.error(traceback.format_exc())
        return JSONResponse(
            {"error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred", "request_id": str(getattr(request.state, 'request_id', ''))}},
            status_code=500
        )
        
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "Invalid request", "details": exc.errors()}},
            status_code=422
        )
    
    return app

app = create_app()
