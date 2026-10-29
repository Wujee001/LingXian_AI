# -*- coding: utf-8 -*-
"""八字段候选的保守中文展示，不是完整的上下文/句读知识库推理。
NA：本字未显写；OTHER：超出当前词表。不能把 NA 当成散音/零徽。
2026-10-27 @zjx：明确字段候选状态，不将八字段自动猜成注册表中的完整类别。
"""
from __future__ import annotations

LABELS={'rh':'右手动作','string':'弦序','lh':'左手按指','hui_base':'徽位',
        'hui_frac':'徽分','mod':'技法修饰','tone':'音类','strings':'复合弦序'}
FINGER={'da':'大指','zhong':'中指','shi':'食指','ming':'名指',
        'da+zhong':'大指＋中指','ming+da':'名指＋大指'}
RIGHT={'gou':'勾','tiao':'挑','mo':'抹','ti':'剔','tuo':'托',
       'cuo':'撮','li':'历','lun':'轮','bo':'拨','da':'打',
       'da+zhai':'打摘','da_yuan':'打圆'}
MOD={'jin':'进','tui':'退','shang':'上','xia':'下','fu':'复','zhuang':'撞',
     'taoqi':'滔起','daiqi':'带起','zhuaqi':'抓起','chuo':'绰','chuo+shang':'绰上',
     'he':'合','yinghe':'应合','zhu':'注','qia_qi':'掐起','tangxia':'淌下'}
TONE={'san':'散音','an':'按音','an+san':'按音与散音组合'}
NA_SET={'','NA','NONE','OTHER','null','unknown','None'}


def label_value(field:str,value:str) -> str:
    val=str(value or 'NA')
    if val in ('NA','NONE',''):return '本字未明写'
    if val=='OTHER':return '稀有或未识别'
    if field=='rh':return RIGHT.get(val,val)
    if field=='lh':return FINGER.get(val,val)
    if field=='mod':return MOD.get(val,val)
    if field=='tone':return TONE.get(val,val)
    if field=='string':return f'{val}弦' if val in '1234567' and len(val)==1 else val
    if field=='strings':return val.replace('+','、')+'弦'
    if field=='hui_base':return f'{val}徽'
    if field=='hui_frac':return f'{val}分' if val!='0' else '整徽'
    return val


def get_top1(prediction:dict) -> dict:
    top=prediction.get('attributes_top3',{})
    return {k:str(top[k][0]['value']) if isinstance(top.get(k),list) and top[k] else 'NA' for k in LABELS}


def parse_attributes(attrs:dict) -> dict:
    """只解释字框内显式预测值；不冒称知道弦位继承、节奏或完整演奏事件。"""
    chosen={k:str(attrs.get(k,'NA')) for k in LABELS}
    base,frac=chosen['hui_base'],chosen['hui_frac']
    hui=('未明写' if base in NA_SET
         else base+'徽'+(frac+'分' if frac not in NA_SET|{'0'} else ''))
    right={'finger': label_value('rh',chosen['rh']),
           'string':label_value('string',chosen['string'])}
    left={'finger':label_value('lh',chosen['lh']), 'hui':hui}
    summary=[]
    for field in ('rh','string','lh','hui_base','hui_frac','mod','tone','strings'):
        val=chosen[field]
        if val not in NA_SET and not (field=='hui_frac' and val=='0'):
            summary.append(LABELS[field]+'：'+label_value(field,val))
    return {'class_key':None, 'display_name':'／'.join(summary[:3]) or '未识别到明确减字属性',
            'right_hand':right,'left_hand':left,'attributes':chosen,
            'meaning': ('模型候选（待人工核对）：'+ '；'.join(summary) if summary else '模型未识别到可确认的显式属性')
                     +'。省写／承前位置、复合动作的语义及简谱节奏尚未由本模型确认。',
            'is_confirmed':False,
            'knowledge_status':'field_candidate',
            'needs_meaning_review':True,
            'origin':'stage2_model_candidate'}
