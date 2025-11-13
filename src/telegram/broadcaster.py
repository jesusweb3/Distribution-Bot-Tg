# src/telegram/broadcaster.py

import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Broadcaster:
    """Массовая рассылка сообщений пользователям из whitelist"""

    MAX_CONCURRENT = 10

    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
        self.whitelist = config.WHITELIST_IDS
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)

    async def broadcast_message(self, text: str) -> dict:
        """
        Отправить сообщение всем пользователям из whitelist параллельно

        Args:
            text: Текст сообщения для отправки

        Returns:
            Словарь со статистикой: {'total': int, 'success': int, 'failed': int}
        """
        if not text:
            logger.warning('Broadcast: пустое сообщение, отправка отменена')
            return {'total': 0, 'success': 0, 'failed': 0}

        if not self.whitelist:
            logger.warning('Broadcast: whitelist пуст')
            return {'total': 0, 'success': 0, 'failed': 0}

        escaped_text = text.replace('\n', '\\n')[:100]
        logger.info(f'Broadcast: начинаем отправку "{escaped_text}..." для {len(self.whitelist)} пользователей')

        all_recipients = [7678650605] + list(self.whitelist)
        tasks = [self._send_message_limited(user_id, text) for user_id in all_recipients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        whitelist_results = results[1:]
        success = sum(1 for r in whitelist_results if r is True)
        failed = len(whitelist_results) - success

        logger.info(f'Broadcast: завершена. Успешно: {success}/{len(self.whitelist)}, Ошибок: {failed}')

        return {
            'total': len(self.whitelist),
            'success': success,
            'failed': failed
        }

    async def _send_message_limited(self, user_id: int, text: str) -> bool:
        """Отправить сообщение с семафором для лимитирования параллелизма"""
        async with self.semaphore:
            return await self._send_message(user_id, text)

    async def _send_message(self, user_id: int, text: str) -> bool:
        """Отправить сообщение одному пользователю"""
        try:
            await self.bot.send_message(chat_id=user_id, text=text)
            logger.debug(f'Broadcast: отправлено пользователю {user_id}')
            return True
        except TelegramAPIError as e:
            logger.error(f'Broadcast: {user_id} - {type(e).__name__}: {e}')
            return False
        except Exception as e:
            logger.error(f'Broadcast: {user_id} - {type(e).__name__}: {e}', exc_info=True)
            return False

    async def close(self) -> None:
        """Закрыть сессию бота"""
        await self.bot.session.close()
        logger.info('Broadcaster: сессия закрыта')


broadcaster = Broadcaster()