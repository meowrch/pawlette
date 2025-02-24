from handlers import MergeCopyHandler

HANDLERS = {
    # Название папки с конфигурацией: Хендлер
    "hypr": MergeCopyHandler(reload_cmd="hyprctl reload"),
    "waybar": MergeCopyHandler(reload_cmd="killall -SIGUSR2 waybar"),
    "qt5ct": MergeCopyHandler(),
    "qt6ct": MergeCopyHandler(),
    "kitty": MergeCopyHandler(reload_cmd="killall -SIGUSR1 kitty"),
    "fish": MergeCopyHandler(
        reload_cmd='fish -c echo "y" | fish_config theme save pawlette'
    ),
    "starship": MergeCopyHandler(),
}
