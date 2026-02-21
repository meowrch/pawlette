#!/usr/bin/env python3
import datetime
import subprocess
from pathlib import Path

from loguru import logger

import pawlette.constants as cnst
from pawlette.core.merge_copy import MergeCopyHandler
from pawlette.errors.themes import ThemeNotFound
from pawlette.schemas.config_struct import Config
from pawlette.schemas.themes import Theme


class SelectiveThemeManager:
    """
    Менеджер тем с git-концепцией.

    Принципы:
    1. Каждая тема = ветка в git
    2. Переключение темы = git checkout <theme-branch>
    3. Пользовательские изменения = uncommitted changes
    4. Простота и надежность
    """

    def __init__(self, config: Config):
        self.state_dir = cnst.APP_STATE_DIR
        self.config_dir = cnst.XDG_CONFIG_HOME
        self.git_repo = self.state_dir / "config_state.git"
        self.config = config

        self._ensure_directories()
        self._init_git_repo()

    def _ensure_directories(self):
        """Создаем необходимые директории"""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _init_git_repo(self):
        """Инициализируем git-репозиторий для состояний тем"""
        if not (self.git_repo / "HEAD").exists():
            logger.debug("Initializing git repository")
            self.git_repo.mkdir(parents=True, exist_ok=True)
            self._run_git("init", "--bare", "--initial-branch=main")
            self._run_git("config", "core.bare", "false")
            self._run_git("config", "core.worktree", str(self.config_dir))
            self._run_git("config", "user.name", "Pawlette")
            self._run_git("config", "user.email", "pawlette@example.com")
            # Создаем пустой коммит в main ветке
            self._run_git("commit", "--allow-empty", "-m", "Initial commit")

        # Создаем или обновляем info/exclude файл с универсальными паттернами
        self._create_git_exclude_file()

    def _create_git_exclude_file(self):
        """Создаем или обновляем info/exclude файл с универсальными паттернами игнорирования"""
        exclude_path = self.git_repo / "info" / "exclude"
        exclude_path.parent.mkdir(parents=True, exist_ok=True)

        self.ignored_patterns = [
            # Папки кешей и временных данных
            "**/Cache/",
            "**/cache/",
            "**/Caches/",
            "**/caches/",
            "**/GPUCache/",
            "**/ShaderCache/",
            "**/DawnCache/",
            "**/DawnWebGPUCache/",
            "**/DawnGraphiteCache/",
            "**/CachedData/",
            "**/CachedExtensions/",
            "**/CachedImages/",
            "**/CachedResources/",
            # Папки логов
            "**/logs/",
            "**/log/",
            "**/Logs/",
            "**/Log/",
            "**/logging/",
            "**/Logging/",
            # Папки временных данных
            "**/tmp/",
            "**/temp/",
            "**/temporary/",
            "**/Tmp/",
            "**/Temp/",
            "**/Temporary/",
            # Папки данных браузера/electron
            "**/Local Storage/",
            "**/Session Storage/",
            "**/IndexedDB/",
            "**/databases/",
            "**/File System/",
            "**/Service Worker/",
            "**/blob_storage/",
            "**/WebStorage/",
            "**/Application Cache/",
            "**/Media Cache/",
            "**/Platform Notifications/",
            "**/shared_proto_db/",
            "**/optimization_guide_hint_cache_store/",
            "**/optimization_guide_prediction_model_downloads/",
            "**/GrShaderCache/",
            # Firefox / Mozilla (XDG standard location)
            "mozilla/",
            ".mozilla/",
            "**/mozilla/",
            "**/.mozilla/",
            # Папки состояний приложений
            "**/globalStorage/",
            "**/workspaceStorage/",
            "**/sessionStorage/",
            "**/localStorage/",
            "**/sessionData/",
            "**/userData/",
            # Файлы по расширениям
            # Логи
            "*.log",
            "*.log.*",
            "*.logs",
            "*.out",
            "*.err",
            # Базы данных
            "*.db",
            "*.db-*",
            "*.sqlite",
            "*.sqlite3",
            "*.sqlite-*",
            "*.leveldb",
            # Временные файлы
            "*.tmp",
            "*.temp",
            "*.bak",
            "*.backup",
            "*.old",
            "*.orig",
            "*.swp",
            "*.swo",
            "*.~*",
            # Блокировки и процессы
            "*.lock",
            "*.pid",
            "*.lck",
            "*.lockfile",
            # Cookies и сессии
            "*Cookies*",
            "*cookies*",
            "*cookie*",
            "*Cookie*",
            "*Session*",
            "*session*",
            "*History*",
            "*history*",
            # Прочие временные данные
            "*TransportSecurity*",
            "*QuotaManager*",
            "*Favicons*",
            "*Thumbnails*",
            "*thumbnails*",
            "*Trash*",
            "*trash*",
            # Системные файлы
            ".DS_Store",
            ".DS_Store?",
            "._*",
            ".Spotlight-V100",
            ".Trashes",
            "ehthumbs.db",
            "Thumbs.db",
            # Недавно использованные файлы
            "*recently-used*",
            "*Recently-used*",
            "*.recently-used*",
            "*.Recently-used*",
            # Резервные копии
            "*~",
            "*.bak",
            "*.backup",
            "*.old",
            "*.orig",
            "*.save",
            "*.autosave",
        ]

        with open(exclude_path, "w") as f:
            f.write("\n".join(self.ignored_patterns))

    def _run_git(self, *args: str) -> bool:
        """Выполняем git команду в контексте нашего репозитория"""
        try:
            subprocess.run(
                ["git", "-C", str(self.git_repo)] + list(args),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git error: {e.stderr}")
            return False

    def _is_file_ignored(self, file_path: Path) -> bool:
        """Проверяем, игнорируется ли файл по паттернам"""
        relative_path = file_path.relative_to(self.config_dir)
        path_str = str(relative_path)

        for pattern in self.ignored_patterns:
            if self._matches_pattern(path_str, pattern):
                return True
        return False

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Проверка соответствия паттерну с поддержкой ** wildcards (gitignore-style).

        Python's fnmatch не поддерживает **, поэтому паттерны вида **/Cache/
        обрабатываются вручную: проверяем каждый компонент и суффикс пути.
        """
        import fnmatch

        # Нормализуем разделители пути
        normalized_path = path.replace("\\", "/")
        # Убираем trailing slash из паттерна (маркер директории, напр. **/Cache/)
        clean_pattern = pattern.rstrip("/")

        if "**" in clean_pattern:
            # Для паттернов вида **/foo или **/foo/bar: проверяем, совпадает ли
            # какой-либо компонент или суффикс пути с частью паттерна после **/
            # Пример: **/Cache/ -> ищем компонент "Cache" в любом месте пути
            suffix_pattern = clean_pattern.lstrip("*/")
            path_parts = normalized_path.split("/")
            for i in range(len(path_parts)):
                # Проверяем отдельный компонент (для **/Cache/ -> "Cache")
                if fnmatch.fnmatch(path_parts[i], suffix_pattern):
                    return True
                # Проверяем суффикс пути начиная с i (для **/foo/bar -> "foo/bar")
                candidate = "/".join(path_parts[i:])
                if fnmatch.fnmatch(candidate, suffix_pattern):
                    return True
            return False

        return fnmatch.fnmatch(normalized_path, clean_pattern)

    def _get_theme_files(self, theme: Theme) -> list[Path]:
        """Получаем все файлы темы, которые есть в config"""
        files = []
        configs_dir = theme.path / "configs"

        if not configs_dir.exists():
            return files

        for config_app_dir in configs_dir.iterdir():
            if not config_app_dir.is_dir():
                continue

            app_name = config_app_dir.name
            target_dir = self.config_dir / app_name

            # Рекурсивно собираем все файлы приложения
            for file_path in config_app_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(config_app_dir)
                    target_file = target_dir / relative_path

                    # Для патчей (.postpaw, .prepaw, .jsonpaw) ищем целевой файл
                    if file_path.suffix in [".postpaw", ".prepaw", ".jsonpaw"]:
                        target_file = target_dir / relative_path.with_suffix("")

                    if target_file.exists() and not self._is_file_ignored(target_file):
                        files.append(target_file)

        return files

    def _create_or_switch_branch(self, theme_name: str):
        """Создаем или переключаемся на ветку темы"""
        # Сначала коммитим все изменения перед переключением
        self._handle_uncommitted_changes()

        # Проверяем, существует ли ветка
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.git_repo),
                "show-ref",
                "--verify",
                f"refs/heads/{theme_name}",
            ],
            capture_output=True,
        )

        if result.returncode == 0:
            # Ветка существует, переключаемся
            logger.debug(f"Switching to existing branch: {theme_name}")
            ok = self._run_git("checkout", theme_name)
            if not ok:
                # Мягкий checkout упал — возможно, нетрекаемые файлы конфликтуют
                # с файлами из целевой ветки (напр. приложение регенерировало файл,
                # который был закоммичен в этой ветке ранее).
                # К этому моменту все tracked-изменения уже закоммичены выше,
                # поэтому --force безопасно перезапишет только нетрекаемые конфликты.
                logger.warning(
                    f"Checkout of '{theme_name}' failed, retrying with --force "
                    "(untracked conflicting files will be overwritten)"
                )
                ok = self._run_git("checkout", "--force", theme_name)
                if not ok:
                    raise RuntimeError(
                        f"Failed to checkout branch '{theme_name}' even with --force. "
                        "Check git logs for details."
                    )
        else:
            # Создаем новую ветку от базовой ветки main
            logger.debug(f"Creating new branch: {theme_name} from main")
            ok = self._run_git("checkout", "-b", theme_name, "main")
            if not ok:
                raise RuntimeError(
                    f"Failed to create and checkout new branch '{theme_name}' from main."
                )

    def _handle_uncommitted_changes(self):
        """Обрабатываем uncommitted изменения перед переключением ветки"""
        if self.has_uncommitted_changes():
            logger.debug("Found uncommitted changes, committing them")
            # Используем -A вместо . для добавления всех изменений из всего воркдерева.
            # При вызове через git -C <git_repo_dir>, точка . разрешается относительно
            # git_repo_dir, а НЕ относительно core.worktree (~/.config), из-за чего
            # изменения в конфигах пользователя не индексировались. Флаг -A явно
            # обходит весь worktree независимо от текущей директории.
            self._run_git("add", "-A")
            # Коммитим с сообщением о пользовательских изменениях
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._run_git(
                "commit", "-m", f"[USER] Save user customizations - {timestamp}"
            )

    def _clean_old_patches_from_file(self, file_path: Path):
        """Очищаем файл от всех существующих PAW-THEME патчей"""
        if not file_path.exists():
            return

        try:
            content = file_path.read_text()

            # Удаляем все PAW-THEME блоки с помощью регулярных выражений
            import re

            # Получаем стиль комментариев для файла
            from pawlette.core.patch_engine import FormatManager

            comment_style = FormatManager.get_comment_style(file_path, self.config)

            # Создаем паттерн для удаления всех PAW-THEME блоков.
            # Используем захватывающую группу (PRE|POST) с back-reference \1 вместо
            # (?:PRE|POST), чтобы гарантировать: PRE-START закрывается только PRE-END,
            # POST-START — только POST-END. Аналогично patch_engine.py.
            pattern = re.compile(
                rf"^\s*{re.escape(comment_style)}\s+PAW-THEME-(PRE|POST)-START:.*?^\s*{re.escape(comment_style)}\s+PAW-THEME-\1-END:.*?$",
                flags=re.DOTALL | re.MULTILINE,
            )

            # Удаляем все найденные блоки
            cleaned_content = pattern.sub("", content)

            # Убираем лишние пустые строки
            lines = cleaned_content.split("\n")
            cleaned_lines = []
            prev_empty = False

            for line in lines:
                is_empty = not line.strip()
                if not (is_empty and prev_empty):  # Избегаем множественных пустых строк
                    cleaned_lines.append(line)
                prev_empty = is_empty

            # Убираем trailing пустые строки
            while cleaned_lines and not cleaned_lines[-1].strip():
                cleaned_lines.pop()

            final_content = "\n".join(cleaned_lines)
            if final_content and not final_content.endswith("\n"):
                final_content += "\n"

            file_path.write_text(final_content)
            logger.debug(
                f"Cleaned old patches from: {file_path.relative_to(self.config_dir)}"
            )

        except Exception as e:
            logger.warning(f"Failed to clean patches from {file_path}: {e}")

    def _clean_old_patches_from_theme_files(self, theme_files: list[Path]):
        """Очищаем все файлы темы от старых патчей"""
        logger.info("Cleaning old patches from files")
        for file_path in theme_files:
            self._clean_old_patches_from_file(file_path)

    def cleanup_ignored_files(self):
        """
        Проверяет текущую ветку на наличие отслеживаемых файлов,
        которые теперь соответствуют паттернам игнорирования (info/exclude),
        и удаляет их из индекса git (но не с диска).

        Создаёт коммит 'chore: stop tracking ignored files' если что-то было удалено.
        """
        logger.info("Checking for ignored files in git index...")

        # 1. Получаем список всех tracked файлов (разделенных null-byte для безопасности путей)
        # ls-files -z выводит пути относительно корня репозитория (core.worktree)
        try:
            ls_result = subprocess.run(
                ["git", "-C", str(self.git_repo), "ls-files", "-z"],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list files: {e}")
            return

        if not ls_result.stdout:
            logger.info("No tracked files found.")
            return

        # 2. Передаем список tracked файлов в check-ignore
        # check-ignore --stdin -z -v -n
        #   --stdin: читаем пути из stdin
        #   -z: ввод/вывод разделен null-byte
        #   --exclude-standard: использовать info/exclude и .gitignore
        #   -v: (опционально) показать паттерн
        #   -n: (non-matching) НЕ используем, нам нужны только matching
        try:
            check_ignore_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.git_repo),
                    "check-ignore",
                    "--stdin",
                    "-z",
                    "--exclude-standard",
                ],
                input=ls_result.stdout,
                capture_output=True,
                # check=False, т.к. exit code 1 означает "ничего не найдено", что нормально
            )
        except subprocess.CalledProcessError as e:
            # check-ignore возвращает 128 при фатальных ошибках
            if e.returncode == 128:
                logger.error(f"git check-ignore failed: {e.stderr}")
                return
            # Код 1 просто означает, что игнорируемых файлов нет
            if e.returncode == 1:
                logger.info("No ignored files found in tracking.")
                return

        ignored_files_raw = check_ignore_result.stdout
        if not ignored_files_raw:
            logger.info("No ignored files found in tracking.")
            return

        # Разбиваем по \0 и фильтруем пустые строки
        ignored_files = [f for f in ignored_files_raw.split(b"\0") if f]

        if not ignored_files:
            return

        count = len(ignored_files)
        logger.info(
            f"Found {count} files that should be ignored but are tracked. Removing from index..."
        )

        # 3. Удаляем найденные файлы из индекса (но не с диска!)
        # git rm --cached --ignore-unmatch -z -- <paths...>
        chunk_size = 1000  # Разбиваем на чанки, чтобы не переполнить командную строку
        for i in range(0, len(ignored_files), chunk_size):
            chunk = ignored_files[i : i + chunk_size]
            try:
                # Преобразуем bytes пути обратно в строки для subprocess аргументов,
                # но безопасно передавать их через null-terminated нельзя в аргументах (только файл или stdin).
                # Поэтому используем --pathspec-from-file=- c -z
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(self.git_repo),
                        "rm",
                        "--cached",
                        "--ignore-unmatch",
                        "--pathspec-from-file=-",
                        "--pathspec-file-nul",
                    ],
                    input=b"\0".join(chunk),
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to remove files from index: {e}")
                continue

        # 4. Коммитим изменения
        if self.has_uncommitted_changes():
            logger.info("Committing changes...")
            self._run_git(
                "commit",
                "-m",
                "chore: stop tracking ignored files (cleaned via pawlette)",
                "--allow-empty",
            )
            logger.info("✅ Cleanup complete. Ignored files removed from git tracking.")
        else:
            logger.info("No changes needed.")

    def apply_theme(self, theme_name: str):
        """Применяем тему с git-концепцией"""
        logger.info(f"Applying theme: {theme_name}")

        # Получаем тему
        theme = self._get_theme(theme_name)
        if not theme:
            raise ThemeNotFound(theme_name)

        # Проверяем, нужно ли копировать файлы или просто переключить ветку
        self.get_current_theme()
        new_version = self._get_theme_version_from_installed(theme_name)

        # Сначала переключаемся на ветку темы, чтобы проверить её состояние
        self._create_or_switch_branch(theme_name)

        # Проверяем, была ли тема реально применена (есть ли коммит темы в истории)
        has_theme_commit = self._has_theme_commit_in_branch(theme_name)

        # Теперь проверяем версию в контексте этой ветки
        current_version = self._get_saved_theme_version_in_branch(theme_name)

        # Тема считается применённой только если:
        # 1. Версия совпадает
        # 2. И есть коммит темы в истории git
        if current_version == new_version and has_theme_commit:
            logger.info(
                f"Theme {theme_name} v{new_version} already applied, just switched branch"
            )
            # Выполняем команды перезагрузки даже при простом переключении веток
            self._execute_reload_commands(theme)
            return

        # Если версия совпадает, но нет коммита - значит .version файл остался после удаления репозитория
        if current_version == new_version and not has_theme_commit:
            logger.warning(
                f"Theme {theme_name} version file exists but no git commit found. Re-applying theme."
            )

        # Если версия изменилась и ветка существует - создаём бэкап старой ветки
        if (
            current_version != new_version
            and current_version != "unknown"
            and has_theme_commit
        ):
            self._backup_and_recreate_branch(theme_name, current_version)

        need_copy_files = (
            True  # Всегда копируем файлы при переключении или изменении версии
        )

        logger.info(
            f"Theme version: {current_version} -> {new_version}, need to copy files: {need_copy_files}"
        )

        if need_copy_files:
            # Получаем файлы темы для отслеживания
            theme_files = self._get_theme_files(theme)

            # ВАЖНО: Очищаем старые патчи перед применением новых
            self._clean_old_patches_from_theme_files(theme_files)

            # Применяем тему (используем существующий обработчик)
            logger.info(f"Copying theme files for: {theme_name}")
            merge = MergeCopyHandler(theme=theme, config=self.config)
            merge.apply_for_all_configs()

            # ВАЖНО: Получаем файлы темы ПОСЛЕ их создания И патчинга
            theme_files = self._get_theme_files(theme)

            # Сохраняем версию темы ПЕРЕД коммитом
            self._save_theme_version(theme_name, new_version)

            # Добавляем ВСЕ файлы темы в git ПОСЛЕ всех изменений (включая патчинг)
            for file_path in theme_files:
                if file_path.exists():
                    self._run_git("add", str(file_path))

            # Добавляем все измененные файлы (которые были модифицированы в процессе применения темы)
            # Это включает файлы, которые были изменены в процессе копирования и патчинга
            self._run_git("add", "-A")  # Добавляем все изменения

            # Коммитим все изменения темы (включая результаты патчинга)
            self._run_git("commit", "-m", f"Apply theme: {theme_name} v{new_version}")

            # Проверяем, что файлы действительно закоммичены
            uncommitted = self._get_uncommitted_files()
            if uncommitted:
                logger.warning(
                    f"Some files still uncommitted after theme apply: {uncommitted}"
                )

        logger.info(f"Theme {theme_name} applied successfully")

    def _execute_reload_commands(self, theme: Theme):
        """Выполняем команды перезагрузки для всех приложений темы"""
        configs_dir = theme.path / "configs"
        if not configs_dir.exists():
            return

        for app_dir in configs_dir.iterdir():
            if not app_dir.is_dir():
                continue

            app_name = app_dir.name
            command = cnst.RELOAD_COMMANDS.get(app_name, None)

            if command:
                logger.info(
                    f"Executing reload command for {app_name}: {command.command}"
                )
                try:
                    # Проверяем условия выполнения команды
                    if command.check_command_exists:
                        import shutil

                        if not shutil.which(command.check_command_exists):
                            logger.debug(
                                f"Command {command.check_command_exists} not found, skipping reload"
                            )
                            continue

                    if command.check_process:
                        result = subprocess.run(
                            ["pgrep", command.check_process], capture_output=True
                        )
                        if result.returncode != 0:
                            logger.debug(
                                f"Process {command.check_process} not running, skipping reload"
                            )
                            continue

                    # Выполняем команду
                    subprocess.run(
                        command.command.split(),
                        check=True,
                        capture_output=True,
                    )
                    logger.debug(f"Successfully reloaded {app_name}")

                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to reload {app_name}: {e}")
                except Exception as e:
                    logger.warning(
                        f"Error executing reload command for {app_name}: {e}"
                    )

    def _has_theme_commit_in_branch(self, theme_name: str) -> bool:
        """Проверяем, есть ли хотя бы один коммит применения темы в ветке"""
        try:
            # Проверяем историю коммитов в текущей ветке
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.git_repo),
                    "log",
                    "--oneline",
                    "--grep",
                    f"Apply theme: {theme_name}",
                    "-1",
                ],
                capture_output=True,
                text=True,
            )
            # Если нашёл коммит, то вернём True
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def _backup_and_recreate_branch(self, theme_name: str, old_version: str):
        """Создаём бэкап старой ветки и пересоздаём ветку темы от main"""
        import datetime

        # Сохраняем uncommitted изменения если есть
        self._handle_uncommitted_changes()

        # Создаём имя бэкапа с версией и временной меткой
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_branch_name = f"{theme_name}-v{old_version}-backup-{timestamp}"

        logger.info(f"Creating backup of old theme version: {backup_branch_name}")

        # Переименовываем текущую ветку в бэкап
        self._run_git("branch", "-m", theme_name, backup_branch_name)

        # Переключаемся на main
        self._run_git("checkout", "main")

        # Создаём новую чистую ветку от main
        logger.info(f"Creating fresh branch: {theme_name} from main")
        self._run_git("checkout", "-b", theme_name, "main")

        logger.info(f"⚠️  Theme update: old version backed up to '{backup_branch_name}'")
        logger.info(
            "📄 You can restore your customizations from the backup branch if needed"
        )

    def _save_theme_version(self, theme_name: str, version: str):
        """Сохраняем версию темы в state_dir"""
        # Сохраняем версию в state_dir
        version_file = self.state_dir / f"{theme_name}.version"
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(version)
        logger.debug(f"Saved theme version: {theme_name} = {version}")

    def _get_saved_theme_version_in_branch(self, theme_name: str) -> str:
        """Получаем версию темы из state_dir"""
        version_file = self.state_dir / f"{theme_name}.version"
        if version_file.exists():
            return version_file.read_text().strip()
        return "unknown"

    def _get_theme_version_from_installed(self, theme_name: str) -> str:
        """Получаем версию темы из installed_themes.json"""
        installed_themes_file = cnst.APP_STATE_DIR / "installed_themes.json"

        if not installed_themes_file.exists():
            logger.debug("installed_themes.json not found, using fallback version")
            return "unknown"

        try:
            import json

            with open(installed_themes_file) as f:
                installed_themes = json.load(f)

            # Проверяем точное имя и имя с префиксом catppuccin-
            for key in [theme_name, f"catppuccin-{theme_name}"]:
                if key in installed_themes:
                    version = installed_themes[key].get("version", "unknown")
                    logger.debug(
                        f"Found theme {theme_name} version {version} in installed_themes.json"
                    )
                    return version

            logger.debug(f"Theme {theme_name} not found in installed_themes.json")
            return "unknown"

        except Exception as e:
            logger.error(f"Failed to read installed_themes.json: {e}")
            return "unknown"

    def restore_user_commit(self, theme_name: str, commit_hash: str):
        """Восстанавливаем пользовательские изменения из коммита"""
        try:
            # Переключаемся на ветку темы
            self._create_or_switch_branch(theme_name)

            # Сохраняем текущие изменения если есть
            if self.has_uncommitted_changes():
                self._handle_uncommitted_changes()

            # Применяем изменения из коммита
            self._run_git("cherry-pick", commit_hash)

            logger.info(f"Restored user changes from commit {commit_hash}")

        except Exception as e:
            logger.error(f"Failed to restore user commit: {e}")
            raise

    def get_current_theme(self) -> str | None:
        """Получаем название текущей ветки (темы)"""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.git_repo), "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip()
            return branch if branch != "main" else None
        except subprocess.CalledProcessError:
            return None

    def has_uncommitted_changes(self) -> bool:
        """Проверяем, есть ли uncommitted изменения"""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.git_repo), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def _get_uncommitted_files(self) -> list[str]:
        """Получаем список uncommitted файлов"""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.git_repo), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    files.append(line[3:])  # Убираем статус и пробелы
            return files
        except subprocess.CalledProcessError:
            return []

    def get_user_changes_info(self, theme_name: str | None = None) -> dict:
        """Получаем информацию о пользовательских изменениях (uncommitted)"""
        try:
            # Если указана тема, переключаемся на неё
            if theme_name:
                current_theme = self.get_current_theme()
                if current_theme != theme_name:
                    self._create_or_switch_branch(theme_name)

            result = subprocess.run(
                ["git", "-C", str(self.git_repo), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )

            changed_files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    # Парсим вывод git status --porcelain
                    # Формат: XY filename (где XY - двухсимвольный статус)
                    # Но может быть и X filename (без второго символа статуса)
                    if len(line) >= 3:
                        # Ищем первый пробел после статуса
                        space_index = line.find(
                            " ", 2
                        )  # Ищем пробел после второго символа
                        if space_index == -1:
                            space_index = line.find(
                                " ", 1
                            )  # Ищем пробел после первого символа

                        if space_index != -1:
                            filename = line[
                                space_index + 1 :
                            ]  # Берем все после пробела
                            changed_files.append(filename)
                        else:
                            # Fallback: берем все после второго символа
                            filename = line[2:]
                            changed_files.append(filename)

            return {"has_changes": len(changed_files) > 0, "files": changed_files}
        except subprocess.CalledProcessError:
            return {"has_changes": False, "files": []}

    @staticmethod
    def _get_theme(theme_name: str) -> Theme | None:
        """Получаем тему по имени"""
        path = cnst.THEMES_FOLDER / theme_name
        sys_path = cnst.SYS_THEMES_FOLDER / theme_name

        for p in [sys_path, path]:
            if p.exists() and p.is_dir():
                return Theme(name=theme_name, path=p)
        return None

    def restore_original(self):
        """Возвращаем к базовому/оригинальному состоянию (main ветка)"""
        logger.info("Restoring to original state")

        # Сохраняем текущие изменения если есть
        if self.has_uncommitted_changes():
            self._handle_uncommitted_changes()

        # Переключаемся на main ветку
        self._run_git("checkout", "main")

        logger.info("Restored to original state (main branch)")

    def list_backup_branches(self) -> list[str]:
        """Получаем список всех бэкап веток"""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.git_repo), "branch", "--list", "*-backup-*"],
                capture_output=True,
                text=True,
                check=True,
            )
            branches = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    # Убираем звёздочку (* указывает на текущую ветку)
                    branch = line.strip().lstrip("* ").strip()
                    branches.append(branch)
            return branches
        except subprocess.CalledProcessError:
            return []

    def delete_backup_branch(self, branch_name: str) -> bool:
        """Удаляем бэкап ветки"""
        if "-backup-" not in branch_name:
            logger.error(f"Cannot delete non-backup branch: {branch_name}")
            return False

        logger.info(f"Deleting backup branch: {branch_name}")
        return self._run_git("branch", "-D", branch_name)

    def delete_theme_branch(self, theme_name: str) -> bool:
        """Удаляем ветку темы в git-репозитории состояний."""
        if not theme_name or theme_name == "main":
            logger.error(f"Cannot delete invalid theme branch: {theme_name}")
            return False

        # Проверяем, существует ли ветка
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.git_repo),
                "show-ref",
                "--verify",
                f"refs/heads/{theme_name}",
            ],
            capture_output=True,
        )

        if result.returncode != 0:
            logger.info(f"Theme branch '{theme_name}' does not exist, nothing to delete")
            return False

        logger.info(f"Deleting theme branch: {theme_name}")
        return self._run_git("branch", "-D", theme_name)

    def cleanup_old_backups(self, theme_name: str | None = None, keep_last: int = 3):
        """Удаляем старые бэкапы, оставляя только последние N"""
        backups = self.list_backup_branches()

        # Фильтруем по имени темы если указано
        if theme_name:
            backups = [b for b in backups if b.startswith(f"{theme_name}-")]

        # Сортируем по временной метке (новые в начале)
        backups.sort(reverse=True)

        # Удаляем всё кроме последних N
        for backup in backups[keep_last:]:
            self.delete_backup_branch(backup)

        if len(backups) > keep_last:
            logger.info(f"Cleaned up {len(backups) - keep_last} old backup(s)")
