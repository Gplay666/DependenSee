# Источники и охват

Дата сбора: **2026-11-04**. Все ссылки — на публичные страницы; вход, CAPTCHA и анти-бот-защита не обходились.

## Итоговая выборка

| Площадка | Способ доступа | Сырой пул | Отобрано | Даты отобранных |
|---|---|---|---:|---|
| Reddit | Публичный архив Arctic Shift (`arctic-shift.photon-reddit.com`) | 410 уникальных постов, из них 351 живой | 46 | 2020-01-09 — 2026-08-18 |
| Ask Ubuntu | Официальный Stack Exchange API 2.3 | входит в 1 020 уникальных вопросов | 25 | 2020-01-14 — 2026-05-03 |
| Unix & Linux Stack Exchange | Официальный Stack Exchange API 2.3 | входит в 1 020 уникальных вопросов | 17 | 2020-04-21 — 2026-02-17 |
| Fedora Discussion | Публичный Discourse API | 600 найденных topic id; детали загружены для 215 | 20 | 2021-08-28 — 2026-10-11 |
| GitHub | GitHub Search API (issues) | 779 уникальных issue | 20 | 2020-01-08 — 2026-11-02 |
| Arch Linux Forums | Публичный поиск FluxBB и страницы тем | 140 уникальных тем | 6 | 2026-04-23 — 2026-10-31 |
| Debian User Forums | Публичный поиск | 0 | 0 | — |

Итого: **134 публикации**, **6 площадок** (Reddit, Ask Ubuntu, Unix & Linux, Fedora Discussion, GitHub, Arch Linux Forums). 116 строк опубликованы в 2021 году или позже; 18 строк — в 2020 году (оставлены как особенно близкие к теме).

## Как искали

### Reddit

Использован публичный архив Arctic Shift, потому что прямой Reddit API отдавал `403`, а RSS был слишком медленным и неполным.

- Сабреддиты: `linux`, `linuxquestions`, `linux4noobs`, `debian`, `Ubuntu`, `archlinux`, `fedora`, `linuxmint`.
- Основные запросы: `unused packages`, `unused dependencies`, `orphaned packages`, `dependency tree`, `dependency graph`, `autoremove`.
- Дополнительные запросы для отдельных сабреддитов: `remove packages safely`, `disk space packages`, `visualize dependencies`, `broken dependencies`, `pacman orphans`, `remove dependencies`, `remove packages`.
- Собрано 13 поисковых выдач; после дедупликации — 410 постов, из них 351 не удалён и не скрыт. Для набора отобраны 46.
- Отобраны публикации из `r/linuxquestions` (29), `r/linux4noobs` (15), `r/linux` (2).

Оценки и число комментариев Reddit — снимок архива, а не live-значения на reddit.com.

### Stack Exchange

Использован официальный API `api.stackexchange.com/2.3/search/advanced` с фильтром `withbody`.

- Сайты: `askubuntu`, `unix`.
- 22 запроса: `unused packages`, `remove unused dependencies`, `orphaned packages`, `autoremove`, `dependency tree`, `dependency graph`, `visualize dependencies`, `reverse dependencies`, `disk space packages`, `clean up packages`, `remove packages safely`, `broken dependencies`, `package manager gui`, `find unused libraries`, `apt purge`, `installed packages size`, `snap disk space`, `flatpak unused runtimes`, `remote server packages`, `aptitude why`, `deborphan`, `dpkg dependencies`.
- После дедупликации — 1 020 вопросов. Для набора отобраны 42: 25 на Ask Ubuntu и 17 на Unix & Linux.
- `comments_count` в наборе для Stack Exchange — это число ответов (`answer_count`), а не комментариев. Это ограничение сопоставимости.

### Fedora Discussion

Использован публичный Discourse API: `search.json` для поиска и `t/{id}.json` для первой публикации темы.

