# Источники и методы аудита

- Клиент: `E:\Games\WoW_3.3.5_12340`; версия `Wow.exe`: 3.3.5.12340 (file metadata).
- Основной набор DBC: `E:\Games\WoW_3.3.5_12340\dbc`. Обрабатывались только файлы из корня этого каталога.
- Сервер: `C:\WOWServer 3.3.5\azerothcore-wotlk`; записи item_template взяты чтением файла `C:\WOWServer 3.3.5\azerothcore-wotlk\data\sql\base\db_world\item_template.sql`. SQL не исполнялся, база не открывалась.
- Результаты: `C:\WOWServer 3.3.5\T11-Audit`. Read-only helper: `dbc_audit.py` (только читает исходники; пишет четыре отчётных файла).

## Корневые DBC

| Файл | Байты | SHA-256 | Формат | Записей | Полей | Размер записи | Строковый блок |
|---|---:|---|---|---:|---:|---:|---:|
| `Item.dbc` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` | WDBC | 46096 | 8 | 32 | 1 |
| `ItemDisplayInfo.dbc` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` | WDBC | 57986 | 25 | 100 | 934207 |
| `ItemSet.dbc` | 118552 | `28c285ea7cab86b74c06ad30138c62c26d5ea5303f1fd2bccb9b3285a95d3467` | WDBC | 509 | 53 | 212 | 10624 |
| `ItemVisuals.dbc` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` | WDBC | 80 | 6 | 24 | 1 |
| `ItemSubClass.dbc` | 22190 | `ed037619b6277fb2b05c3cf05233b19687a4004427d5e63a12d038804bc8b0e5` | WDBC | 119 | 44 | 176 | 1226 |
| `ItemClass.dbc` | 1538 | `f14b09254010765ab75c3c04ddf55a4b03e75163655c5015d188b04e31fa1b20` | WDBC | 17 | 20 | 80 | 158 |

Все шесть файлов имеют magic `WDBC`; для каждого выполнено `20 + record_count × record_size + string_block_size == file_size`, и `field_count × 4 == record_size`. Поля в DBC хранятся по 4 байта; строковые поля указывают смещение в таблицу строк.

## Подтверждённые структуры/сопоставления

- `Item.dbc`: `Itemfmt = niiiiiii` и `ItemEntry` в `src/server/shared/DataStores/DBCfmt.h` / `DBCStructure.h`: поля 0–7 это ID, ClassID, SubclassID, SoundOverrideSubclassID, Material, DisplayInfoID, InventoryType, SheatheType.
- `ItemDisplayInfo.dbc`: 25 полей по заголовку; порядок проверен по `itemdisplayinfo_dbc.sql` (ID, имена модели, модельные текстуры, иконки, геосеты, флаги, визуальные поля и текстуры). Core format `ItemDisplayTemplateEntryfmt` использует ID и поле иконки, игнорируя большинство визуальных полей; CSV декодирует строковые смещения по порядку DDL, поэтому визуальные поля — сырые данные DBC, не подтверждённый просмотр.
- `ItemSet.dbc`: `ItemSetEntryfmt` и `ItemSetEntry`: ID в поле 0, имя enUS в поле 1, ruRU в поле 12, членство в полях 18–34 (ItemID_1..17 per `itemset_dbc.sql`). Поля 28–34 закомментированы в `ItemSetEntry` текущего AC, но их смысл как ItemID_11..17 подтверждается SQL schema; аудит декодирует их как client DBC data.
- Связь предмет→display: `Item.dbc` поле `ID` (0) → `DisplayInfoID` (5) → `ItemDisplayInfo.dbc` поле `ID` (0). Название и ItemLevel извлечены по `entry` из записей файла `item_template.sql`; отдельно сохранено сравнение его `displayid` с DBC.
- Связь комплект→предмет: ID из `ItemSet.dbc` полей 18–34 сопоставлены с `Item.dbc.ID`, затем с `item_template.entry`. `ItemSet` не хранит отдельный слот для каждого ID; слот берётся из `Item.dbc.InventoryType` (сверен с `item_template.InventoryType`).
- `ItemVisuals.dbc`, `ItemSubClass.dbc`, `ItemClass.dbc`: заголовки/размеры/строки проверены. Для этих таблиц в доступном AC коде не обнаружено достаточного названного полного layout, поэтому они не используются для неподтверждённых связей; class/subclass в каталоге оставлены числовыми значениями Item.dbc.

## Локализованные и архивные копии

Ниже отдельно перечислены доступные копии; они не смешивались с корневым набором:

| DBC | Каталог | Байты | SHA-256 |
|---|---|---:|---|
| `Item.dbc` | `Archive_dbc` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `deDE` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `enCN` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `enUS` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `esES` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `esMX` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `frFR` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `koKR` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `ruRU` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `zhCN` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `Item.dbc` | `zhTW` | 1475093 | `d455bc30b59bc368b2a972a913864dd092d50695140b9513582100dc56ed777d` |
| `ItemDisplayInfo.dbc` | `Archive_dbc` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `deDE` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `enCN` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `enUS` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `esES` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `esMX` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `frFR` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `koKR` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `ruRU` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `zhCN` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemDisplayInfo.dbc` | `zhTW` | 6732827 | `42d2c67fb12cb79e1e62fee2839f5f8f8239abe4ecfd45ed6fee1021642d19bc` |
| `ItemSet.dbc` | `Archive_dbc` | 128112 | `cd04572e81868e716661ab0bb93b4c80be886284294be8bf8e368a4802aa9c89` |
| `ItemSet.dbc` | `deDE` | 121590 | `504c0778cb012cfe55ce3d6f1d87b90a57fc8b0afefb596fd7ad3d192553cb45` |
| `ItemSet.dbc` | `enCN` | 116093 | `ca290f7d828e859c2816421b4631cc5caad224f18a2e1e7ae74005a01c0bf50f` |
| `ItemSet.dbc` | `enUS` | 118552 | `28c285ea7cab86b74c06ad30138c62c26d5ea5303f1fd2bccb9b3285a95d3467` |
| `ItemSet.dbc` | `esES` | 121616 | `63affb90ea8ebc7527d028755b5f68c5042ae76833feeca901e99f26acdd331a` |
| `ItemSet.dbc` | `esMX` | 121616 | `2729d92706f926a7752d54c72f61b624d51355a33692c430b43ee42a3cf03c33` |
| `ItemSet.dbc` | `frFR` | 121851 | `50a9fbe4beebb5cd737e352d1929e69ae9a0503d489ce9128a04c5c9bd078277` |
| `ItemSet.dbc` | `koKR` | 120077 | `ab58d9293f7231f7e25566d76a079af6c0e4a1e74dbf4b6f4244dc2cc867ec03` |
| `ItemSet.dbc` | `zhCN` | 116093 | `ca290f7d828e859c2816421b4631cc5caad224f18a2e1e7ae74005a01c0bf50f` |
| `ItemSet.dbc` | `zhTW` | 116920 | `30a8d713917af475b761e00049b6383a51c806f0258dc2b11745199677bf8653` |
| `ItemVisuals.dbc` | `deDE` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemVisuals.dbc` | `enCN` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemVisuals.dbc` | `enUS` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemVisuals.dbc` | `esES` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemVisuals.dbc` | `esMX` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemVisuals.dbc` | `frFR` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemVisuals.dbc` | `koKR` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemVisuals.dbc` | `ruRU` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemVisuals.dbc` | `zhCN` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemVisuals.dbc` | `zhTW` | 1941 | `d2af5a29c78b10a3a366641de2785c15cb093d5e5f46fc740772a29b90164091` |
| `ItemSubClass.dbc` | `deDE` | 22399 | `a6069908c942c0ca3f017405d52634fa32c8b3712fc12938e6a6a5eda695f8bb` |
| `ItemSubClass.dbc` | `enCN` | 21951 | `ffcc738cda4bcc76851bf16d5113f2934be6e31f1d91d9074afa1fc3aca7eba0` |
| `ItemSubClass.dbc` | `enUS` | 22190 | `ed037619b6277fb2b05c3cf05233b19687a4004427d5e63a12d038804bc8b0e5` |
| `ItemSubClass.dbc` | `esES` | 22467 | `66e7c5f323b1d802aa3f047ab05a0ba4879c6759eba0ca33deed5ff0a9778720` |
| `ItemSubClass.dbc` | `esMX` | 22467 | `0d3666eda14afa54a80042a6e669c532c0ca323414e0dad004e645cf6effed98` |
| `ItemSubClass.dbc` | `frFR` | 22413 | `327ea07871eeb49b7f1f369d78255f799adb7143d3973a614e3df38cead52c6a` |
| `ItemSubClass.dbc` | `koKR` | 22383 | `16fcdf376aede92bab814ff4975bbec9fb462099c77accd7ea15bbe7a270f2e1` |
| `ItemSubClass.dbc` | `ruRU` | 23511 | `d1c44b19eb3ecedb6d5e563287d932c1a42f57add4b9a6474d85e5489bd01752` |
| `ItemSubClass.dbc` | `zhCN` | 21951 | `ffcc738cda4bcc76851bf16d5113f2934be6e31f1d91d9074afa1fc3aca7eba0` |
| `ItemSubClass.dbc` | `zhTW` | 22017 | `8b8229b5d530eb7af6c3974fd2adc236336710042cfde391e73f5760986aa200` |
| `ItemClass.dbc` | `deDE` | 1564 | `e3de24d5c4274bf7bb0d366cbbb07976a19816e4721ce9c693ffa854f7c6ff5c` |
| `ItemClass.dbc` | `enCN` | 1523 | `a955e8c2335623705dd9eb7bdc59ade7f4803918ce9804069f4964ce85ed854c` |
| `ItemClass.dbc` | `enUS` | 1538 | `f14b09254010765ab75c3c04ddf55a4b03e75163655c5015d188b04e31fa1b20` |
| `ItemClass.dbc` | `esES` | 1558 | `7030d2b1c69a42db4907afb0ca3662cd3d9d1582bce7a31aad91c830b0ba4353` |
| `ItemClass.dbc` | `esMX` | 1558 | `11bea562dc2c352f3405ca9ce051a8163d6bb7b25c4d17568ea5baadd9d67b88` |
| `ItemClass.dbc` | `frFR` | 1544 | `a6478512d3a06d0cdad74667bed56dfe6962efc5a5abc4903197e41232da733c` |
| `ItemClass.dbc` | `koKR` | 1524 | `fa3bf951cc76cb6edb27cfdc4fc906658ea16bc0616de28ae15d3708c42564db` |
| `ItemClass.dbc` | `ruRU` | 1711 | `dacd64db07db0e22275c11bd1605a64c67e9f3570fcf69a831da248bb65fd601` |
| `ItemClass.dbc` | `zhCN` | 1523 | `a955e8c2335623705dd9eb7bdc59ade7f4803918ce9804069f4964ce85ed854c` |
| `ItemClass.dbc` | `zhTW` | 1519 | `c782e0aaeeeb1a2386e00c68f10eb97aa421a9636695ed3861e29f721bfd6fc1` |

## Ограничения

- `visual_candidates.csv` использует реальные члены T4/T5, найденные по именам семейств и ID-членам ItemSet. Категоризация T4/T5 — классификация по семействам названий, не самостоятельная игровая проверка.
- Локальные модели/текстуры отмечаются только при точном совпадении относительного пути или уникальном совпадении basename с распакованным `.m2`/`.blp`; неоднозначные совпадения не подтверждаются. MPQ не читались, не извлекались.
- По DBC и путям нельзя подтвердить внешний вид, комплектность на персонаже или совпадение визуальных моделей; все такие проверки имеют статус «не проверено».
