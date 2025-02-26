# 🐾 Pawlette
Универсальный менеджер тем. 
Легко переключайтесь между темами для своего рабочего стола, сохраняя индивидуальные настройки. 
Под капотом — гибкая система патчей и атомарные операции.

> [!Warning]
> Проект находится в активной разработке.  
> Для production-использования рекомендуется версия 1.0+

## 🌟 Особенности
- **Полная поддержка XDG**
- **Неинвазивная система патчей** с автоматическим откатом
- **Модульная архитектура** обработчиков конфигов
- **Сквозная проверка целостности** файлов
- **Транзакционная система** изменений
- **Поддержка пользовательских тем** через единый формат
- **Автоматические бэкапы** перед изменениями
- **Частичное изменение** конфигураций (patch)

## 🛠 Архитектура тем
Темы хранятся в `/usr/share/pawlette/themes/` или в `~/.local/share/pawlette/themes/` со структурой:
```text
theme-name/
├── configs/           # Конфигурации приложений
│   ├── kitty/
│   │   └── kitty.conf.pre_pawlette  # патч-файл
│   ├── waybar/
│   │   ├── style.css
│   │   └── config.json
│   └── ...
└── global/            # Глобальные параметры темы
    ├── gtk/           # Папка с темой GTK
    └── wallpapers/    # Папка с обоями
```
Папка `configs` должна иметь ту-же архитектуру, что и `~/.config`.
Вы можете создавать папки для каждого приложения, и добавлять конфигурации. 
При этом не обязательно добавлять абсолютно все конфигурации. 
Вы можете ограничиться лишь теми, которые должны изменяться от темы к теме. 

Применение тем происходит в формате слияния двух директорий. 
Если определенного файла/папки не было, то он создастся. 
А если был, то изменит контент на тот, который был написан в вашей теме.

### Патчинг конфигураций
Если файл уже существует в `.config/.../`, 
и вам нужно частично изменить его (вставить что-то в начало или конец), то
для вас мы реализовали систему патчинга (patch). 

Она заключается в том, что вы создаете файл с абсолютно тем-же названием и расширением,
что и в `.config/.../`, но при этом добавляете в конце суффикс ".pre_pawlette" или ".post_pawlette".

>[!INFO]
> Например был `kitty/kitty.conf`, а станет `kitty/kitty.conf.pre_pawlette`
> Такой файл будет расцениваться как патч. 

Если суффикс `.pre_pawlette`, то содержимое этого файла вставится перед основной частью оригинальной конфигурации.
Соответственно, если суффикс `.post_pawlette`, то содержимое вставится после основной части оригинальной конфигурации.

## 🎛 Управление темами
| Команда                 | Описание                                |
| ----------------------- | ----------------------------------------|
| `generate-config`       | Сгенерировать конфигурацию по умолчанию |
| `pawlette get-themes`   | Список доступных тем                    |
| `pawlette theme <name>` | Применить указанную тему                |

## 🐾 Особые Благодарности
Проект использует лучшие практики из:
- **GTheme** \
    Архитектура транзакционных изменений и система патчей

- **Catppuccin Manager** \
    Подход к управлению цветовыми схемами и интеграции с приложениями

Отдельная благодарность сообществу Arch Linux за вдохновение и базовые концепции.

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