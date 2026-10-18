# -*- coding: utf-8 -*-
"""泠弦智谱 Stage-2 ResNet18：对单个真实减字框产生八字段 Top-3 候选。
此模块只依赖 torch、torchvision、Pillow；不依赖训练脚本/scikit-learn。

本模块不能自己找到减字框、不能根据单字推导省写继承，也不能进行句读。

用法:
    from stage2_reader_service import Stage2Recognizer
    service = Stage2Recognizer('stage2_best.pth')  # 应在服务启动时加载一次
    result = service.predict_boxes('sheet.jpg', [(100,200,150,260)])
"""
from __future__ import annotations
from pathlib import Path
from typing import Sequence
import math
import torch
from torch import nn
from torch.nn import functional as F
from torchvision import transforms
from torchvision.models import resnet18
from PIL import Image

HEADS=('rh','string','lh','hui_base','hui_frac','mod','tone','strings')


class MultiHeadResNet(nn.Module):
    """必须和 Stage2 Colab v01 保存时的结构一致。"""
    def __init__(self,vocab):
        super().__init__()
        backbone=resnet18(weights=None)
        dim=backbone.fc.in_features
        backbone.fc=nn.Identity()
        self.backbone=backbone
        self.heads=nn.ModuleDict({h:nn.Sequential(nn.Dropout(0.30), nn.Linear(dim,len(vocab[h]))) for h in HEADS})
    def forward(self,x):
        features=self.backbone(x)
        return {h:head(features) for h,head in self.heads.items()}


