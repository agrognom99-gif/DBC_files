# WMVx: read-only аудит исходного кода для визуальной проверки T11

Дата: 2026-10-20. Цель — оценить применимость WoW Model Viewer X (WMVx) к визуальному аудиту 19 T11-комплектов, без запуска или сборки программы и без открытия игровых ресурсов WMVx.

Оценки ниже относятся к проверенному публичному коду и документации. **CONFIRMED означает, что механизм виден в исходнике, но не означает, что его работа уже подтверждена запуском на нашем клиенте.** Build 12340 не тестировался.

## 1. Краткий вывод

WMVx — функционально сильный кандидат для предварительной визуальной проверки T11: в ветке `main` есть legacy MPQ файловая система, профиль WotLK, определения `Item.dbc` и `ItemDisplayInfo.dbc`, диалог предметов с поиском по числовому Item ID и выбором DisplayID, а также код preview/equip на модели персонажа. `CharacterControl` применяет соответствующие записи через `ModelHelper`, модельные attachments, заменяемые текстуры и обновление экипировки.

Это не только просмотр M2 по имени файла. По коду предусмотрен путь «выбранный item DBC record → выбранный DisplayID → запись ItemDisplayInfo → модель/текстуры и preview в слоте персонажа». Однако заявленный кодовый путь ещё нужно подтвердить одним практическим тестом на клиенте build 12340. WMVx не следует считать точным визуальным эталоном: в README перечислены проблемы WotLK с текстурной анимацией и прозрачностью. Распознавание конкретной расы/пола в поиске текстур было исправлено только в последних коммитах main после актуального релиза v0.5.2.

**Рекомендация:** оставить WMVx основным кандидатом для контролируемого теста одного предмета, но перед запуском зафиксировать/получить именно проверяемую сборку, соответствующую выбранному исходному commit. Не использовать его результат как подтверждение прозрачности или тонких эффектов без сверки в клиенте. Текущая задача не разрешает получать, собирать или запускать программу.

## 2. Источник и версия исходников

