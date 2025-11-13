# main.py

import asyncio
from src.telegram.auth import auth
from src.telegram.parser import ChannelParser
from src.telegram.broadcaster import broadcaster
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main() -> None:
    """Основной запуск приложения"""
    try:
        logger.info('Запуск приложения')

        client = await auth.get_client()
        parser = ChannelParser(client, broadcaster)
        await parser.start()

        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info('Получен сигнал прерывания')
    except Exception as e:
        logger.error(f'Ошибка в main: {type(e).__name__}: {e}', exc_info=True)
    finally:
        tasks = [task for task in asyncio.all_tasks() if task != asyncio.current_task()]
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        await broadcaster.close()
        await auth.disconnect()
        logger.info('Приложение завершено')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass