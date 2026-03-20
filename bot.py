import os
import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
PHONE = os.getenv('PHONE')
MANAGER_TG = os.getenv('MANAGER_TG')

# Состояния для ConversationHandler
CHOOSING_CATEGORY, ADDING_PHOTO, ADDING_SIZE, ADDING_DESCRIPTION, ADDING_FACTS, ADDING_PRICE = range(6)
EDITING_PHOTO, EDITING_SIZE, EDITING_DESCRIPTION, EDITING_FACTS, EDITING_PRICE = range(6, 11)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('evas_studio.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            photo_id TEXT NOT NULL,
            size TEXT NOT NULL,
            description TEXT NOT NULL,
            facts TEXT NOT NULL,
            price TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Проверка, является ли пользователь администратором
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Главная клавиатура
def get_main_keyboard(user_id: int):
    keyboard = [
        ['Картины', 'Скульптуры'],
        ['Декор', 'Связь со студией']
    ]
    if is_admin(user_id):
        keyboard.append(['Админ-панель'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Добро пожаловать в студию EvaS. Здесь можно посмотреть наши работы",
        reply_markup=get_main_keyboard(user.id)
    )

# Обработка категорий товаров
async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category_map = {
        'Картины': 'paintings',
        'Скульптуры': 'sculptures',
        'Декор': 'decor'
    }
    
    category_name = update.message.text
    category = category_map.get(category_name)
    
    if not category:
        return
    
    conn = sqlite3.connect('evas_studio.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE category = ?', (category,))
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        await update.message.reply_text(
            f"В категории '{category_name}' пока нет товаров.",
            reply_markup=get_main_keyboard(update.effective_user.id)
        )
        return
    
    for product in products:
        product_id, cat, photo_id, size, description, facts, price = product
        caption = f"📦 <b>Размер:</b> {size}\n\n"
        caption += f"📝 <b>Описание:</b> {description}\n\n"
        caption += f"✨ <b>Интересные факты:</b> {facts}\n\n"
        caption += f"💰 <b>Цена:</b> {price}"
        
        await update.message.reply_photo(
            photo=photo_id,
            caption=caption,
            parse_mode='HTML'
        )
    
    await update.message.reply_text(
        "Показаны все товары из выбранной категории.",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )

# Связь со студией
async def contact_studio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📞 Телефон", callback_data='contact_phone')],
        [InlineKeyboardButton("💬 Telegram менеджера", callback_data='contact_telegram')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Выберите способ связи со студией:",
        reply_markup=reply_markup
    )

# Обработка кнопок связи
async def contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'contact_phone':
        await query.edit_message_text(f"📞 Номер телефона студии:\n{PHONE}")
    elif query.data == 'contact_telegram':
        await query.edit_message_text(f"💬 Telegram менеджера:\n@{MANAGER_TG}")

# Админ-панель
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("У вас нет доступа к админ-панели.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить товар", callback_data='add_product')],
        [InlineKeyboardButton("✏️ Редактировать товар", callback_data='edit_product')],
        [InlineKeyboardButton("🗑 Удалить товар", callback_data='delete_product')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔧 Админ-панель\nВыберите действие:",
        reply_markup=reply_markup
    )

# Добавление товара - выбор категории
async def add_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🖼 Картины", callback_data='add_paintings')],
        [InlineKeyboardButton("🗿 Скульптуры", callback_data='add_sculptures')],
        [InlineKeyboardButton("🎨 Декор", callback_data='add_decor')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Выберите категорию товара:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_CATEGORY

# Начало добавления товара
async def start_adding_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    category_map = {
        'add_paintings': 'paintings',
        'add_sculptures': 'sculptures',
        'add_decor': 'decor'
    }
    
    context.user_data['adding_category'] = category_map[query.data]
    
    await query.edit_message_text("Отправьте фото товара:")
    return ADDING_PHOTO

# Получение фото
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправьте фото.")
        return ADDING_PHOTO
    
    photo = update.message.photo[-1]
    context.user_data['photo_id'] = photo.file_id
    
    await update.message.reply_text("Фото получено. Теперь введите размер товара:")
    return ADDING_SIZE

# Получение размера
async def receive_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['size'] = update.message.text
    await update.message.reply_text("Размер получен. Теперь введите описание товара:")
    return ADDING_DESCRIPTION

# Получение описания
async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Описание получено. Теперь введите интересные факты о товаре:")
    return ADDING_FACTS

# Получение фактов
async def receive_facts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['facts'] = update.message.text
    await update.message.reply_text("Факты получены. Теперь введите цену товара:")
    return ADDING_PRICE

# Получение цены и сохранение
async def receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    
    # Сохранение в базу данных
    conn = sqlite3.connect('evas_studio.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (category, photo_id, size, description, facts, price)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        context.user_data['adding_category'],
        context.user_data['photo_id'],
        context.user_data['size'],
        context.user_data['description'],
        context.user_data['facts'],
        context.user_data['price']
    ))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        "✅ Товар успешно добавлен!",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    
    context.user_data.clear()
    return ConversationHandler.END

# Редактирование товара
async def edit_product_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('evas_studio.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, category, description FROM products')
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        await query.edit_message_text("Нет товаров для редактирования.")
        return ConversationHandler.END
    
    keyboard = []
    category_names = {
        'paintings': '🖼',
        'sculptures': '🗿',
        'decor': '🎨'
    }
    
    for product in products:
        product_id, category, description = product
        emoji = category_names.get(category, '📦')
        button_text = f"{emoji} ID:{product_id} - {description[:30]}..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'edit_{product_id}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите товар для редактирования:", reply_markup=reply_markup)

