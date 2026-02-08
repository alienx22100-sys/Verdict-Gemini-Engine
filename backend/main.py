"""
Decision Authority - FastAPI Main Application.
Deterministic Intelligence Engine powered by Gemini 3.

SECURITY NOTES:
- Rate limiting: 10 requests/minute per IP
- Input validation: 10-2000 chars, sanitized
- Error handling: Stack traces hidden in production
- CORS: Wildcard for hackathon demo (restrict in production)
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os
import traceback

from config import Config
from models import (
    DecisionInput,
    DecisionResponse,
    GatekeeperResponse,
    HealthResponse,
    CompleteDecision,
    BiasLevel
)
from gatekeeper import gatekeeper
from sensors import sensor_council
from extractor import extractor
from decision_core import decision_core
from optimizer import optimizer
from bias_detector import bias_detector
from models import DecisionVerdict

# SECURITY: Import security modules
from security import validate_input, sanitize_input
from rate_limiter import api_rate_limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("=" * 60)
    print("🔷 DECISION AUTHORITY")
    print("   Deterministic Intelligence Engine")
    print("   v3.3 - Security Hardened")
    print("=" * 60)
    
    print(f"✅ Gemini API configured (key: {Config.get_masked_key()})")
    print(f"🔒 Debug mode: {'ON' if Config.DEBUG_MODE else 'OFF'}")
    print(f"🚀 Server running on http://localhost:{Config.API_PORT}")
    print("=" * 60)
    
    yield
    
    print("\n🛑 Decision Authority shutting down...")


# Initialize FastAPI
app = FastAPI(
    title="Decision Authority",
    description="Deterministic Intelligence Engine powered by Gemini 3",
    version="1.0.0",
    lifespan=lifespan
)

# ─────────────────────────────────────────────────────────────
# SECURITY: CORS Configuration
# NOTE: Wildcard (*) is used for hackathon demo accessibility.
# In production, replace with specific allowed origins.
# ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# SECURITY: Global Exception Handler
# Hides stack traces from clients in production mode
# ─────────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    SECURITY: Never expose internal details to clients in production.
    """
    # Always log full error server-side
    print(f"❌ Unhandled exception: {exc}")
    if Config.DEBUG_MODE:
        traceback.print_exc()
    
    # Return sanitized error to client
    if Config.DEBUG_MODE:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "type": type(exc).__name__}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred. Please try again."}
        )


# ─────────────────────────────────────────────────────────────
# HELPER: Get client IP for rate limiting
# ─────────────────────────────────────────────────────────────
def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─────────────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="operational",
        gemini_configured=bool(Config.GEMINI_API_KEY),
        version="1.0.0"
    )


@app.post("/api/gatekeeper", response_model=GatekeeperResponse)
async def process_gatekeeper(input_data: DecisionInput, request: Request):
    """
    Step 1: Input Gatekeeper
    Extracts decision fields from user input.
    Returns incomplete status if fields are missing.
    """
    # SECURITY: Rate limiting
    client_ip = get_client_ip(request)
    allowed, retry_after = api_rate_limiter.check(client_ip)
    if not allowed:
        return GatekeeperResponse(
            success=False, 
            error=f"Too many requests. Please wait {retry_after} seconds."
        )
    
    try:
        # SECURITY: Sanitize input before processing
        sanitized_message = sanitize_input(input_data.message)
        
        result = await gatekeeper.extract_decision_object(sanitized_message)
        return GatekeeperResponse(success=True, data=result)
    except ValueError as e:
        return GatekeeperResponse(success=False, error=str(e))
    except Exception as e:
        # SECURITY: Log full error, return generic message
        print(f"❌ Gatekeeper error: {e}")
        if Config.DEBUG_MODE:
            return GatekeeperResponse(success=False, error=f"Gatekeeper failed: {str(e)}")
        return GatekeeperResponse(success=False, error="Failed to process input. Please try again.")


