import unittest
from unittest.mock import patch

from extra_commands import Extras


class TimerCommandTests(unittest.TestCase):
    def setUp(self):
        self.notifications = []
        self.extras = Extras(self.notifications.append)
        self.addCleanup(self.extras.close)
        timer_patch = patch('extra_commands.threading.Timer')
        self.timer_class = timer_patch.start()
        self.addCleanup(timer_patch.stop)

    def test_combined_duration_and_completion(self):
        command = 'Поставь таймер на один час и пятнадцать минут 30 секунд'
        self.assertTrue(self.extras.recognized(command))
        self.assertEqual(
            self.extras.handle(command),
            'Таймер 1 поставлен на 1 час 15 минут 30 секунд.',
        )
        seconds, complete = self.timer_class.call_args.args
        self.assertEqual(seconds, 4530)
        complete()
        self.assertEqual(self.notifications, ['Таймер 1 завершён: 1 час 15 минут 30 секунд.'])
        self.assertEqual(self.extras.timer_snapshot(), [])

    def test_cancel_one_timer_by_spoken_number(self):
        self.assertEqual(self.extras.handle('таймер 5 минут'), 'Таймер 1 поставлен на 5 минут.')
        self.extras.handle('таймер 1 час')
        command = 'Отмени таймер номер один'
        self.assertTrue(self.extras.recognized(command))
        self.assertEqual(self.extras.handle(command), 'Таймер 1 отменён.')
        self.assertEqual([identifier for identifier, _ in self.extras.timer_snapshot()], [2])
        self.timer_class.return_value.cancel.assert_called_once()
        self.timer_class.call_args_list[0].args[1]()
        self.assertEqual(self.notifications, [])
        self.assertEqual(self.extras.handle('отмени таймер 1'), 'Активного таймера 1 нет.')
        self.assertEqual(self.extras.handle('отмени таймеры'), 'Все таймеры отменены.')
        self.assertEqual(self.extras.timer_snapshot(), [])

    def test_invalid_durations_do_not_schedule_timers(self):
        for duration in ('1 минута 2 минуты', '24 часа и 1 секунда', '0 секунд', '1 час потом 2 минуты'):
            with self.subTest(duration=duration):
                self.extras.handle(f'таймер {duration}')
        self.timer_class.assert_not_called()
