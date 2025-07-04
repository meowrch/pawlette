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

## ⚡ Быстрый старт
Для установки на систему Arch Linux выполните команду:
```bash
yay -S pawlette-git
```

## 🛠 Архитектура тем
Темы хранятся в `/usr/share/pawlette/themes/` или в `~/.local/share/pawlette/themes/` со структурой:
```text
theme-name/
├── configs/           # Конфигурации приложений
│   ├── kitty/
│   │   └── kitty.conf.prepaw  # патч-файл
│   ├── waybar/
│   │   ├── style.css
│   │   └── config.json
│   └── ...
├── gtk-theme/     # Папка с темой GTK
├── gtk-theme/     # Папка с иконками
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
что и в `.config/.../`, но при этом добавляете в конце суффикс ".prepaw" или ".postpaw".

> [!INFO]
> Например был `kitty/kitty.conf`, а станет `kitty/kitty.conf.prepaw`
> Такой файл будет расцениваться как патч.

Если суффикс `.prepaw`, то содержимое этого файла вставится перед основной частью оригинальной конфигурации.
Соответственно, если суффикс `.postpaw`, то содержимое вставится после основной части оригинальной конфигурации.

## 🎛 Управление темами
| Команда                 | Описание                                |
| ----------------------- | ----------------------------------------|
| `generate-config`       | Сгенерировать конфигурацию по умолчанию |
| `pawlette get-themes`   | Список доступных тем                    |
| `pawlette theme <name>` | Применить указанную тему                |

## 🔄 Управление бэкапами
| Команда                                                             | Описание                       |
| ------------------------------------------------------------------- | ------------------------------ |
| `pawlette backup list ~/.config/<APP>/config.conf`                  | Показать все версии файла      |
| `pawlette backup restore ~/.config/<APP>/config.conf`               | Восстановить последнюю версию  |
| `pawlette backup restore ~/.config/<APP>/config.conf --hash abc123` | Восстановить конкретную версию |
| `pawlette system-backup list`                                       | Показать системные бэкапы      |
| `pawlette system-backup create --comment "Before dark theme"`       | Создать полный бэкап           |
| `pawlette system-backup restore BACKUP_ID`                          | Откатить всю систему           |

## ☕ Поддержать проект
Если Pawlette делает ваш рабочий стол красивее:
| Криптовалюта | Адрес                                              |
| ------------ | -------------------------------------------------- |
| **TON**      | `UQB9qNTcAazAbFoeobeDPMML9MG73DUCAFTpVanQnLk3BHg3` |
| **Ethereum** | `0x56e8bf8Ec07b6F2d6aEdA7Bd8814DB5A72164b13`       |
| **Bitcoin**  | `bc1qt5urnw7esunf0v7e9az0jhatxrdd0smem98gdn`       |
| **Tron**     | `TBTZ5RRMfGQQ8Vpf8i5N8DZhNxSum2rzAs`               |

Ваша поддержка мотивирует нас делать больше крутых фич! ❤️

## 📊 Статистика
[![Star History Chart](https://api.star-history.com/svg?repos=meowrch/pawlette&type=Date)](https://star-history.com/#meowrch/pawlette&Date)