@app.post("/api/decide", response_model=DecisionResponse)
async def make_decision(input_data: DecisionInput, request: Request):
    """
    Full Decision Pipeline:
    1. Input Gatekeeper → Extract decision object
    2. Sensor Council → Run 4 Gemini sensors
    3. Extractor → Extract signals
    4. Decision Core → Deterministic verdict
    5. Return Decision Card
    
    SECURITY: Rate limited, input sanitized, errors hidden in production.
    """
    # ─────────────────────────────────────────────────────────
    # SECURITY: Rate limiting per IP
    # ─────────────────────────────────────────────────────────
    client_ip = get_client_ip(request)
    allowed, retry_after = api_rate_limiter.check(client_ip)
    if not allowed:
        print(f"⚠️ Rate limit exceeded for {client_ip}")
        return DecisionResponse(
            success=False,
            error=f"Too many requests. Please wait {retry_after} seconds before trying again."
        )
    
    # ─────────────────────────────────────────────────────────
    # SECURITY: Validate and sanitize input
    # ─────────────────────────────────────────────────────────
    is_valid, validation_error = validate_input(input_data.message)
    if not is_valid:
        return DecisionResponse(success=False, error=validation_error)
    
    sanitized_message = sanitize_input(input_data.message)
    
    try:
        # Step 0: Bias Detection - Analyze for emotional charge
        print("🔍 [0/3] Checking for emotional bias...")
        bias_analysis = await bias_detector.analyze(sanitized_message)
        
        # If HIGH bias, reject the input
        if bias_analysis.bias_level == BiasLevel.HIGH:
            print(f"❌ Input rejected: Emotional bias score {bias_analysis.bias_score}%")
            return DecisionResponse(
                success=False,
                bias_analysis=bias_analysis,
                bias_rejected=True,
                error=f"Input too emotional (Score: {bias_analysis.bias_score}%). Please rephrase objectively."
            )
        
        # MEDIUM bias: proceed with warning attached
        if bias_analysis.bias_level == BiasLevel.MEDIUM:
            print(f"⚠️ Bias warning: Score {bias_analysis.bias_score}% - proceeding with caution")
        
        # Rate limit delay after bias check
        import asyncio
        await asyncio.sleep(1.5)
        
        # Step 1: Gatekeeper - Extract decision object
        print("🤖 [1/3] Calling Gatekeeper...")
        gatekeeper_result = await gatekeeper.extract_decision_object(sanitized_message)
        
        # If incomplete, return the question for missing field
        if not gatekeeper_result.complete:
            print("❌ Gatekeeper incomplete.")
            return DecisionResponse(
                success=False,
                bias_analysis=bias_analysis,
                error=f"Incomplete decision: {gatekeeper_result.question}"
            )
        
        # We have a complete decision object
        decision_object = gatekeeper_result.decision_object
        print("✅ Gatekeeper passed. Waiting 2s to avoid Rate Limit...")
        
        # SAFETY DELAY: Wait 2 seconds between calls to avoid burst limit
        await asyncio.sleep(2.0)
        
        # Step 2: Sensor Council - Run all 4 sensors
        print("🤖 [2/3] Calling Sensor Council...")
        sensors = await sensor_council.analyze(decision_object)
        
        # Step 3: Extractor - Extract signals
        extracted = extractor.extract(sensors)
        
        # Step 4: Decision Core - Deterministic verdict
        decision_card = decision_core.decide(extracted)
        
        # Step 5: Strategic Optimizer (only for non-APPROVED decisions)
        optimizer_suggestions = None
        if decision_card.verdict != DecisionVerdict.APPROVED:
            print("🔧 [3/3] Calling Strategic Optimizer...")
            await asyncio.sleep(1.5)  # Rate limit protection
            optimizer_suggestions = await optimizer.optimize(
                decision_object,
                sensors,
                decision_card.verdict,
                decision_card.blocking_reason
            )
        
        print("✅ Decision complete.")
        return DecisionResponse(
            success=True,
            decision_card=decision_card,
            sensors=sensors,
            decision_object=decision_object,
            optimizer_suggestions=optimizer_suggestions,
            bias_analysis=bias_analysis
        )
        
    except ValueError as e:
        print(f"❌ ValueError: {e}")
        return DecisionResponse(success=False, error=str(e))
    except Exception as e:
        # SECURITY: Log full error server-side, return generic message to client
        print(f"❌ Exception in make_decision: {e}")
        if Config.DEBUG_MODE:
            traceback.print_exc()
            return DecisionResponse(success=False, error=f"Decision failed: {str(e)}")
        return DecisionResponse(success=False, error="Analysis failed. Please try again.")


# ─────────────────────────────────────────────────────────────
# STATIC FILES (Frontend)
# ─────────────────────────────────────────────────────────────

# Get the frontend directory path
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Mount static files if frontend exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the frontend application."""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=True
    )
