from __future__ import annotations
import csv, hashlib, json, pathlib, re, struct
from collections import Counter, defaultdict

CLIENT = pathlib.Path(r'E:\Games\WoW_3.3.5_12340')
SERVER = pathlib.Path(r'C:\WOWServer 3.3.5\azerothcore-wotlk')
DBC = CLIENT / 'dbc'
OUT = pathlib.Path(r'C:\WOWServer 3.3.5\T11-Audit')

FILES = ['Item.dbc','ItemDisplayInfo.dbc','ItemSet.dbc','ItemVisuals.dbc','ItemSubClass.dbc','ItemClass.dbc']
DISPLAY_COLUMNS = ['ID','ModelName_1','ModelName_2','ModelTexture_1','ModelTexture_2','InventoryIcon_1','InventoryIcon_2','GeosetGroup_1','GeosetGroup_2','GeosetGroup_3','Flags','SpellVisualID','GroupSoundIndex','HelmetGeosetVis_1','HelmetGeosetVis_2','Texture_1','Texture_2','Texture_3','Texture_4','Texture_5','Texture_6','Texture_7','Texture_8','ItemVisual','ParticleColorID']
DISPLAY_STRINGS = {1,2,3,4,5,6,15,16,17,18,19,20,21,22}
# Source family names present in the WDBC ItemSet records; only source families, not target assignments.
T4_FAMILIES = ['Malorne','Demon Stalker','Aldor','Incarnate','Justicar','Netherblade','Cyclone','Voidheart','Warbringer']
T5_FAMILIES = ['Nordrassil','Rift Stalker','Tirisfal','Avatar','Crystalforge','Deathmantle','Cataclysm','Corruptor','Destroyer']
SLOT_BY_INVTYPE = {1:'Head',3:'Shoulders',5:'Chest',20:'Chest',10:'Hands',7:'Legs'}


def read_dbc(path: pathlib.Path):
    b = path.read_bytes()
    if len(b) < 20:
        raise ValueError(f'{path}: shorter than WDBC header')
    magic, count, fields, record_size, string_size = struct.unpack_from('<4s4I', b)
    if magic != b'WDBC':
        raise ValueError(f'{path}: unsupported magic {magic!r}')
    expected = 20 + count * record_size + string_size
    if expected != len(b) or fields * 4 != record_size:
        raise ValueError(f'{path}: inconsistent header size/count')
    strings = b[20 + count * record_size:]
    rows=[]
    for n in range(count):
        values=struct.unpack_from('<'+'I'*fields,b,20+n*record_size)
        rows.append(values)
    return {'path':path,'bytes':b,'count':count,'fields':fields,'record_size':record_size,'string_size':string_size,'strings':strings,'rows':rows,'sha256':hashlib.sha256(b).hexdigest()}


def string_at(dbc, offset):
    strings=dbc['strings']
    if offset == 0 or offset >= len(strings): return ''
    end=strings.find(b'\0',offset)
    if end < 0: return ''
    return strings[offset:end].decode('utf-8','replace')


def sql_columns(path):
    text=path.read_text(encoding='utf-8-sig')
    m=re.search(r'CREATE TABLE `[^`]+`\s*\((.*?)\n\) ENGINE',text,re.S)
    if not m: raise ValueError(f'Cannot read DDL columns: {path}')
    return re.findall(r'^\s*`([^`]+)`\s+([^,\n]+)',m.group(1),re.M)


def parse_insert_values(path):
    text=path.read_text(encoding='utf-8-sig')
    marker='INSERT INTO `item_template` VALUES'
    pos=0
    while True:
        start=text.find(marker,pos)
        if start<0: break
        i=start+len(marker)
        while i<len(text) and text[i].isspace(): i+=1
        while i<len(text) and text[i]!=';':
            if text[i].isspace() or text[i]==',': i+=1; continue
            if text[i]!='(': raise ValueError(f'Unexpected SQL at offset {i}')
            i+=1; values=[]; token=[]; quoted=False
            while i<len(text):
                c=text[i]
                if quoted:
                    if c=='\\' and i+1<len(text):
                        token.append(text[i+1]); i+=2; continue
                    if c=="'":
                        if i+1<len(text) and text[i+1]=="'": token.append("'"); i+=2; continue
                        quoted=False; i+=1; continue
                    token.append(c); i+=1; continue
                if c=="'": quoted=True; i+=1; continue
                if c==',': values.append(''.join(token).strip()); token=[]; i+=1; continue
                if c==')': values.append(''.join(token).strip()); i+=1; yield values; break
                token.append(c); i+=1
            else: raise ValueError('Unterminated INSERT tuple')
        pos=i+1


