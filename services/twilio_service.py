"""
Twilio Service - WhatsApp messaging utilities
Handles sending proactive messages to customers
"""
from twilio.rest import Client


async def send_whatsapp_message(
    twilio_client: Client,
    to_number: str,
    from_number: str,
    message: str,
    media_url: str = None
) -> bool:
    """
    Send WhatsApp message via Twilio
    
    Args:
        twilio_client: Initialized Twilio client
        to_number: Recipient's WhatsApp number (whatsapp:+...)
        from_number: Your Twilio WhatsApp number (whatsapp:+...)
        message: Message text
        media_url: Optional media URL (PDF, image, etc.)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        message_params = {
            'from_': from_number,
            'to': to_number,
            'body': message
        }
        
        # Add media if provided
        if media_url:
            message_params['media_url'] = [media_url]
        
        response = twilio_client.messages.create(**message_params)
        
        print(f"✅ Message sent to {to_number}: {response.sid}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send message to {to_number}: {e}")
        return False


async def send_invoice_message(
    twilio_client: Client,
    to_number: str,
    from_number: str,
    customer_name: str,
    product_name: str,
    amount: float,
    invoice_url: str = None
) -> bool:
    """
    Send invoice notification with optional PDF attachment
    """
    message = f"✅ فاتورتك جاهزة يا {customer_name}!\n\n"
    message += f"📦 المنتج: {product_name}\n"
    message += f"💰 المبلغ: {amount} دينار\n\n"
    message += "شكراً لتعاملك معنا! 🙏"
    
    return await send_whatsapp_message(
        twilio_client=twilio_client,
        to_number=to_number,
        from_number=from_number,
        message=message,
        media_url=invoice_url
    )
