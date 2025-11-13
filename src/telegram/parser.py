# src/telegram/parser.py

import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel, User
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChannelParser:
    """Парсер сообщений из Telegram канала с polling механизмом"""

    POLL_INTERVAL = 1.5
    POLL_LIMIT = 10

    def __init__(self, client: TelegramClient, broadcaster):
        self.client = client
        self.broadcaster = broadcaster
        self.channel_id = int(config.CHANNEL_ID)
        self.processed_ids: set[int] = set()
        self._connection_state: bool | None = None

    async def start(self) -> None:
        """Запуск парсера с polling механизмом"""
        try:
            entity = await self.client.get_entity(self.channel_id)

            if isinstance(entity, Channel):
                channel_name = entity.title
            elif isinstance(entity, User):
                channel_name = entity.first_name or entity.username or "unknown"
            else:
                channel_name = "unknown"
        except Exception as e:
            logger.error(f'Ошибка получения имени канала: {type(e).__name__}: {e}', exc_info=True)
            channel_name = "unknown"

        logger.info(f'Запуск парсера для канала {channel_name} (ID: {self.channel_id})')

        try:
            await self._init_processed_ids()
        except Exception as e:
            logger.error(f'Ошибка инициализации: {type(e).__name__}: {e}', exc_info=True)
            raise

        asyncio.create_task(self._polling_loop())
        asyncio.create_task(self._monitor_connection())

        logger.info('Парсер активен, начинаем polling')

    async def _init_processed_ids(self) -> None:
        """Получить ID последних сообщений при старте"""
        logger.debug(f'Инициализация: получаю последние {self.POLL_LIMIT} сообщений из канала')

        messages = await self.client.get_messages(self.channel_id, limit=self.POLL_LIMIT)
        if messages:
            for msg in messages:
                self.processed_ids.add(msg.id)
            logger.info(
                f'Инициализация: сохранено {len(messages)} ID сообщений (от {messages[-1].id} до {messages[0].id})')
        else:
            logger.info('Канал пуст')

    async def _polling_loop(self) -> None:
        """Бесконечный polling каждые 1.5 секунды"""
        logger.info('_polling_loop: запущен')

        try:
            while True:
                try:
                    await asyncio.sleep(self.POLL_INTERVAL)

                    logger.debug(f'Polling: получаю последние {self.POLL_LIMIT} сообщений')
                    messages = await self.client.get_messages(self.channel_id, limit=self.POLL_LIMIT)

                    if not messages:
                        logger.debug('Polling: канал пуст')
                        continue

                    logger.debug(f'Polling: получено {len(messages)} сообщений, IDs: {[m.id for m in messages]}')

                    new_messages = [m for m in messages if m.id not in self.processed_ids]

                    if new_messages:
                        logger.debug(
                            f'Polling: найдено {len(new_messages)} новых сообщений, IDs: {[m.id for m in new_messages]}')

                        for message in reversed(new_messages):
                            self.processed_ids.add(message.id)
                            await self._handle_message(message)
                    else:
                        logger.debug('Polling: нет новых сообщений')

                except Exception as e:
                    logger.error(f'_polling_loop: исключение {type(e).__name__}: {e}', exc_info=True)

        except asyncio.CancelledError:
            logger.info('Polling остановлен')

    async def _monitor_connection(self) -> None:
        """Мониторить состояние соединения"""
        logger.info('_monitor_connection: запущен')

        try:
            while True:
                try:
                    is_connected = self.client.is_connected()
                    logger.debug(f'Connection status: {is_connected}')

                    if self._connection_state is None:
                        self._connection_state = is_connected
                        logger.debug(f'Connection state initialized: {is_connected}')
                    elif self._connection_state != is_connected:
                        if is_connected:
                            logger.info('Telethon: соединение восстановлено')
                        else:
                            logger.warning('Telethon: соединение потеряно')
                        self._connection_state = is_connected

                    await asyncio.sleep(10)
                except Exception as e:
                    logger.error(f'_monitor_connection: исключение {type(e).__name__}: {e}', exc_info=True)

        except asyncio.CancelledError:
            logger.info('Мониторинг остановлен')

    async def _handle_message(self, message) -> None:
        """Обработка нового сообщения"""
        try:
            message_text = message.text
            message_id = message.id

            if not message_text:
                logger.debug(f'_handle_message: ID={message_id} без текста, пропускаю')
                return

            escaped_text = message_text.replace('\n', '\\n')
            logger.info(f'Новое сообщение [ID={message_id}]: {escaped_text}')

            logger.debug(f'_handle_message: отправляю в рассылку')
            stats = await self.broadcaster.broadcast_message(message_text)
            logger.info(f'Рассылка завершена: {stats}')

        except Exception as e:
            logger.error(f'_handle_message: исключение {type(e).__name__}: {e}', exc_info=True)