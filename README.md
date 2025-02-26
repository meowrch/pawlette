# 🐾 Pawlette
Универсальный менеджер тем. 
Легко переключайтесь между темами для своего рабочего стола, сохраняя индивидуальные настройки. 
Под капотом — гибкая система патчей и атомарные операции.

> [!Warning]
> Проект находится в активной разработке.  
> Для production-использования рекомендуется версия 1.0+

## 🌟 Особенности
- **Неинвазивная система патчей** с автоматическим откатом
- **Модульная архитектура** обработчиков конфигов
- **Сквозная проверка целостности** файлов
- **Транзакционная система** изменений
- **Поддержка пользовательских тем** через единый формат
- **Автоматические бэкапы** перед изменениями

## 🛠 Архитектура тем
Темы хранятся в `/usr/share/pawlette/themes/` или в `~/.local/share/pawlette/themes/` со структурой:
```text
theme-name/
├── configs/           # Полные конфигурации приложений
│   ├── kitty/
│   └── waybar/
├── global/            # Глобальные параметры темы
│   ├── gtk
│   └── wallpapers/
└── patches/        # Частичные изменения конфигураций
    ├── fish.conf.patch
    └── hyprland.conf.patch
```
Пример патча:
```ini
# PAW-THEME-START: material-dark
background = #1A1A1A
font_size = 12
# PAW-THEME-END: material-dark
```

## 🎛 Управление темами
| Команда                 | Описание                       |
| ----------------------- | ------------------------------ |
| `pawlette get-themes`   | Список доступных тем           |
| `pawlette theme <name>` | Применить указанную тему       |
| `pawlette theme-revert` | Откатить последнее применение  |
| `pawlette verify`       | Проверить целостность конфигов |
| `pawlette state`        | Показать системные метрики     |

## 🐾 Особые Благодарности
Проект использует лучшие практики из:
- **GTheme** \
    Архитектура транзакционных изменений и система патчей

- **Catppuccin Manager** \
    Подход к управлению цветовыми схемами и интеграции с приложениями

Отдельная благодарность сообществу Arch Linux за вдохновение и базовые концепции.

## 🚀 Развитие проекта
Хотите добавить обработчик для нового приложения?
Создайте класс-наследник AppHandler!

```python
class MyAppHandler(AppHandler):
    def apply(self, theme: Theme):
        # Ваша логика применения темы
        self.run_hook("post_apply")
```
Зарегистрируйте обработчик
```python
HANDLERS["myapp"] = MyAppHandler(
    reload_cmd="systemctl restart myapp"
)
```
Отправьте Pull Request! 🎉

## ☕ Поддержать проект
Если Pawlette делает ваш рабочий стол красивее:
| Криптовалюта | Адрес                                              |
| ------------ | -------------------------------------------------- |
| **TON**      | `UQCsIhKtqCnh0Mp76X_5qfh66TPBoBsYx_FihgInw-Auk5BA` |
| **Ethereum** | `0x56e8bf8Ec07b6F2d6aEdA7Bd8814DB5A72164b13`       |
| **Bitcoin**  | `bc1qt5urnw7esunf0v7e9az0jhatxrdd0smem98gdn`       |
| **Tron**     | `TBTZ5RRMfGQQ8Vpf8i5N8DZhNxSum2rzAs`               |

Ваша поддержка мотивирует нас делать больше крутых фич! ❤️

## 📊 Статистика
[![Star History Chart](https://api.star-history.com/svg?repos=meowrch/pawlette&type=Date)](https://star-history.com/#meowrch/pawlette&Date)