Официальный upstream, указанный здесь: [Frostshake/WMVx](https://github.com/Frostshake/WMVx). Публичная ветка — `main`. В доступной истории последний видимый commit: `90a4d9e7d4fffb4af483f2fe5d11489ae1d5d42c`, сообщение “Fix item/model texture lookup ignoring gender/race fields.” [Commit](https://github.com/Frostshake/WMVx/commit/90a4d9e7d4fffb4af483f2fe5d11489ae1d5d42c).

Последний опубликованный релиз на странице Releases — `v0.5.2`, тег/коммит `dc4634d`; в странице релиза указано, что после него в `main` есть два коммита. Значит, бинарник релиза не подтверждён как эквивалент текущему `main`, в частности он может не содержать исправление поиска текстур по расе/полу. [Releases](https://github.com/Frostshake/WMVx/releases), [релиз v0.5.2](https://github.com/Frostshake/WMVx/releases/tag/v0.5.2).

В локальном окружении проверены ожидаемые места внутри серверного проекта, каталога аудита и клиента: локального каталога WMVx/git checkout не обнаружено. Поэтому локальный branch/status/hash и незакоммиченные изменения зафиксировать нельзя. Исследованы публичные исходные файлы/страницы upstream по HTTPS; ничего не клонировано и не скачано как файл. Ссылки в этом отчёте привязаны к commit `90a4d9e7…` там, где это возможно.

## 3. Совместимость с WotLK 3.3.5a / build 12340

README перечисляет WotLK `3.3.5` в поддерживаемых профилях. Это заявление проекта о поддержке версии эпохи, а не доказательство любой сборки клиента.

В исходнике [`WOTLKDefinitions.h`](https://github.com/Frostshake/WMVx/blob/90a4d9e7d4fffb4af483f2fe5d11489ae1d5d42c/src/core/database/WOTLKDefinitions.h) есть комментарий “Created via WDBReader schema_gen (client 3.3.5.12340)” и типы WotLK Item/ItemDisplayInfo. Это прямое свидетельство, что схема DBC ориентирована на build `3.3.5.12340`. `WOTLKDatasets.h` создаёт legacy DBC datasets с `DBCVersion::BC_WOTLK`; `WOTLKGameDatabase::load()` открывает WotLK DBFilesClient через MPQ filesystem.

Вывод: **структурная совместимость DBC с build 12340 подтверждена исходником; фактическая загрузка данного клиентского каталога и полная runtime-совместимость build 12340 — UNVERIFIED до теста.** Наличие schema profile не гарантирует правильный порядок архивов, успешную загрузку каждого файла или корректный render всех эффектов.

## 4. Чтение MPQ и DBC

### Архивы

- `src/core/filesystem/MPQFilesystem.cpp`, `MPQFileSystem::MPQFileSystem`, `MPQFileSystem::openFile`, `MPQFileSystem::fileList`: конструктор вызывает `WDBReader::Filesystem::discoverMPQArchives(root)`, создаёт `MPQFilesystem`, `openFile()` открывает внутренний архивный ресурс по path URI и возвращает reader wrapper. Это чтение непосредственно из MPQ, не предварительное извлечение. Список файлов берётся из `(listfile)` каждого MPQ с использованием StormLib API `SFileOpenFileEx`.
- `src/core/filesystem/MPQFileSystem.h` объявляет отдельную filesystem-реализацию. Соседняя `CascFileSystem` показывает, что WMVx имеет отдельный CASC backend; WotLK профиль использует MPQ backend.
- README/Users guide описывает выбор директории клиента. Указание WotLK и наличие `WOTLKGameDatabase` подтверждают разделение legacy-пути от современных профилей. Точный runtime-профиль для нашей установки не проверен.

### DBC

`src/core/database/WOTLKDefinitions.h` описывает WotLK-поля (schema):

- `ItemRecord`: `id`, `classId`, `subclassId`, `displayInfoId`, `inventoryType`, `sheatheType` и др.; `static_assert` сверяет destination record size с описанной схемой.
- `ItemDisplayInfoRecord`: `id`, `modelName[2]`, `modelTexture[2]`, `inventoryIcon[2]`, `geosetGroup[3]`, `helmetGeosetVisId[2]`, `texture[8]`, `itemVisualId` и др.

`WOTLKDatasets.h`: `WOTLKItemDataset` напрямую открывает `DBFilesClient\\Item.dbc`, вызывает WDBReader `makeDBCFile(...BC_WOTLK)`, загружает записи и помещает их в dataset. Там же объявлен `WOTLKItemDisplayInfoDataset` на legacy DBC reader.

`WOTLKGameDatabase.h`, `WOTLKGameDatabase::load()`: подключает `Item.dbc`, `ItemDisplayInfo.dbc`, `ItemVisuals.dbc`, `ItemVisualEffects.dbc` и остальные базы из `DBFilesClient\\...`. Это не серверная MySQL база; WMVx читает клиентские DBC.

Класс `ItemSet.dbc` в перечисленных WotLK datasets/database load не обнаружен. Поэтому поиск/фильтр по игровому комплекту ItemSet WMVx, судя по проверенной схеме, не предоставляет. Состав T4/T5-наборов для аудита следует брать из уже проверенного DBC-каталога отдельно.

## 5. Поиск предметов по Item ID / DisplayID

`src/core/database/WOTLKDatasetAdaptors.h`, `WOTLKItemRecordAdaptor::getId()` и `getItemDisplayInfoId()` возвращают соответственно `Item.dbc.id` и `Item.dbc.displayInfoId`; `getInventorySlotId()` возвращает `inventoryType`. В том же файле WotLK ItemDisplayInfo привязан к `GenericLegacyDBCItemDisplayInfoRecordAdaptor`.

`src/EquipmentChoiceDialog.cpp`, `EquipmentChoiceDialog`:

1. Числовая строка преобразуется в `uint32_t`; фильтр сравнивает её с `item_data.first` — внутренним item ID (строки 21–46). Следовательно, диалог умеет искать именно по **Item ID**, не только по названию.
2. После выбора item записи `getItemDisplayInfoId()` заполняет DisplayID combo (строки 94–109).
3. Выбранная запись находится через `itemsDB->findById(...)`, DisplayID передаётся в `CharacterItemWrapper::make(...)`; смена DisplayID вызывает preview (строки 64–72, 111–120).
4. Список заполняется предметами, совместимыми с выбранным слотом персонажа (`Mapping::CharacterSlotItemInventory`), а метка имеет формат «название [ID]» (строки 126–149).

Таким образом, DisplayID является выбираемым вариантом **после** выбора Item ID. В проверенном диалоге отдельного глобального поиска только по DisplayID не видно. `ItemSet ID` также не является источником поиска.

### Контрольный Netherblade Facemask

Кодовый маршрут, необходимый для теста, реализован: в слоте Head выполнить точный поиск ID `29044`; adaptor получает поле `displayInfoId` из DBC; combo показывает это значение; при выборе вызывается preview wrapper для того же item и display. WotLK database loader включает `ItemDisplayInfo.dbc`, schema включает модельные и текстурные поля.

Но значение конкретной строки `Item.dbc[29044].displayInfoId == 45810` и наличие соответствующей записи `ItemDisplayInfo.dbc[45810]` в WMVx runtime **не читались и не тестировались в этом задании**. Поэтому:

- возможность пройти ID → DisplayID по коду: **CONFIRMED**;
- фактическое соответствие `29044 → 45810` в указанном клиенте: **UNVERIFIED** (значения предоставлены контрольными данными аудита);
- фактический render предмета: **UNVERIFIED**.

Названия/quality для элементов списка берутся из reference CSV `Support Files\\wotlk\\items.csv` в `WOTLKGameDatabase::load()` / `WOTLKItemDataset`. `WOTLKItemRecordAdaptor::getName()` возвращает `Unknown (Missing Name)` при отсутствии reference-строки, но item ID/DBC record остаётся в dataset. Поэтому тест по числовому ID менее зависим от покрытия CSV, чем поиск по имени.

## 6. Отображение отдельной модели и текстур

### Предмет через DBC

`ItemDisplayInfoRecord` содержит имена моделей и модельных текстур, а также восемь texture-компонентов и geoset/helmet значения. Диалог выбранный DisplayID оборачивает в `CharacterItemWrapper`. `CharacterControl::updateItem(CharacterSlot, wrapper)` передаёт его в `ModelHelper(...).addItem(...)`; callback получает `item_vis_id` и пытается разрешить ItemVisuals. Это подтверждает item-context preview, а не только просмотр произвольного файла.

`src/core/modeling/AttachmentCustomization.cpp`, `StandardAttachmentCustomizationProvider::makeAttachment()` вызывает `modelFactory(gameFS, model_file)`, загружает модельные текстуры `tex_info`, animation/geoset данные, загружает выбранную текстуру и добавляет attachment к родительской модели. Для merged slots `MergedAwareAttachmentCustomizationProvider` формирует `MergedModel` по DisplayID/slot/позиции. Это относится к визуализации на модели персонажа.

### Отдельный M2-файл

WMVx содержит `ModelControl`/`ModelControl.ui`, файл-лист и `M2.cpp`; документация указывает M2 loading и Browse assets. Поэтому просмотр отдельного M2 из файла/архива доступен как отдельная операция. Если модель открыта только по имени файла в библиотеке, такой просмотр сам по себе не доказывает, что она связана с Item ID/DisplayID или что выбран правильный texture variant. Для T11 существенно полезнее item-dialog preview, так как он применяет display-данные в контексте персонажа.

### Материалы, прозрачность и точность

`ModelSupport.cpp::ModelTextureInfo::loadTexture()` загружает текстуры по filename URI через TextureManager, а специальные типы текстур оставляет как special texture type. `M2.cpp`, `Texture.cpp`, `ModelRenderPassRenderer.cpp` содержат разбор M2/текстур/рендер-проходов; наличие этих частей подтверждает render pipeline, но не идеальное соответствие WoW-клиенту для каждого эффекта.

В README проекта в блоке known issues отдельно указаны WotLK texture animations, которые не показываются, и некорректная прозрачность текстур (пример boar). Это ограничения документации проекта, а не собственный visual test. Следовательно, видимые контуры/цвета могут быть полезны, но корректность альфа-слоёв и анимированных текстур для T11 не считать подтверждённой.

## 7. Экипировка персонажа и geosets

### Реализовано кодом

- `CharacterControl` выбирает/создаёт персонажа; race/gender содержатся в CharacterDetails и используются для model/texture search. WotLK database загружает `ChrRaces`, `CharSections`, `CharacterFacialHairStyles`, `CharHairGeosets`.
- `EquipmentChoiceDialog` создаётся для `CharacterSlot`, отфильтровывает ItemInventoryType для этого слота, затем запускает live preview.
- `CharacterControl::openChoiceDialog`, `updateEquipment`, `updateItem` сохраняют несколько предметов в `model->characterEquipment` и перебирают все записи при обновлении; значит полный комплект можно собирать одновременно.
- `CharacterSlot::HEAD`/`SHOULDER` используют attachment positions (шлем и обе стороны плеч); `CHEST`, `GLOVES`, `PANTS` используют merged model путь (`MergedAwareAttachmentCustomizationProvider`). У WMVx есть `GeosetState::init`, `visible`, `setVisibility`, `clearVisibility` в `Geoset.cpp`.
- WotLK ItemDisplayInfo schema несёт `geosetGroup[3]` и `helmetGeosetVisId[2]`, код attachment инициирует geoset data, а CharacterControl пропускает display attachment и visual effects.

Это подтверждает, что WMVx не ограничен одиночными M2 и имеет структуру для экипировки персонажа и обработки geosets.

### Что ещё не подтверждено

Правильность конечного результата для конкретной модели/расы/пола/слота, соответствие каждого значения geoset правилам клиента, скрытие волос под конкретным шлемом и итоговый комплект не проверялись запуском. Текущий main commit `90a4d9e` именно исправляет ранее игнорировавшиеся race/gender поля при поиске текстур. Это важная причина зафиксировать commit и не переносить выводы на старый релиз без проверки.

## 8. Зависимости и безопасная сборка

`CMakeLists.txt` и `Docs/technical.md` указывают CMake, C++20, Visual Studio 2022, Qt 6.5, FBX SDK 2020.3.4, а также CascLib, StormLib, GLEW, glm, WDBReader и fast-cpp-csv-parser; сборочный процесс использует vcpkg. Файл проекта требует Qt6/OpenGL и линкует CascLib, StormLib, WDBReader. Сборка не выполнялась.

Описанный preset имеет `binaryDir` внутри `${sourceDir}/build` и `CMAKE_INSTALL_PREFIX` `./install`. Следовательно, default-рецепт может писать в checkout; технически внешний CMake build dir возможен, но его конфигурацию здесь не проверяли. Не запускать default build в имеющемся checkout без отдельного плана изоляции.

Пути runtime-записи по доступному коду/инструкциям:

- `WMVxSettings::fileName()` возвращает `QDir::currentPath() + "/settings.ini"` — запись настроек идёт относительно current working directory.
- User guide указывает, что `wmvx.log` находится в каталоге, откуда запущено приложение.
- Проект поддерживает сохранение сцен, экспорт изображений и FBX; пользовательский выбор путей вывода будет создавать файлы.
- Документы/исходник указывают `Support Files` и reference CSV. Точное поведение обновления support-файлов, полный список создаваемых кэшей/директорий и гарантии «не писать в клиент» не подтверждены статическим проходом.

Изолированный рабочий каталог вне WoW-клиента и сервера выглядит выполнимым, но не является гарантией: надо проверить все file writes. Открытие MPQ read path в исходнике само по себе не доказывает отсутствие других записей. Запуск и проверка путей записи запрещены в текущей задаче.

## 9. Ограничения и риски

1. Нет локального исходного checkout, поэтому branch/hash/status фиксируются только по публичному GitHub, а не по рабочей копии.
2. Текущий `main` и latest release различаются: два commit после v0.5.2; стабильный release может не включать правку race/gender texture lookup.
3. Точный build 12340 указан в генерационном комментарии DBC schema, но фактическое чтение файлов конкретной клиентской установки не проверялось.
4. WotLK-известные проблемы: текстурная анимация и прозрачность. Учитывать при оценке цветов, alpha, свечения и анимированных эффектов.
5. ItemSet.dbc не подключён к WotLK game database в проверенной реализации. WMVx — не источник правды для принадлежности исходного предмета к T4/T5 set.
6. Полное отображение комплекта реализовано структурно, но визуальная корректность каждой комбинации и каждой расы/пола остаётся предметом ручной проверки.
7. Нет гарантии безопасности произвольного бинарника или его read-only поведения без проверки происхождения/хешей и файловых операций.
8. Этот аудит не открывал локальные MPQ/DBC через WMVx, не скачивал/собирал/запускал программу и не менял клиент/сервер.

## 10. Таблица статусов и доказательств

| Механизм | Статус | Доказательство | Ограничение |
|---|---|---|---|
| WotLK профиль и schema build 12340 | **CONFIRMED** (для schema/profile кода) | `WOTLKDefinitions.h` — комментарий client 3.3.5.12340; `WOTLKGameDatabase::load()`; `WOTLKDatasets.h` | Runtime с клиентом не проверен |
| Чтение файлов напрямую из legacy MPQ | **CONFIRMED** | `MPQFileSystem::MPQFileSystem`, `openFile`, `fileList`; WDBReader MPQ FS + StormLib listfile path | Полная archive order/locale для клиента не тестировалась |
| Чтение Item.dbc и ItemDisplayInfo.dbc для WotLK | **CONFIRMED** | `WOTLKItemDataset`, `WOTLKItemDisplayInfoDataset`; `WOTLKGameDatabase::load()` | Успешность открытия конкретных файлов не тестировалась |
| Item ID поиск | **CONFIRMED** | `EquipmentChoiceDialog`: сравнение числового запроса с `item_data.first` | Имя зависит от support CSV; ID-поиск сохраняется при unknown name |
| DisplayID выбор по item | **CONFIRMED** | `itemClicked` добавляет `getItemDisplayInfoId()` в combo; `CharacterItemWrapper::make` получает выбранный ID | Отдельного глобального DisplayID search в диалоге нет |
| Конкретная связка `29044 → 45810` | **UNVERIFIED** фактические значения / **CONFIRMED** механизм | DBC adaptor переносит `displayInfoId`; UI путь Item→Display→preview | Значения не перечитаны в этой задаче, WMVx не запускался |
| DisplayInfo → имя M2/текстура | **CONFIRMED** на уровне record schema и item-preview pipeline | `ItemDisplayInfoRecord` в `WOTLKDefinitions.h`; adaptor alias; `AttachmentCustomization.cpp::makeAttachment`; `CharacterControl::updateItem` | Алгоритм подстановки каждого поля/модельного варианта не визуально протестирован |
| Standalone просмотр произвольного M2 | **CONFIRMED** как viewer-функция | `ModelControl`, `M2.cpp`, file browser/model display UI | Не подтверждает item-to-display связь |
| Надевание предметов на персонажа | **CONFIRMED** как реализованная функция | `EquipmentChoiceDialog`; `CharacterControl::openChoiceDialog`, `updateEquipment`, `updateItem` | Для конкретного клиента/предмета runtime-результат UNVERIFIED |
| Race/gender и компоненты тела | **CONFIRMED** как кодовый путь | WotLK race/section DB; `CharacterControl`; commit `90a4d9e` исправляет context в item texture lookup | Исправление в текущей ветке может отсутствовать в release v0.5.2 |
| Geosets / helmet visibility | **PARTIAL** | WotLK schema fields; `Geoset.cpp::GeosetState`; item attachment initialization/merged path | Нужны тестирование конкретной семантики и визуальная сверка с игрой |
| Текстуры M2 | **CONFIRMED** для загрузочного pipeline; **PARTIAL** для fidelity | `ModelSupport.cpp::loadTexture`, `Texture.cpp`, M2 renderer | Текстурная анимация/прозрачность WotLK имеют known issues |
| Полный комплект в одном preview | **CONFIRMED** как возможность интерфейса/модели | `model->characterEquipment`, `updateEquipment()` и слотные `updateItem()` | Финальная посадка комплекта не проверена |
| Нет MPQ extraction при обычном чтении | **PARTIAL** | `MPQFileSystem` открывает/читает resource stream; extraction/export — отдельные функции UI | Нельзя гарантировать отсутствие любых записей всего приложения без наблюдения |
| Безопасное размещение runtime-файлов | **PARTIAL** | settings от current working directory; log рядом с запуском | Все runtime-каталоги и write paths нужно контролировать отдельно |

## 11. Рекомендация для аудита T11

WMVx пригоден для следующего согласованного этапа как инструмент **просмотра кандидатов на персонаже по Item ID и выбранному DisplayID**, а не только для просмотра свободных M2. Сначала нужно определить, какой проверяемый артефакт будем использовать: последний релиз v0.5.2 или источник commit `90a4d9e…`; эти варианты не эквивалентны по опубликованной истории. Затем — отдельное разрешение на получение/сборку/запуск, изолированный рабочий каталог, фиксация хешей клиента и наблюдение за записями.

Для контрольного item проверить в UI числовой ID 29044, слот Head, DisplayID 45810, загрузку модели/текстур и geoset на выбранной race/gender. Отдельно проверить оставшиеся T11-слоты и полный комплект. Прозрачность/анимацию сверять в клиенте: WMVx README заранее сообщает о WotLK limitations. До такого теста все visual registry статусы остаются UNVERIFIED.