# Выбор параметра для редактирования
async def edit_product_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[1])
    context.user_data['editing_product_id'] = product_id
    
    keyboard = [
        [InlineKeyboardButton("📷 Фото", callback_data=f'editfield_photo')],
        [InlineKeyboardButton("📏 Размер", callback_data=f'editfield_size')],
        [InlineKeyboardButton("📝 Описание", callback_data=f'editfield_description')],
        [InlineKeyboardButton("✨ Факты", callback_data=f'editfield_facts')],
        [InlineKeyboardButton("💰 Цена", callback_data=f'editfield_price')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Редактирование товара ID:{product_id}\nВыберите параметр для редактирования:",
        reply_markup=reply_markup
    )

# Начало редактирования конкретного поля
async def start_editing_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    field = query.data.split('_')[1]
    context.user_data['editing_field'] = field
    
    field_names = {
        'photo': ('фото', EDITING_PHOTO),
        'size': ('размер', EDITING_SIZE),
        'description': ('описание', EDITING_DESCRIPTION),
        'facts': ('интересные факты', EDITING_FACTS),
        'price': ('цену', EDITING_PRICE)
    }
    
    field_name, state = field_names[field]
    
    if field == 'photo':
        await query.edit_message_text(f"Отправьте новое фото:")
    else:
        await query.edit_message_text(f"Введите новое значение для поля '{field_name}':")
    
    return state

# Обработчики редактирования полей
async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправьте фото.")
        return EDITING_PHOTO
    
    photo = update.message.photo[-1]
    product_id = context.user_data['editing_product_id']
    
    conn = sqlite3.connect('evas_studio.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET photo_id = ? WHERE id = ?', (photo.file_id, product_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        "✅ Фото успешно обновлено!",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    context.user_data.clear()
    return ConversationHandler.END

async def edit_field_text(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str):
    new_value = update.message.text
    product_id = context.user_data['editing_product_id']
    
    conn = sqlite3.connect('evas_studio.db')
    cursor = conn.cursor()
    cursor.execute(f'UPDATE products SET {field} = ? WHERE id = ?', (new_value, product_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ Поле '{field}' успешно обновлено!",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    context.user_data.clear()
    return ConversationHandler.END

async def edit_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await edit_field_text(update, context, 'size')

async def edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await edit_field_text(update, context, 'description')

async def edit_facts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await edit_field_text(update, context, 'facts')

async def edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await edit_field_text(update, context, 'price')

# Удаление товара
async def delete_product_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('evas_studio.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, category, description FROM products')
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        await query.edit_message_text("Нет товаров для удаления.")
        return
    
    keyboard = []
    category_names = {
        'paintings': '🖼',
        'sculptures': '🗿',
        'decor': '🎨'
    }
    
    for product in products:
        product_id, category, description = product
        emoji = category_names.get(category, '📦')
        button_text = f"{emoji} ID:{product_id} - {description[:30]}..."
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'delete_{product_id}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите товар для удаления:", reply_markup=reply_markup)

# Подтверждение удаления
async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[1])
    
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f'confirmdelete_{product_id}')],
        [InlineKeyboardButton("❌ Отмена", callback_data='canceldelete')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Вы уверены, что хотите удалить товар ID:{product_id}?",
        reply_markup=reply_markup
    )

# Выполнение удаления
async def execute_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'canceldelete':
        await query.edit_message_text("Удаление отменено.")
        return
    
    product_id = int(query.data.split('_')[1])
    
    conn = sqlite3.connect('evas_studio.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ Товар ID:{product_id} успешно удален!")

# Отмена операции
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Операция отменена.",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    # Инициализация БД
    init_db()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчик добавления товара
    add_product_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_product_category, pattern='^add_product$')],
        states={
            CHOOSING_CATEGORY: [CallbackQueryHandler(start_adding_product, pattern='^add_(paintings|sculptures|decor)$')],
            ADDING_PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
            ADDING_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_size)],
            ADDING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description)],
            ADDING_FACTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_facts)],
            ADDING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Обработчик редактирования товара
    edit_product_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_product_select, pattern='^edit_product$')],
        states={
            CHOOSING_CATEGORY: [
                CallbackQueryHandler(edit_product_choose_field, pattern='^edit_\d+$'),
                CallbackQueryHandler(start_editing_field, pattern='^editfield_')
            ],
            EDITING_PHOTO: [MessageHandler(filters.PHOTO, edit_photo)],
            EDITING_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_size)],
            EDITING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_description)],
            EDITING_FACTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_facts)],
            EDITING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_price)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(add_product_handler)
    application.add_handler(edit_product_handler)
    
    application.add_handler(CallbackQueryHandler(edit_product_choose_field, pattern='^edit_\d+$'))
    application.add_handler(CallbackQueryHandler(start_editing_field, pattern='^editfield_'))
    
    application.add_handler(MessageHandler(filters.Regex('^(Картины|Скульптуры|Декор)$'), show_category))
    application.add_handler(MessageHandler(filters.Regex('^Связь со студией$'), contact_studio))
    application.add_handler(MessageHandler(filters.Regex('^Админ-панель$'), admin_panel))
    
    application.add_handler(CallbackQueryHandler(contact_callback, pattern='^contact_'))
    application.add_handler(CallbackQueryHandler(delete_product_select, pattern='^delete_product$'))
    application.add_handler(CallbackQueryHandler(confirm_delete, pattern='^delete_\d+$'))
    application.add_handler(CallbackQueryHandler(execute_delete, pattern='^confirmdelete_|^canceldelete$'))
    
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