def crop_box(im:Image.Image,coords:Sequence[float],padding:float=0.10,side:int=96)->Image.Image:
    """与训练阶段 prepare_stage2.py:crop_gray() 完全一致的裁剪和背景填充。"""
    if len(coords)!=4: raise ValueError('box 必须是 x1,y1,x2,y2（原图像素）')
    x1,y1,x2,y2=map(float,coords)
    if not all(map(math.isfinite,[x1,y1,x2,y2])) or not (0<=x1<x2<=im.width and 0<=y1<y2<=im.height):
        raise ValueError(f'检测框无效/超出原图: {coords} vs {im.size}')
    dx=max(2.0,(x2-x1)*padding)
    dy=max(2.0,(y2-y1)*padding)
    xa=max(0,int(math.floor(x1-dx))); xb=min(im.width,int(math.ceil(x2+dx)))
    ya=max(0,int(math.floor(y1-dy))); yb=min(im.height,int(math.ceil(y2+dy)))
    region=im.crop((xa,ya,xb,yb)).convert('L')
    span=max(region.size)
    background=int(region.resize((1,1)).getpixel((0,0)))
    background=max(205,background)
    canvas=Image.new('L',(span,span),background)
    canvas.paste(region,((span-region.width)//2,(span-region.height)//2))
    return canvas.resize((side,side),Image.Resampling.LANCZOS)


class Stage2Recognizer:
    def __init__(self,weights:str|Path,device:str='cpu',review_threshold:float=0.75):
        self.device=torch.device(device)
        self.weights=Path(weights)
        ckpt=torch.load(self.weights,map_location='cpu',weights_only=True)
        if ckpt.get('architecture')!='resnet18_multihead':
            raise ValueError('所提供的不是 Stage-2 多头 ResNet18 权重，不可把 YOLO best.pt 混入')
        self.vocab=ckpt['vocab']
        self.imgsz=int(ckpt['imgsz'])
        self.model=MultiHeadResNet(self.vocab).to(self.device)
        self.model.load_state_dict(ckpt['state_dict'],strict=True)
        self.model.eval()
        self.review_threshold=float(review_threshold)
        self.preprocess=transforms.Compose([
            transforms.Grayscale(num_output_channels=3),
            transforms.Resize((self.imgsz,self.imgsz)),
            transforms.ToTensor(),
            transforms.Normalize((.485,.456,.406),(.229,.224,.225)),
        ])

    @torch.inference_mode()
    def predict_boxes(self,image:Image.Image|str|Path, boxes:Sequence[Sequence[float]],batch_size:int=24):
        """返回每框 Top3 + 风险提示。坐标必须以原图宽高为基准，不是 CSS 显示尺寸。"""
        if isinstance(image,(str,Path)):
            with Image.open(image) as im: src=im.convert('RGB')
        else:
            src=image.convert('RGB')
        coords=[list(map(float,b)) for b in boxes]
        if not coords:return []
        all_rows=[]
        for start in range(0,len(coords),batch_size):
            group=coords[start:start+batch_size]
            x=torch.stack([self.preprocess(crop_box(src,b).convert('RGB')) for b in group]).to(self.device)
            output=self.model(x)
            probability={h:F.softmax(logits,dim=-1).cpu() for h,logits in output.items()}
            for j,b in enumerate(group):
                attrs={};warn=[]
                for h in HEADS:
                    vec=probability[h][j]
                    rank=torch.argsort(vec,descending=True)[:3].tolist()
                    candidates=[{'value':str(self.vocab[h][k]),'score':round(float(vec[k]),5)} for k in rank]
                    attrs[h]=candidates
                    if candidates[0]['value']=='OTHER':warn.append(f'{h}: 不支持/稀有字形 OTHER')
                    elif candidates[0]['score']<self.review_threshold:warn.append(f'{h}: 候选置信度不足（仅为未校准概率）')
                if attrs['hui_base'][0]['value']=='NA' and attrs['hui_frac'][0]['value'] not in ('NA','OTHER'):
                    warn.append('徽位未明确但徽分有值：不可直接输出确认解释')
                # 新曲目 tone/mod/strings 缺失或少见类即使高分也可能出错；这里始终人工核验。
                warn.append('谱外泛化未经充分验证：指法结果仅作候选，需用户/教师确认')
                all_rows.append({'bbox_xyxy':b,'attributes_top3':attrs,'needs_review':bool(warn),
                                 'review_reasons':warn,'model_stage':'stage2_resnet18_explicit_glyph_fields'})
        return all_rows


if __name__=='__main__':
    import argparse,csv,json
    p=argparse.ArgumentParser(description='对 CSV 中 YOLO 检测出的减字框输出指法候选。')
    p.add_argument('--weights',required=True)
    p.add_argument('--image',required=True)
    p.add_argument('--boxes-csv',required=True)
    p.add_argument('--output',default='stage2_candidates.json')
    p.add_argument('--review-threshold',type=float,default=.75)
    args=p.parse_args()
    with open(args.boxes_csv,encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    coords=[[float(row[k]) for k in ('x1','y1','x2','y2')] for row in rows]
    reader=Stage2Recognizer(args.weights,review_threshold=args.review_threshold)
    predictions=reader.predict_boxes(args.image,coords)
    for i,(row,pred) in enumerate(zip(rows,predictions)):
        pred['source_pred_index']=i
        pred['stage1_detection_confidence']=float(row.get('confidence',0))
    result={'image':args.image,'image_boxes_count':len(predictions),'model':str(args.weights),
            'model_limitations':['每框仅输出指法显式属性候选','不自动解析简谱/句读','NA代表未显写，不代表散音或真实继承状态','OTHER不能作为演奏术语','低置信度和跨谱本结果必须人工核验'],
            'results':predictions}
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('完成',len(predictions),'框；输出',args.output)

# ===== FastAPI 复用的权重单例（需服务重启后生效） =====
from core.config import MODEL_DIR

_WEIGHT_FILE = Path(MODEL_DIR) / 'stage2_best.pth'
_shared = None
_last_error = None


def get_reader():
    global _shared,_last_error
    if _shared is not None: return _shared
    if not _WEIGHT_FILE.is_file():
        _last_error=f'缺少第二阶段属性权重: {_WEIGHT_FILE}'
        return None
    try:
        _shared=Stage2Recognizer(_WEIGHT_FILE, device='cpu')
        _last_error=None
    except Exception as e:
        _last_error=f'第二阶段权重加载失败: {e}'
    return _shared


def status():
    model=get_reader()
    return {'available':model is not None,'model':'ResNet18 八字段指法候选识别',
            'weight':_WEIGHT_FILE.name,'error':None if model else _last_error}


def predict_pil(image:Image.Image):
    reader=get_reader()
    if reader is None: raise RuntimeError(_last_error or 'Stage2 不可用')
    return reader.predict_boxes(image,[(0,0,image.width,image.height)])[0]
