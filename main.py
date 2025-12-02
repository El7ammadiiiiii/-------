"""
SmartSalesAgent - FastAPI WhatsApp Sales Bot for Print Shop
خادم المحادثة الذكي للمطبعة
"""
import os
from fastapi import FastAPI, Form, BackgroundTasks
try:
    from twilio.rest import Client
except ImportError:  # pragma: no cover
    Client = None
    def _missing_twilio_client(*args, **kwargs):
        raise RuntimeError("twilio is not installed. Install it via 'pip install twilio'.")
    print("⚠️ twilio package is not installed. WhatsApp messaging will be simulated.")
import openai
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        """Fallback placeholder when python-dotenv is missing."""
        print("⚠️ python-dotenv is not installed. Environment variables from .env will not be loaded.")
from database import SessionLocal, init_db, PRINT_SHOP_CATALOG, ConversationState
from services.ai_service import analyze_message, analyze_intent, fallback_intent_detection
from services.conversation_service import ConversationManager
from services.invoice_service import create_invoice
from services.twilio_service import send_whatsapp_message
from services.order_service import create_order_from_state

# Load environment variables
load_dotenv()

# Initialize OpenAI and Twilio clients
openai.api_key = os.getenv("OPENAI_API_KEY")

# Twilio client (initialize only if credentials exist)
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
BOT_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

twilio_client = None
if TWILIO_SID and TWILIO_TOKEN:
    try:
        twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
    except Exception as e:
        print(f"⚠️ Twilio initialization failed: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="Smart Sales Agent - Print Shop",
    description="مساعد مبيعات ذكي لمطبعة تغليف المطاعم والكافيهات",
    version="2.0.0"
)


async def process_message_task(incoming_msg: str, sender_phone: str):
    """
    Background task to process customer messages
    Uses conversation state to track progress
    """
    db = SessionLocal()
    
    try:
        # Initialize conversation manager
        conv_manager = ConversationManager(db)
        
        # Get or create conversation state
        state = conv_manager.get_or_create_state(sender_phone)
        
        # Check for reset commands
        if incoming_msg.strip().lower() in ["إلغاء", "cancel", "بداية", "start", "من جديد"]:
            conv_manager.reset_state(sender_phone)
            response_text = conv_manager.generate_step_message(state)
            await send_response(sender_phone, response_text)
            return
        
        # Special handling when we are at confirmation step and user replies textually
        if state.current_step == "confirm":
            normalized = incoming_msg.strip().lower()
            if normalized in ["موافق", "ok", "نعم", "تمام"]:
                order = create_order_from_state(db, state)
                response_text = (
                    "تم استلام طلبك.\n"
                    "بحال توفر طلبك وموافقة الادارة على التنفيذ راح أعطيك تفاصيل الدفع بأقرب وقت."
                )
                await send_response(sender_phone, response_text)
                return
            elif normalized in ["تعديل", "edit"]:
                # send user back to quantity step for now
                conv_manager.update_state(sender_phone, current_step="quantity")
                response_text = conv_manager.generate_step_message(state)
                await send_response(sender_phone, response_text)
                return
            elif normalized in ["إلغاء", "الغاء", "cancel"]:
                conv_manager.reset_state(sender_phone)
                response_text = "تم إلغاء الطلب الحالي. متى ما حبيت نبدأ من جديد أنا جاهز."
                await send_response(sender_phone, response_text)
                return

        # Analyze message with AI
        result = await analyze_message(
            message=incoming_msg,
            conversation_history=None  # TODO: Load history from ChatLog
        )
        
        response_text = result.get("response", "")
        extracted_data = result.get("data", {})
        
        # Update state based on extracted data
        if extracted_data.get("category"):
            # Find category ID
            from database import ProductCategory
            cat = db.query(ProductCategory).filter(
                ProductCategory.name.like(f"%{extracted_data['category']}%")
            ).first()
            if cat:
                conv_manager.update_state(sender_phone, 
                    selected_category_id=cat.id,
                    current_step="type"
                )
        
        if extracted_data.get("quantity"):
            conv_manager.update_state(sender_phone,
                selected_quantity=extracted_data["quantity"],
                current_step="confirm"
            )
        
        if extracted_data.get("ready_for_invoice"):
            # Generate invoice
            order_summary = conv_manager.get_order_summary(state)
            
            if order_summary.get("variant") and state.selected_quantity:
                invoice_path = await create_invoice(
                    customer_name=state.customer_name or "عميل",
                    customer_phone=sender_phone,
                    product_name=order_summary["variant"]["name"],
                    price=0,  # TODO: Calculate from pricing tiers
                    db=db
                )
                
                response_text = f"""
✅ تم إصدار الفاتورة!

📋 تفاصيل الطلب:
📦 {order_summary["variant"]["name"]}
🔢 الكمية: {state.selected_quantity}

سيتم التواصل معك لتأكيد الطلب والتسليم.
شكراً لتعاملك معنا! 🙏
"""
                # Reset for new order
                conv_manager.reset_state(sender_phone)
        
        # If no AI response, generate based on current step
        if not response_text:
            response_text = conv_manager.generate_step_message(state)
        
        # Send response
        await send_response(sender_phone, response_text)
        
        # Log the interaction
        from database import ChatLog
        log = ChatLog(
            phone_number=sender_phone,
            message_type="incoming",
            message_content=incoming_msg,
            intent=extracted_data.get("intent")
        )
        db.add(log)
        
        out_log = ChatLog(
            phone_number=sender_phone,
            message_type="outgoing",
            message_content=response_text
        )
        db.add(out_log)
        db.commit()
        
        print(f"✅ Processed message for {sender_phone}")
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        import traceback
        traceback.print_exc()
        
        # Send error message
        error_msg = """
عذراً، حدث خطأ. 😅

يمكنك:
• كتابة "بداية" للبدء من جديد
• أو اكتب ما تحتاجه وسأحاول مساعدتك
"""
        await send_response(sender_phone, error_msg)
    
    finally:
        db.close()


