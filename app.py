
import telebot
import fitz 
from PIL import Image, ImageDraw, ImageFont
import io
import os
import arabic_reshaper
from bidi.algorithm import get_display

TOKEN = '8324075166:AAFWH3irxuS0uQMoFEM9PMQrGnHqsVdjCbk'

bot = telebot.TeleBot(TOKEN)
user_data = {}

FONT_FILE = "Amiri-Regular.ttf"

if not os.path.exists(FONT_FILE):
    print(f"Error: Font file '{FONT_FILE}' not found.")
    print("Please download an Arabic font like 'Amiri' and place it in the same directory.")
    exit()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك. أرسل ملف PDF ")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if message.document.mime_type == 'application/pdf':
        chat_id = message.chat.id
        user_data[chat_id] = {'file_id': message.document.file_id}
        bot.reply_to(message, "تم استلام ملف PDF. الآن أرسل النص ")
    else:
        bot.reply_to(message, "الرجاء إرسال ملف بصيغة PDF فقط.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    if chat_id in user_data and 'file_id' in user_data[chat_id]:
        file_id = user_data[chat_id]['file_id']
        text_to_add = message.text

        processing_message = None
        pdf_document = None
        output_pdf = None

        try:
            processing_message = bot.send_message(chat_id, "جاري معالجة الملف، يرجى الانتظار...")
            
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            pdf_document = fitz.open(stream=downloaded_file, filetype="pdf")
            output_pdf = fitz.open()

            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                draw = ImageDraw.Draw(img)
                
                font_size = int(img.width / 25)
                if font_size < 20:
                    font_size = 20
                
                font = ImageFont.truetype(FONT_FILE, font_size)

                reshaped_text = arabic_reshaper.reshape(text_to_add)
                bidi_text = get_display(reshaped_text)

                text_bbox = draw.textbbox((0, 0), bidi_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                x = (img.width - text_width) / 2
                y = img.height - text_height - (img.height * 0.05)

                shadow_offset = int(font_size * 0.05)
                shadow_color = (50, 50, 50)
                draw.text((x + shadow_offset, y + shadow_offset), bidi_text, font=font, fill=shadow_color)
                
                text_color = (255, 255, 255)
                draw.text((x, y), bidi_text, font=font, fill=text_color)

                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                new_page = output_pdf.new_page(-1, width=page.rect.width, height=page.rect.height)
                new_page.insert_image(new_page.rect, stream=img_byte_arr)

            pdf_document.close()

            output_pdf_stream = io.BytesIO()
            output_pdf.save(output_pdf_stream)
            output_pdf_stream.seek(0)
            output_pdf.close()

            bot.delete_message(chat_id, processing_message.message_id)
            bot.send_document(chat_id, output_pdf_stream, caption="تمت إضافة النص إلى جميع الصفحات.")
            bot.send_message(chat_id, "اكتملت المعالجة بنجاح.")

        except Exception as e:
            if processing_message:
                bot.delete_message(chat_id, processing_message.message_id)
            bot.send_message(chat_id, f"حدث خطأ أثناء المعالجة: {e}")
        finally:
            if pdf_document:
                pdf_document.close()
            if output_pdf:
                output_pdf.close()
            if chat_id in user_data:
                del user_data[chat_id]
    else:
        bot.reply_to(message, "يرجى إرسال ملف PDF أولاً.")

bot.infinity_polling()
