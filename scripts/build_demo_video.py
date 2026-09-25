"""Captioned evidence replay, deliberately labelled as not a screen recording."""
from pathlib import Path
import json, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.media-runtime'))
import imageio_ffmpeg
e=json.loads((ROOT/'artifacts/policy-change-evidence.json').read_text(encoding='utf-8'))
retry=json.loads((ROOT/'artifacts/policy-change-live-retry.json').read_text(encoding='utf-8'))
out=ROOT/'output/video';out.mkdir(parents=True,exist_ok=True)
frames=ROOT/'tmp/policy-video';frames.mkdir(parents=True,exist_ok=True)
fontroot=Path('C:/Windows/Fonts') if Path('C:/Windows/Fonts').exists() else Path('/mnt/c/Windows/Fonts')
def font(size,bold=False):return ImageFont.truetype(str(fontroot/('malgunbd.ttf' if bold else 'malgun.ttf')),size)
sections=[
 ('정책이 바뀌면, 자동화도 다시 검증','SkillForge / 검증 가능한 업무 자동화',
  ['반복 환불을 자동화해도 정책과 승인 기준은 변합니다.','운영자는 어떤 사례가 왜 달라지는지 알아야 합니다.','실행 출처 → 독립 검증 → 변경 영향 → 재승격','합성 커머스 주문 · 실제 결제 없음']),
 ('성공 경험을 근거 있는 절차로','새 NVIDIA discovery 성공 5건에서 구성',
  ['Nemotron이 6개 업무 도구를 순서대로 호출합니다.','이전 quote 출력과 실제 인자의 값·타입·순서를 대조합니다.','과거 주문 ID 대신 입력과 이전 출력 참조를 사용합니다.','지원 범위는 환불 6단계 · 범용 프로그램 학습 아님']),
 ('검증을 통과한 버전만 활성화','Validation 30건 + 승인 경계 6건',
  ['생성에 사용하지 않은 사례를 독립 DB에서 재실행합니다.','도구 오류·중복·승인·정책 경계는 공통 gateway로 검사합니다.','운영자가 artifact와 보고서를 확인하고 활성화합니다.','회귀 테스트 57건 통과 · 별도 안전 행렬 36/36']),
 ('35만원 환불의 판단이 달라집니다','승인 기준 50만원 → 30만원',
  ['변경 전: 자동 환불 가능 / 변경 후: 운영자 승인 필요',f'42쌍의 합성 비교 중 {e["comparison"]["changed_count"]}개 사례 판정 변화',f'위험 변경 {e["comparison"]["unsafe_count"]} · 정상 환불 오차단 {e["comparison"]["false_block_count"]}', '미리보기는 운영 주문을 환불하지 않습니다.']),
 ('출처를 보존하고, 다시 검증합니다','기존 절차 STALE → 새 후보 → 검증 → 활성화',
  ['정책 적용 시 이전 버전의 절차 재사용을 중지합니다.','부모 hash와 원래 실행 출처를 새 후보에 남깁니다.','새 정책에서 분리 검증·경계 검사를 다시 통과해야 합니다.','35만원 주문: 승인 대기 → 단회 승인 → 1회 환불']),
 ('실제 증거와 한계를 함께 공개','github.com/kkokkiyo/skillforge',
  ['신규 live 5개 출처 성공 · 변경 후 승인 대기 확인','변경 전 live: HTTP 500 실패 보존 → 별도 재실행 '+retry['result']['status'], 'OpenShell OS 격리·대회 Skill API 기준은 미확인','42쌍은 모의 비교입니다. 실서비스 안전성 보장이 아닙니다.'])
]
def wrap(draw,text,width,f):
    lines=[];line=''
    for char in text:
        if draw.textlength(line+char,font=f)>width:lines.append(line);line=''
        line+=char
    return lines+[line]
for i,(title,subtitle,lines) in enumerate(sections,1):
    im=Image.new('RGB',(1280,720),'#0b1410');d=ImageDraw.Draw(im)
    d.text((64,38),'SKILLFORGE / POLICY-AWARE AUTOMATION',font=font(17,True),fill='#b6ed64')
    d.text((64,106),title,font=font(39,True),fill='#e8f0e9')
    d.text((64,174),subtitle,font=font(25),fill='#a1b1a8')
    y=255
    for j,line in enumerate(lines,1):
        d.text((64,y),f'0{j}',font=font(20,True),fill='#b6ed64')
        for segment in wrap(d,line,1050,font(25)):
            d.text((120,y),segment,font=font(25),fill='#e8f0e9');y+=38
        y+=24
    d.line((64,612,1216,612),fill='#344336',width=1)
    d.text((64,640),'저장된 실제 실행 증거의 시각화 · 브라우저 화면 녹화 아님',font=font(19),fill='#a1b1a8')
    d.text((1135,38),f'{i:02} / 06',font=font(17),fill='#a1b1a8')
    d.rectangle((0,707,int(1280*i/6),720),fill='#b6ed64')
    im.save(frames/f'{i:02}.png')
manifest=frames/'concat.txt'
manifest.write_text(''.join(f"file '{i:02}.png'\nduration 30\n" for i in range(1,7))+"file '06.png'\n",encoding='utf-8')
video=out/'SkillForge-evidence-walkthrough.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(manifest),'-t','180','-vf','fps=24','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
reader=imageio_ffmpeg.read_frames(str(video));meta=next(reader);reader.close()
assert 179.9<=meta['duration']<=180.1
(out/'video-manifest.json').write_text(json.dumps({'duration_seconds':meta['duration'],'size':meta['size'],'format':'captioned evidence replay','not_browser_recording':True,'source':'artifacts/policy-change-evidence.json','retry_source':'artifacts/policy-change-live-retry.json','source_mode':e['source']},indent=2),encoding='utf-8')
print(json.dumps({'duration':meta['duration'],'bytes':video.stat().st_size}))