async def send_response(to_number: str, message: str):
    """Send WhatsApp response"""
    if twilio_client and BOT_NUMBER:
        await send_whatsapp_message(
            twilio_client=twilio_client,
            to_number=to_number,
            from_number=BOT_NUMBER,
            message=message
        )
    else:
        print(f"📤 [SIMULATED] To {to_number}:\n{message}")


@app.post("/bot")
async def bot_endpoint(
    background_tasks: BackgroundTasks,
    Body: str = Form(...),
    From: str = Form(...)
):
    """
    Twilio webhook endpoint for incoming WhatsApp messages
    Returns immediately to avoid timeout, processes message in background
    """
    print(f"📥 Message from {From}: {Body}")
    
    # Add message processing to background queue
    background_tasks.add_task(process_message_task, Body, From)
    
    # Return immediately to Twilio (acknowledgment)
    return {"status": "received", "message": "Processing your request"}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Smart Sales Agent - Print Shop",
        "version": "2.0.0",
        "catalog": "مطبعة تغليف المطاعم والكافيهات"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "twilio": "configured" if twilio_client else "not configured",
        "openai": "configured" if openai.api_key else "not configured"
    }


@app.get("/catalog")
async def get_catalog():
    """Return product catalog"""
    return {
        "catalog": PRINT_SHOP_CATALOG
    }


@app.get("/test/{message}")
async def test_message(message: str):
    """Test endpoint to simulate a message (for development)"""
    test_phone = "whatsapp:+1234567890"
    
    db = SessionLocal()
    try:
        conv_manager = ConversationManager(db)
        state = conv_manager.get_or_create_state(test_phone)
        
        # Analyze with fallback (no OpenAI needed)
        intent_data = fallback_intent_detection(message)
        
        return {
            "message": message,
            "intent": intent_data,
            "current_state": {
                "step": state.current_step,
                "category_id": state.selected_category_id,
                "type_id": state.selected_type_id,
                "variant_id": state.selected_variant_id,
                "quantity": state.selected_quantity
            },
            "next_message": conv_manager.generate_step_message(state)
        }
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    print("🚀 Starting Smart Sales Agent - Print Shop...")
    init_db()
    print("✅ Database initialized with print shop catalog")
    print("✅ Server ready!")
    
    if not openai.api_key:
        print("⚠️ OpenAI API key not configured - using fallback intent detection")
    if not twilio_client:
        print("⚠️ Twilio not configured - responses will be simulated")


if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        raise RuntimeError("uvicorn is required to run this app. Install it via 'pip install uvicorn'.")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
