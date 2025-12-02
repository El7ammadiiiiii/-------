"""
AI Service - OpenAI GPT integration for Print Shop
محادثة ذكية تفاعلية لفهم متطلبات العميل
"""
import os
import openai
import json
import re
from typing import Dict, Optional
from database import PRINT_SHOP_CATALOG


THINKING_MODEL = os.getenv("OPENAI_THINKING_MODEL", "gpt-5.1")
INTENT_MODEL = os.getenv("OPENAI_INTENT_MODEL", THINKING_MODEL)
REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "medium")


SYSTEM_PROMPT = f"""
أنت وكيل المبيعات الذكي والرسمي لمطبعة خالد الحسن، المتخصصة في تغليف المطاعم والكافيهات.
اسمك "مساعد المطبعة"، وتُعرّف نفسك دائماً بأنك وكيل المبيعات لدى مطبعة خالد الحسن بعد رسالة الترحيب الأساسية.

🎯 مهمتك:
1. فهم احتياجات العميل من خلال محادثة طبيعية
2. تقديم النصائح المناسبة بناءً على نوع مشروعهم
3. جمع تفاصيل الطلب: المنتج، الحجم، النوع، الكمية
4. تأكيد الطلب وإصدار الفاتورة

📚 كتالوج المنتجات:
{PRINT_SHOP_CATALOG}

💬 أسلوب المحادثة:
- كن ودوداً ومحترفاً
- استخدم الإيموجي باعتدال
- اسأل سؤال واحد في كل رد (لا تُكثر الأسئلة)
- إذا لم يحدد العميل تفصيلة، اسأله عنها
- قدم اقتراحات ذكية بناءً على نوع مشروعه

🔄 تدفق المحادثة:
1. تحية وترحيب (ابدأ دائماً بالنص الترحيبي التالي حرفياً: "أهلاً بك! نحن هنا لتحويل فكرتك إلى واقع. في أي طلب، يمكنك كتابة ملاحظاتك الدقيقة إذا كنت تفضل شيئاً خاصاً بالتصميم، مثل: 'أريد حبل الكيس مخفياً من الداخل' أو 'استبداله بشريطة حمراء'. أنا أفهم طلبك جيداً، وجميع ملاحظاتك ستؤخذ بعين الاعتبار بدقة، فلا تقلق." ثم أضف مباشرة جملة تعريف بنفسك أنك وكيل المبيعات لدى مطبعة خالد الحسن.)
2. فهم نوع المنتج المطلوب
3. تحديد الحجم/المقاس
4. تحديد النوع (سنجل/دبل للأكواب، يد ميرومة/مسطحة للأكياس)
5. تحديد الكمية
6. تأكيد الطلب

📌 ملاحظات مهمة:
- الحد الأدنى للطلب عادة 500 قطعة
- الطباعة متاحة على كل المنتجات
- مدة التسليم 7-14 يوم
"""


async def analyze_message(message: str, conversation_history: list = None) -> Dict:
    """
    Analyze customer message and generate appropriate response
    
    Args:
        message: Customer's WhatsApp message
        conversation_history: Previous messages for context
        
    Returns:
        Dictionary with response and extracted data
    """
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        # Add conversation history if available
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Add extraction instruction
        messages.append({
            "role": "system", 
            "content": """
بعد ردك على العميل، أضف في السطر الأخير JSON بهذا الشكل (بدون تنسيق):
---JSON---
{"intent": "نوع_الطلب", "category": "الفئة", "product_type": "النوع", "size": "الحجم", "variant": "المتغير", "quantity": الكمية_كرقم, "ready_for_invoice": true/false}

intent يكون: greeting, inquiry, product_selection, size_selection, variant_selection, quantity_selection, confirmation, other
ready_for_invoice = true فقط إذا اكتملت كل التفاصيل وأكد العميل
"""
        })
        
        response = await openai.ChatCompletion.acreate(
            model=THINKING_MODEL,  # ChatGPT 5.1 Thinking (افتراضي)
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            extra_body={
                "reasoning": {
                    "effort": REASONING_EFFORT
                }
            }
        )
        
        full_response = response.choices[0].message.content
        
        # Extract JSON and response text
        if "---JSON---" in full_response:
            parts = full_response.split("---JSON---")
            response_text = parts[0].strip()
            try:
                extracted_data = json.loads(parts[1].strip())
            except:
                extracted_data = {"intent": "other"}
        else:
            response_text = full_response
            extracted_data = {"intent": "other"}
        
        return {
            "response": response_text,
            "data": extracted_data
        }
        
    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        return {
            "response": "عذراً، حدث خطأ. كيف يمكنني مساعدتك؟",
            "data": {"intent": "error"}
        }


