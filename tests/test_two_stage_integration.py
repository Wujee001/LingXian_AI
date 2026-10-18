# -*- coding: utf-8 -*-
"""双模型 API 契约测试，不依赖访问网络/真实 Ultralytics 安装。"""
import io
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from service import yolo_infer,stage2_reader,correction_store
from service.attribute_parser import parse_attributes, get_top1
from main import app


def image_bytes():
    im=Image.new('RGB',(320,240),'white')
    b=io.BytesIO();im.save(b,'PNG');return b.getvalue()


def make_attrs():
    values={'rh':'gou','string':'4','lh':'ming','hui_base':'10','hui_frac':'0',
            'mod':'NA','tone':'an','strings':'NONE'}
    attrs={k:[{'value':v,'score':0.87},{'value':'NA','score':0.13}] for k,v in values.items()}
    return {'attributes_top3':attrs,'review_reasons':['需要人工核对']}


def make_detector_result():
    return (True,[{'box':{'x':0.1,'y':0.2,'w':0.12,'h':0.18},
                   'xyxy':[32,48,70.4,91.2],
                   'confidence':0.75,'raw_label':'jianzi','class_key':None}],(320,240))


class DummyReader:
    def predict_boxes(self,image,boxes):
        assert image.size==(320,240)
        assert len(boxes)==1
        assert abs(boxes[0][0]-32)<0.1
        return [make_attrs()]


def test_semantics_only_explicit_fields():
    p=parse_attributes({'rh':'gou','string':'4','lh':'NA','hui_base':'NA',
                        'hui_frac':'NA','mod':'NA','tone':'NA','strings':'NONE'})
    assert p['right_hand']['string']=='4弦'
    assert p['left_hand']['finger']=='本字未明写'
    assert '散音' not in p['meaning']
    assert p['is_confirmed'] is False
    assert get_top1(make_attrs())['rh']=='gou'


def test_stage1_edge_filter_math():
    assert yolo_infer._starts(1447,768,600)==[0,600,679]
    assert yolo_infer._truncated((60,720,95,768),0,0,768,768,1447,2048,2)
    assert not yolo_infer._truncated((60,0,95,30),0,0,768,768,1447,2048,2)
    assert yolo_infer._nms([[10,10,20,20],[11,11,21,21],[100,100,130,130]],
                           [0.91,0.80,0.7])==[0,2]


def test_stage1_predictor_without_model_dependency():
    class Tensor:
        def __init__(self,data): self.arr=np.array(data)
        def cpu(self):return self
        def numpy(self):return self.arr
    class Model:
        def predict(self,**kwargs):
            class X: pass
            result=X();result.boxes=X()
            result.boxes.xyxy=Tensor([[20,30,60,70],[21,31,61,71]])
            result.boxes.conf=Tensor([0.90,0.80])
            return [result]
    boxes,scores,removed=yolo_infer.detect_tiles(Model(),np.zeros((240,320,3),dtype=np.uint8))
    assert len(boxes)==len(scores)==1
    assert boxes[0]==[20,30,60,70]
    assert removed==0


def test_sheet_stage1_stage2_and_corrections(monkeypatch,tmp_path):
    monkeypatch.setattr(yolo_infer,'recognize',lambda p:make_detector_result())
    monkeypatch.setattr(stage2_reader,'get_reader',lambda:DummyReader())
    monkeypatch.setattr(correction_store,'_STORE_PATH',str(tmp_path/'corrections.json'))
    client=TestClient(app)
    res=client.post('/api/sheet/upload',files={'file':('page.png',image_bytes(),'image/png')},
                    data={'engine':'auto'})
    assert res.status_code==200,res.text
    d=res.json()['data']
    assert d['source']=='stage1_yolo+stage2'
    assert len(d['items'])==1
    item=d['items'][0]
    assert item['status']=='U'  # 不自动确认
    assert item['attributes_selected']['rh']=='gou'
    assert item['parse_result']['right_hand']['finger']=='勾'
    assert item['candidates']==[]  # 不伪造整字知识库 key
    payload={'image_url':d['image_url'],'index':0,'box':item['box'],
             'attributes_selected':item['attributes_selected'],
             'attributes_top3':item['attributes_top3'],
             'detection_confidence':item['detection_confidence'],
             'source':d['source'],'confirmed_key':None}
    saved=client.post('/api/sheet/correct',json=payload)
    assert saved.status_code==200
    rows=correction_store.list_all()
    assert len(rows)==1
    assert rows[0]['attributes_selected']['string']=='4'


def test_manual_single_char_stage2(monkeypatch):
    monkeypatch.setattr(stage2_reader,'get_reader',lambda:DummyReaderForSingle())
    client=TestClient(app)
    res=client.post('/api/char/predict',files={'file':('glyph.png',image_bytes(),'image/png')},
                    data={'engine':'auto'})
    assert res.status_code==200,res.text
    body=res.json()['data']
    assert body['source']=='stage2' and body['status']=='U'
    assert body['top_key'] is None and body['candidates']==[]
    assert body['attributes_top3']['rh'][0]['value']=='gou'
    res=client.post('/api/char/parse-attributes',json={'attributes':{'rh':'tiao','string':'7','lh':'NA'}})
    assert res.status_code==200
    assert res.json()['data']['right_hand']['finger']=='挑'


class DummyReaderForSingle:
    def predict_boxes(self,image,boxes):
        assert boxes==[(0,0,320,240)] or boxes==[[0,0,320,240]]
        return [make_attrs()]


def test_stage1_only_does_not_invent_attributes(monkeypatch):
    monkeypatch.setattr(yolo_infer,'recognize',lambda p:make_detector_result())
    monkeypatch.setattr(stage2_reader,'get_reader',lambda:None)
    client=TestClient(app)
    res=client.post('/api/sheet/upload',files={'file':('page.png',image_bytes(),'image/png')})
    assert res.status_code==200
    item=res.json()['data']['items'][0]
    assert item['status']=='U' and item['attributes_top3']=={}
    assert item['parse_result'] is None and item['candidates']==[]
