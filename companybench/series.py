"""Inspect attached time series without confirming facts or editing sources."""
import csv,hashlib,json
from collections import Counter
from datetime import date
from decimal import Decimal,InvalidOperation
from pathlib import Path

REQUIRED={'time','id','index_name','value'}
def number(value):
    if str(value).strip().lower() in {'','na','n/a','none','null','nan','--'}:return None
    try:
        result=Decimal(str(value))
        return result if result.is_finite() else None
    except InvalidOperation:return None

def profile_series(source,cutoff=None):
    source=Path(source)
    if cutoff:date.fromisoformat(cutoff)
    raw=source.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    counts=Counter();blanks=Counter();groups={};seen={};duplicates=[];conflicts=[];invalid=[]
    minimum=maximum=None
    with source.open('r',encoding='utf-8-sig',newline='') as handle:
        reader=csv.reader(handle);header=next(reader,None)
        if not header or len(header)!=len(set(header)) or not REQUIRED.issubset(header):
            raise ValueError('CSV需唯一列名及time/id/index_name/value字段')
        start=reader.line_num+1
        for cells in reader:
            line=start;start=reader.line_num+1
            if not cells or not any(cells):continue
            counts['records']+=1
            if len(cells)!=len(header):raise ValueError('字段数不符，原行'+str(line))
            row=dict(zip(header,cells));time=row['time']
            try:date.fromisoformat(time)
            except ValueError:invalid.append({'line':line,'time':time})
            minimum=min(minimum,time) if minimum else time;maximum=max(maximum,time) if maximum else time
            within=not cutoff or time<=cutoff
            counts['included_by_observation_date' if within else 'after_observation_cutoff']+=1
            if within and row.get('rtime','')[:10]>str(cutoff or '9999-12-31'):
                counts['included_rows_updated_after_cutoff']+=1
            for h,v in row.items():
                if v=='':blanks[h]+=1
            parsed=number(row['value'])
            if parsed is None:counts['missing_or_non_numeric_values']+=1
            key=(row.get('batch_no',''),row.get('batch_name',''),row['id'],row.get('thscode',''),row['index_name'])
            item=groups.setdefault(key,{'id':row['id'],'name':row['index_name'],'batch':row.get('batch_name',''),
                'thscode':row.get('thscode',''),'count':0,'included':0,'after_cutoff':0,'first_line':line,
                'min_time':time,'max_time':time,'missing_or_non_numeric':0})
            item['count']+=1;item['included']+=int(within);item['after_cutoff']+=int(not within)
            item['missing_or_non_numeric']+=int(parsed is None);item['last_line']=line
            item['min_time']=min(item['min_time'],time);item['max_time']=max(item['max_time'],time)
            dkey=(row['id'],row.get('thscode',''),time)
            if dkey in seen:
                duplicate={'key':dkey,'first_line':seen[dkey]['line'],'line':line,'values':[seen[dkey]['value'],row['value']]}
                duplicates.append(duplicate)
                if seen[dkey]['value']!=row['value']:conflicts.append(duplicate)
            else:seen[dkey]={'line':line,'value':row['value']}
    return {'source':str(source),'sha256':sha,'bytes':len(raw),'encoding':'UTF-8/UTF-8 BOM',
        'header':header,**dict(counts),'series_count':len(groups),'min_time':minimum,'max_time':maximum,
        'blank_fields':dict(blanks),'duplicate_records':len(duplicates),'conflicting_records':len(conflicts),
        'conflict_examples':conflicts[:12],'invalid_dates':invalid,'observation_cutoff':cutoff,
        'unit_metadata_present':'unit' in header,'publication_date_present':'publication_date' in header,
        'included_rows_rtime_after_cutoff':counts.get('included_rows_updated_after_cutoff',0),
        'rtime_semantics':'未获字段定义时Unknown；旧updated计数字段仅比较日期，不证明更新时间',
        'fact_confirmation':False,'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==sha,
        'limitations':['期间筛选不等于当时可获，rtime业务含义待核，不冒充更新日或披露日','累计值不按月求和；停更/同名序列不拼接',
                       '无单位和细分定义时不计算份额/可比净溢价','供应商附件不冒充一手公告或学生核验'],
        'catalog':list(groups.values())}

def comparability_gaps(left,right):
    """Return unresolved metadata instead of assuming two series are comparable."""
    required=['unit','currency','period_basis','market_scope','product_scope','price_layer','definition']
    issues=[]
    for key in required:
        if not left.get(key) or not right.get(key):issues.append('缺少'+key)
        elif left[key]!=right[key]:issues.append(key+'不同')
    return issues