- 14 запросов: `unused packages`, `unused dependencies`, `orphaned packages`, `dependency tree`, `dependency graph`, `visualize dependencies`, `autoremove`, `remove packages safely`, `disk space packages`, `clean up packages`, `reverse dependencies`, `dnf remove dependencies`, `flatpak unused`, `package cleanup`.
- Найдено 600 topic id. Детали загружены для 215 тем; сбор остановлен, потому что отобранный пул уже покрывал нужные категории, а оставшиеся темы не добавляли новых типов проблем. Это не полная выборка всех 600 тем.
- Для набора отобраны 20 тем. `comments_count` = `posts_count - 1`; лайки не используются как голоса, `score` = `null`.

### GitHub

Использован GitHub Search API по issues.

- 12 общих запросов: `"unused packages"`, `"unused dependencies" apt`, `"orphaned packages"`, `"dependency graph" package manager`, `"visualize dependencies"`, `"reverse dependencies"`, `"remove unused packages"`, `"autoremove" package`, `"dependency tree" apt`, `"disk space" packages linux`, `"package cleanup" linux`, `"unused" "package manager" linux`.
- 9 запросов по репозиториям: `debian/apt`, `archlinux/pacman`, `rpm-software-management/dnf5`, `volian/nala`, `oguzhaninan/Stacer`, `bleachbit/bleachbit`, `Jguer/yay`, `Morganamilo/paru`.
- После дедупликации — 779 issue. Для набора отобраны 20 issue из `dnf5` (5), `paru` (5), `bleachbit` (4), `Stacer` (2), `mintupdate` (1), `synaptic` (1), `unattended-upgrades` (1), `yay` (1).
- Реакции GitHub не приравнивались к голосам: `score` = `null`, `comments_count` = число комментариев issue.

### Arch Linux Forums

Использован публичный поиск FluxBB и обычные страницы тем. Поиск на форуме ограничен: между запросами требуется не менее 60 секунд.

- 6 запросов только по заголовкам: `unused`, `orphan`, `dependency`, `autoremove`, `disk space`, `clean`, с паузой 65 секунд.
- Получено 140 уникальных тем; после просмотра отобраны 6, непосредственно относящихся к зависимостям, orphan-пакетам и безопасному обновлению.
- Поиск FluxBB даёт широкие совпадения, поэтому автоматическая выдача содержала много тем о железе и сборке; они не включались. `score` = `null`, `comments_count` = `replies`.

### Debian User Forums

Попытка получить публичную выдачу не удалась: сайт возвращал JS-заглушку `Loading...` (около 1 233 байт) вместо результатов. Обход анти-бот-защиты не выполнялся, площадка исключена. Это ограничение зафиксировано в журнале.

## Принципы отбора

- Включались публикации, где автор описывает свою проблему, задаёт вопрос или предлагает изменение; приоритет — пользовательским обсуждениям, а не рекламе и анонсам.
- Удалённые и скрытые посты Reddit исключены; для остальных проверялась доступность URL.
- Саморекламные посты Reddit `1ujnn4j` (анонс инструмента) и `1r4t6jc` (анонс собственного TUI) не включены.
- Анонсы сопровождения пакетов и обсуждения maintainer-orphan не смешивались с пользовательской очисткой.
- Дубликаты по URL отсутствуют. Одинаковые заголовки на разных площадках — разные публикации.
- Evidence — дословная цитата из тела или заголовка; проверяется скриптом сборки.

## Ограничения

- Это не вероятностная и не репрезентативная выборка. По ней нельзя оценивать распространённость проблем среди пользователей Linux.
- Reddit представлен только тремя сабреддитами; другие тематические сообщества и неанглоязычные площадки не покрыты.
- Stack Exchange и Reddit дают рейтинги, но их семантика разная; GitHub, Fedora и Arch не имеют сопоставимого рейтинга. Метрики вовлечённости несравнимы между площадками.
- Для Fedora загружены детали не всех найденных тем; для Arch поисковая выдача была широкой и дала небольшую итоговую выборку.
- GitHub Search API без токена имеет жёсткий лимит; после его исчерпания дополнительные запросы не выполнялись.
- Reddit-метрики — снимок архива, а не live-значения; они могут отличаться от текущих.
- Публикации выражают мнения авторов; набор не подтверждает и не опровергает востребованность какого-либо продукта.