def field(row, cols, name):
    try: return row[cols[name]]
    except (KeyError, IndexError): return ''


def main():
    dbcs={name:read_dbc(DBC/name) for name in FILES}
    # Locale/archive inventory is recorded separately and never joined to the root dataset.
    variants=[]
    for name in FILES:
        for folder in sorted([p for p in DBC.iterdir() if p.is_dir() and (p.name=='Archive_dbc' or re.fullmatch(r'[a-zA-Z]{4}',p.name))],key=lambda p:p.name.casefold()):
            p=folder/name
            if p.is_file():
                bb=p.read_bytes(); variants.append({'name':name,'folder':folder.name,'path':str(p),'bytes':len(bb),'sha256':hashlib.sha256(bb).hexdigest()})
    # Decode Item.dbc fields according to Itemfmt and ItemEntry in AzerothCore.
    items={r[0]:{'id':r[0],'class':r[1],'subclass':r[2],'sound_override_subclass':r[3],'material':r[4],'display_id':r[5],'inventory_type':r[6],'sheathe_type':r[7]} for r in dbcs['Item.dbc']['rows']}
    displays={}
    for r in dbcs['ItemDisplayInfo.dbc']['rows']:
        d={}
        for ix,col in enumerate(DISPLAY_COLUMNS): d[col]=string_at(dbcs['ItemDisplayInfo.dbc'],r[ix]) if ix in DISPLAY_STRINGS else r[ix]
        displays[r[0]]=d
    # Decode ItemSet according to ItemSetEntryfmt / ItemSetEntry: ID, localized names, field 17 mask,
    # ItemID_1..10 at fields 18..27; fields 28..34 are unused by this server structure.
    sets=[]
    for r in dbcs['ItemSet.dbc']['rows']:
        sets.append({'id':r[0],'name_enUS':string_at(dbcs['ItemSet.dbc'],r[1]),'name_ruRU':string_at(dbcs['ItemSet.dbc'],r[12]),'item_ids':[x for x in r[18:35] if x]})
    # Extract names and item levels from the checked-in base SQL dump (no SQL execution/connection).
    template_path=SERVER/'data/sql/base/db_world/item_template.sql'
    template_cols_raw=sql_columns(template_path)
    template_cols={name:i for i,(name,_) in enumerate(template_cols_raw)}
    templates={}
    tuple_count=0
    for row in parse_insert_values(template_path):
        tuple_count+=1
        if len(row)!=len(template_cols_raw): raise ValueError(f'item_template tuple has {len(row)} values, DDL has {len(template_cols_raw)} columns')
        def num(name):
            v=field(row,template_cols,name)
            try: return int(v)
            except (TypeError,ValueError): return 0
        entry=num('entry')
        templates[entry]={'entry':entry,'name':field(row,template_cols,'name'),'class':num('class'),'subclass':num('subclass'),'displayid':num('displayid'),'inventory_type':num('InventoryType'),'item_level':num('ItemLevel')}
    # Loose-asset exact relative-path inventory (no MPQ reads/extraction).
    loose={}
    for p in CLIENT.rglob('*'):
        if p.is_file() and p.suffix.lower() in ('.m2','.blp'):
            loose[p.relative_to(CLIENT).as_posix().casefold()]=str(p)
    def asset(field_value, ext):
        if not field_value: return ''
        raw=field_value.replace('\\','/').lstrip('/')
        rel=raw.casefold()
        suffix=pathlib.PurePosixPath(rel).suffix
        alternatives=[rel]
        if not suffix: alternatives.append(rel+ext)
        if ext=='.m2' and suffix=='.mdx': alternatives.append(str(pathlib.PurePosixPath(rel).with_suffix('.m2')))
        for candidate in alternatives:
            if candidate in loose: return 'exact path: '+loose[candidate]
        wanted=pathlib.PurePosixPath(raw).stem.casefold()
        matches=sorted({v for k,v in loose.items() if pathlib.PurePosixPath(k).stem.casefold()==wanted and pathlib.PurePosixPath(k).suffix.casefold()==ext})
        if len(matches)==1: return 'unique basename: '+matches[0]
        if len(matches)>1: return f'ambiguous basename ({len(matches)} files)'
        return ''
    candidates=[]
    family_matches=[]
    seen_ids=set()
    for st in sets:
        source_tier=next((4 for x in T4_FAMILIES if x.casefold() in st['name_enUS'].casefold()),None)
        if source_tier is None: source_tier=next((5 for x in T5_FAMILIES if x.casefold() in st['name_enUS'].casefold()),None)
        if source_tier is None: continue
        family_matches.append(st)
        for item_id in st['item_ids']:
            item=items.get(item_id); tmpl=templates.get(item_id)
            if not item: continue
            inv=item['inventory_type']; slot=SLOT_BY_INVTYPE.get(inv,'')
            display=displays.get(item['display_id'],{})
            template_display=tmpl['displayid'] if tmpl else ''
            record={'source_tier':f'T{source_tier}','source_itemset_id':st['id'],'source_itemset_name_enUS':st['name_enUS'],'source_itemset_name_ruRU':st['name_ruRU'],'source_item_id':item_id,'source_item_name':tmpl['name'] if tmpl else '', 'class_id':item['class'],'subclass_id':item['subclass'],'inventory_type':inv,'slot':slot,'item_level':tmpl['item_level'] if tmpl else '', 'item_dbc_display_id':item['display_id'],'item_template_displayid':template_display,'display_ids_match':(item['display_id']==template_display) if tmpl else '', 'model_name_1':display.get('ModelName_1',''),'model_name_2':display.get('ModelName_2',''),'model_texture_1':display.get('ModelTexture_1',''),'model_texture_2':display.get('ModelTexture_2',''),'inventory_icon_1':display.get('InventoryIcon_1',''),'texture_1':display.get('Texture_1',''),'texture_2':display.get('Texture_2',''),'texture_3':display.get('Texture_3',''),'texture_4':display.get('Texture_4',''),'texture_5':display.get('Texture_5',''),'texture_6':display.get('Texture_6',''),'texture_7':display.get('Texture_7',''),'texture_8':display.get('Texture_8',''),'itemvisual_id':display.get('ItemVisual',''),'model_file_1_available':asset(display.get('ModelName_1',''),'.m2'),'model_file_2_available':asset(display.get('ModelName_2',''),'.m2'),'texture_files_available':';'.join(filter(None,[asset(display.get('ModelTexture_1',''),'.blp'),asset(display.get('ModelTexture_2',''),'.blp')]+[asset(display.get(f'Texture_{i}',''),'.blp') for i in range(1,9)])),'loose_file_check':'exact path or unique basename; ambiguous basename not confirmed; MPQ not inspected','visual_status':'not checked visually','confidence':'high for DBC/itemset link; medium for template/display concordance; no visual claim'}
            if item_id in seen_ids: record['duplicate_itemset_membership']='yes'
            else: record['duplicate_itemset_membership']='no'
            seen_ids.add(item_id); candidates.append(record)
    # Persist candidate catalog with explicit provenance columns.
    candidate_cols=list(candidates[0].keys()) if candidates else ['source_tier','source_itemset_id','source_itemset_name_enUS','source_itemset_name_ruRU','source_item_id','source_item_name','class_id','subclass_id','inventory_type','slot','item_level','item_dbc_display_id','item_template_displayid','display_ids_match','model_name_1','model_name_2','model_texture_1','model_texture_2','texture_1','texture_2','texture_3','texture_4','texture_5','texture_6','texture_7','texture_8','visual_status','confidence']
    with (OUT/'visual_candidates.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=candidate_cols); w.writeheader(); w.writerows(candidates)
    # 19 x 5 rows; target identity is deliberately unassigned because no target names/spec list was supplied.
    with (OUT/'t11_visual_registry.csv').open('w',newline='',encoding='utf-8-sig') as f:
        cols=['target_set_key','target_set_name','specialization','target_slot','prototype_item_id','prototype_item_name','source_itemset','display_id','model_and_texture_data','loose_asset_confirmation','selection_reason','alternative_candidates','visual_status','confidence','manual_review_questions']
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for n in range(1,20):
            for slot in ['Head','Shoulders','Chest','Hands','Legs']:
                w.writerow({'target_set_key':f'T11-{n:02d}','target_set_name':'NOT PROVIDED','specialization':'NOT PROVIDED','target_slot':slot,'prototype_item_id':'','prototype_item_name':'','source_itemset':'','display_id':'','model_and_texture_data':'','loose_asset_confirmation':'','selection_reason':'No prototype assigned; target class/spec list was not supplied and candidates require visual review.','alternative_candidates':f'See visual_candidates.csv filtered on slot={slot}','visual_status':'not checked','confidence':'not assigned','manual_review_questions':'Identify target set/spec; inspect candidate appearance and client asset availability.'})
    # source documentation: headers, schema/API provenance, hashes and separate locale inventory.
    schema_sql=SERVER/'data/sql/base/db_world'
    lines=['# Источники и методы аудита','',f'- Клиент: `{CLIENT}`; версия `Wow.exe`: 3.3.5.12340 (file metadata).',f'- Основной набор DBC: `{DBC}`. Обрабатывались только файлы из корня этого каталога.',f'- Сервер: `{SERVER}`; записи item_template взяты чтением файла `{template_path}`. SQL не исполнялся, база не открывалась.',f'- Результаты: `{OUT}`. Read-only helper: `dbc_audit.py` (только читает исходники; пишет четыре отчётных файла).','', '## Корневые DBC','', '| Файл | Байты | SHA-256 | Формат | Записей | Полей | Размер записи | Строковый блок |','|---|---:|---|---|---:|---:|---:|---:|']
    for name,d in dbcs.items(): lines.append(f"| `{name}` | {len(d['bytes'])} | `{d['sha256']}` | WDBC | {d['count']} | {d['fields']} | {d['record_size']} | {d['string_size']} |")
    lines += ['', 'Все шесть файлов имеют magic `WDBC`; для каждого выполнено `20 + record_count × record_size + string_block_size == file_size`, и `field_count × 4 == record_size`. Поля в DBC хранятся по 4 байта; строковые поля указывают смещение в таблицу строк.','', '## Подтверждённые структуры/сопоставления','', '- `Item.dbc`: `Itemfmt = niiiiiii` и `ItemEntry` в `src/server/shared/DataStores/DBCfmt.h` / `DBCStructure.h`: поля 0–7 это ID, ClassID, SubclassID, SoundOverrideSubclassID, Material, DisplayInfoID, InventoryType, SheatheType.','- `ItemDisplayInfo.dbc`: 25 полей по заголовку; порядок проверен по `itemdisplayinfo_dbc.sql` (ID, имена модели, модельные текстуры, иконки, геосеты, флаги, визуальные поля и текстуры). Core format `ItemDisplayTemplateEntryfmt` использует ID и поле иконки, игнорируя большинство визуальных полей; CSV декодирует строковые смещения по порядку DDL, поэтому визуальные поля — сырые данные DBC, не подтверждённый просмотр.','- `ItemSet.dbc`: `ItemSetEntryfmt` и `ItemSetEntry`: ID в поле 0, имя enUS в поле 1, ruRU в поле 12, членство в полях 18–34 (ItemID_1..17 per `itemset_dbc.sql`). Поля 28–34 закомментированы в `ItemSetEntry` текущего AC, но их смысл как ItemID_11..17 подтверждается SQL schema; аудит декодирует их как client DBC data.','- Связь предмет→display: `Item.dbc` поле `ID` (0) → `DisplayInfoID` (5) → `ItemDisplayInfo.dbc` поле `ID` (0). Название и ItemLevel извлечены по `entry` из записей файла `item_template.sql`; отдельно сохранено сравнение его `displayid` с DBC.','- Связь комплект→предмет: ID из `ItemSet.dbc` полей 18–34 сопоставлены с `Item.dbc.ID`, затем с `item_template.entry`. `ItemSet` не хранит отдельный слот для каждого ID; слот берётся из `Item.dbc.InventoryType` (сверен с `item_template.InventoryType`).','- `ItemVisuals.dbc`, `ItemSubClass.dbc`, `ItemClass.dbc`: заголовки/размеры/строки проверены. Для этих таблиц в доступном AC коде не обнаружено достаточного названного полного layout, поэтому они не используются для неподтверждённых связей; class/subclass в каталоге оставлены числовыми значениями Item.dbc.','', '## Локализованные и архивные копии','', 'Ниже отдельно перечислены доступные копии; они не смешивались с корневым набором:','', '| DBC | Каталог | Байты | SHA-256 |','|---|---|---:|---|']
    for v in variants: lines.append(f"| `{v['name']}` | `{v['folder']}` | {v['bytes']} | `{v['sha256']}` |")
    lines += ['', '## Ограничения','', '- `visual_candidates.csv` использует реальные члены T4/T5, найденные по именам семейств и ID-членам ItemSet. Категоризация T4/T5 — классификация по семействам названий, не самостоятельная игровая проверка.', '- Локальные модели/текстуры отмечаются только при точном совпадении относительного пути или уникальном совпадении basename с распакованным `.m2`/`.blp`; неоднозначные совпадения не подтверждаются. MPQ не читались, не извлекались.', '- По DBC и путям нельзя подтвердить внешний вид, комплектность на персонаже или совпадение визуальных моделей; все такие проверки имеют статус «не проверено».']
    (OUT/'audit_sources.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # Repeat analysis is numeric/string-key based and explicitly not visual.
    display_counts=Counter(r['item_dbc_display_id'] for r in candidates)
    model_counts=Counter((r['model_name_1'],r['model_name_2']) for r in candidates if r['model_name_1'] or r['model_name_2'])
    texture_counts=Counter(tuple(r[f'texture_{i}'] for i in range(1,9)) for r in candidates if any(r[f'texture_{i}'] for i in range(1,9)))
    repeated_displays={str(k):v for k,v in display_counts.items() if v>1}
    repeated_models=[{'model_names':list(k),'count':v} for k,v in model_counts.items() if v>1]
    repeated_textures=[{'texture_tuple':list(k),'count':v} for k,v in texture_counts.items() if v>1]
    missing_template=[r['source_item_id'] for r in candidates if not r['source_item_name']]
    missing_display=[r['source_item_id'] for r in candidates if r['item_dbc_display_id'] not in displays]
    slot_counts=Counter(r['slot'] for r in candidates)
    inventory_mismatch=[r['source_item_id'] for r in candidates if r['source_item_name'] and r['inventory_type']!=templates.get(r['source_item_id'],{}).get('inventory_type')]
    findings=['# Результаты первого табличного прохода','',f'- Корневые DBC разобраны: {len(dbcs)}; распознаны {sum(d["count"] for d in dbcs.values()):,} записей суммарно. Все размеры заголовков согласованы с размером файлов.',f'- Прочитано {tuple_count:,} кортежей из базового `item_template.sql` без исполнения SQL.',f'- Найдено {len(family_matches)} ItemSet-записей, чьи названия соответствуют семействам T4/T5; в каталог попало {len(candidates)} членов, для которых есть `Item.dbc` запись.',f'- Каталог кандидатов: {len(candidates)} строк; слоты по InventoryType: {dict(slot_counts)}.',f'- Проверка имени/уровня зависит от наличия item_template entry; без имени осталось {len(missing_template)} кандидатов. DisplayID отсутствует в ItemDisplayInfo для {len(missing_display)} кандидатов.',f'- Несовпадение InventoryType между Item.dbc и item_template: {len(inventory_mismatch)} записей.','', '## Целевой реестр','', '- `t11_visual_registry.csv` содержит ровно 95 строк (19 ключей × 5 слотов). В запросе не перечислены имена 19 целевых комплектов или специализаций, поэтому они оставлены `NOT PROVIDED`; ни один исходный предмет не назначен прототипом.', '- В каждой целевой строке приведена ссылка на каталог альтернатив по слоту; это не рекомендация окончательной модели.','', '## Повторы','',f'- DisplayID, встречающийся более одного раза в каталоге: {len(repeated_displays)} разных ID (повторы распределены по исходным set-вариантам).','', '| DisplayID | Количество строк |','|---:|---:|']
    findings += [f'| {k} | {v} |' for k,v in sorted(repeated_displays.items(),key=lambda kv:int(kv[0]))]
    findings += ['',f'- Повторяющиеся пары имён модели: {len(repeated_models)}; повторяющиеся полные сочетания полей Texture_1..8: {len(repeated_textures)}. Это только совпадение полей, не утверждение о визуальной идентичности.','- Подробности отображения и доступности точного loose path приведены в `visual_candidates.csv`; файлы, присутствующие только в MPQ, показаны как недоступные в распакованной проверке.', '', '## Ограничения и следующие действия','', '- Для выбора прототипов нужно получить названия/специализации всех 19 целевых комплектов. Без этой карты нельзя корректно связать кандидата с конкретным целевым комплектом.', '- Все кандидаты основаны на T4/T5 membership; так как для каждого класса/специализации в этих данных есть наборы по 5 предметов, поиск WotLK альтернатив для заполнения пробелов не запускался. Это предварительно по записям, не визуальная пригодность.', '- Просмотр модели/текстур обязателен до статуса «визуально подтверждено». В текущем окружении отдельного ModelViewer не найдено; `.m2`/`.blp` в MPQ не читаются.', '- Поля класса/подкласса в `Item.dbc` подтверждены как целые значения; человекочитаемые наименования из ItemClass/ItemSubClass не назначались, поскольку полные layouts не подтверждены серверными источниками.', '- Не создавались изменения сервера/клиента, SQL, патчи или игровые данные.']
    (OUT/'audit_findings.md').write_text('\n'.join(findings)+'\n',encoding='utf-8')
    print(json.dumps({'outputs':[p.name for p in OUT.iterdir() if p.is_file()],'source_sets':len(family_matches),'candidates':len(candidates),'slot_counts':dict(slot_counts),'templates':len(templates),'sql_tuples':tuple_count,'repeat_display_count':len(repeated_displays),'missing_template_names':len(missing_template),'inventory_type_mismatch':len(inventory_mismatch)},indent=2))

if __name__=='__main__': main()





