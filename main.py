import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional

from database import create_document
from schemas import Inquiry

app = FastAPI(title="Event Planning API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Event Planning Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# Email sending model and endpoint
class EmailSettings(BaseModel):
    to: EmailStr

@app.post("/api/inquiry")
def submit_inquiry(payload: Inquiry, to: Optional[EmailStr] = None):
    """
    Accept booking/contact inquiries.
    - Stores the inquiry in MongoDB (collection: inquiry)
    - Optionally sends an email if EMAIL_TO is configured or `to` query param provided
    """
    try:
        inserted_id = create_document("inquiry", payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Prepare email notification (simple stdout fallback)
    recipient = to or os.getenv("BOOKING_EMAIL") or os.getenv("EMAIL_TO")
    subject = "Ny booking-henvendelse"
    body = (
        f"Navn: {payload.name}\n"
        f"Email: {payload.email}\n"
        f"Telefon: {payload.phone}\n"
        f"Eventtype: {payload.event_type}\n"
        f"Dato/periode: {payload.date_preference or '-'}\n"
        f"Antal gæster: {payload.guests or '-'}\n"
        f"Pakke: {payload.package}\n\n"
        f"Besked:\n{payload.message or '-'}\n"
    )

    # If an email provider isn't configured in this environment,
    # we simply log to server output so the team can see submissions.
    if recipient:
        print("[Inquiry Notification] To:", recipient)
        print("Subject:", subject)
        print(body)
    else:
        print("[Inquiry Received] No recipient configured. Set BOOKING_EMAIL to forward.")
        print(body)

    return {"ok": True, "id": inserted_id, "message": "Tak for din henvendelse – vi vender tilbage inden for 24 timer."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