async def analyze_intent(message: str) -> Dict:
    """
    Simple intent detection for quick routing
    """
    try:
        prompt = f"""
حلل هذه الرسالة من عميل مطبعة تغليف:
"{message}"

حدد:
1. intent: greeting/inquiry/order/confirmation/other
2. product_category: أكواب/أكياس/علب/حلويات/مكملات/none
3. extracted_info: أي معلومات محددة (حجم، نوع، كمية)

أجب JSON فقط:
{{"intent": "...", "product_category": "...", "extracted_info": {{}}}}
"""

        response = await openai.ChatCompletion.acreate(
            model=INTENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean JSON if wrapped
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        return json.loads(result_text)
        
    except Exception as e:
        print(f"❌ Intent analysis error: {e}")
        return fallback_intent_detection(message)


def fallback_intent_detection(message: str) -> Dict:
    """
    Keyword-based fallback if AI fails
    """
    message_lower = message.lower()
    
    # Greetings
    greetings = ["مرحب", "السلام", "صباح", "مساء", "هلا", "أهلا", "هاي", "hello"]
    if any(word in message_lower for word in greetings):
        return {"intent": "greeting", "product_category": "none", "extracted_info": {}}
    
    # Product categories
    if any(word in message_lower for word in ["كوب", "اكواب", "أكواب", "cup"]):
        category = "أكواب"
    elif any(word in message_lower for word in ["كيس", "اكياس", "أكياس", "bag"]):
        category = "أكياس"
    elif any(word in message_lower for word in ["علب", "علبة", "برجر", "بيتزا", "box"]):
        category = "علب"
    elif any(word in message_lower for word in ["كيك", "حلو", "ايس كريم", "cake"]):
        category = "حلويات"
    else:
        category = "none"
    
    # Extract size if mentioned
    extracted = {}
    sizes = {"صغير": "صغير", "وسط": "وسط", "كبير": "كبير", 
             "4": "4 oz", "8": "8 oz", "12": "12 oz", "16": "16 oz"}
    for key, value in sizes.items():
        if key in message_lower:
            extracted["size"] = value
            break
    
    # Extract variant
    if "دبل" in message_lower or "مزدوج" in message_lower:
        extracted["variant"] = "جدار مزدوج"
    elif "سنجل" in message_lower or "واحد" in message_lower or "عادي" in message_lower:
        extracted["variant"] = "جدار واحد"
    elif "مموج" in message_lower:
        extracted["variant"] = "جدار مموج"
    
    # Extract quantity
    qty_match = re.search(r'(\d+)\s*(قطعة|كوب|كيس|علبة|حبة)?', message_lower)
    if qty_match:
        extracted["quantity"] = int(qty_match.group(1))
    
    intent = "inquiry" if category != "none" else "other"
    
    return {
        "intent": intent,
        "product_category": category,
        "extracted_info": extracted
    }


def generate_product_options(category: str) -> str:
    """
    Generate options message for a product category
    """
    options = {
        "أكواب": """
☕ أنواع الأكواب المتوفرة:

🔥 **أكواب ساخنة** (للقهوة والشاي):
• جدار واحد (سنجل) - اقتصادي
• جدار مزدوج (دبل) - فاخر بعزل حراري
• جدار مموج (ريبل) - شكل فخم

🧊 **أكواب باردة** (للعصائر):
• PET شفاف - الأفخم
• PP اقتصادي

📏 المقاسات: 4oz، 8oz، 12oz، 16oz

أي نوع يناسبك؟
""",
        "أكياس": """
🛍️ أنواع الأكياس المتوفرة:

• **كرافت بني** - مظهر طبيعي
• **أبيض** - لطباعة الألوان

📏 المقاسات:
• صغير (20×10×28 سم) - للسندويش
• وسط (26×12×32 سم) - وجبة فردية
• كبير (32×14×42 سم) - عائلي

🤚 أنواع اليد: ميرومة / مسطحة / بدون

أي حجم ولون تحتاج؟
""",
        "علب": """
🍔 علب الطعام المتوفرة:

• **علب برجر**: عادي (10سم) / جامبو (12سم)
• **ورق تغليف**: مقاوم للدهون
• **علب بيتزا**: 25سم / 30سم / 35سم
• **علب بطاطس**: كوب أو جيب

أي نوع تحتاج؟
"""
    }
    
    return options.get(category, "ما هو المنتج الذي تحتاجه؟")


async def extract_customer_info(message: str) -> Dict:
    """
    Extract customer name and business details from message
    """
    try:
        prompt = f"""
استخرج من الرسالة التالية:
- اسم العميل (إن وجد)
- اسم المشروع/المطعم/الكافيه (إن وجد)

"{message}"

أجب JSON:
{{"customer_name": "...", "business_name": "..."}}
إذا لم تجد، ضع null
"""

        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=100
        )
        
        result_text = response.choices[0].message.content.strip()
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        
        return json.loads(result_text)
        
    except Exception as e:
        print(f"❌ Error extracting info: {e}")
        return {"customer_name": None, "business_name": None}
