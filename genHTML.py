import os
import json
import re
from datetime import datetime, timezone, timedelta  # ⏱️ 시간 처리를 위해 추가

USER_ID = "charming09"
SAVE_DIR = f"./pandalive_{USER_ID}"
MASTER_JSON_PATH = os.path.join(SAVE_DIR, "notices_master.json")
TEMPLATE_PATH = "./template.html"
OUTPUT_HTML_PATH = os.path.join(SAVE_DIR, "index.html")


def clean_contents(text: str) -> str:
    """HTML 태그 정제 및 개행 정리"""
    if not text:
        return ""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('\n\n', '\n')
    return text.strip()

def build_html():
    if not os.path.exists(MASTER_JSON_PATH):
        print(f"에러: {MASTER_JSON_PATH} 파일이 없습니다.")
        return

    if not os.path.exists(TEMPLATE_PATH):
        print(f"에러: {TEMPLATE_PATH} 템플릿 파일이 없습니다.")
        return

    # 1. 마스터 JSON 데이터 로드
    with open(MASTER_JSON_PATH, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    # 2. 데이터 정제 및 로컬 이미지 경로 보존/생성
    cleaned_master_data = {}
    for idx_str, item in master_data.items():
        item_copy = item.copy()
        
        # 메인 본문 정제
        item_copy["contents"] = clean_contents(item_copy.get("contents", ""))
        
        # 📸 로컬 이미지 경로 처리
        existing_local = item_copy.get("localImgPath")
        img_src = item_copy.get("imgMainSrc")

        if existing_local:
            item_copy["localImgPath"] = existing_local
        elif img_src:
            clean_url = img_src.split("?")[0]
            img_name = f"{item_copy.get('idx', idx_str)}_{clean_url.split('/')[-1]}"
            item_copy["localImgPath"] = f"./images/{img_name}"
        else:
            item_copy["localImgPath"] = None

        if "imgMainSrc" in item_copy:
            del item_copy["imgMainSrc"]

        # 수정 이력(history) 본문 정제
        if "history" in item_copy and isinstance(item_copy["history"], list):
            new_history = []
            for h in item_copy["history"]:
                h_copy = h.copy()
                h_copy["previousContents"] = clean_contents(h_copy.get("previousContents", ""))
                new_history.append(h_copy)
            item_copy["history"] = new_history
            
        cleaned_master_data[idx_str] = item_copy

    # 3. HTML 템플릿 읽기
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html_template = f.read()

    # 4. 데이터 주입 및 빌드 시간 치환 ⏱️
    json_str = json.dumps(cleaned_master_data, ensure_ascii=False)
    
    # 한국 표준시(KST, UTC+9) 기준으로 최근 액션 빌드 시각 생성
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

    # 💡 데이터 및 빌드 시각 치환
    final_html = html_template.replace("/* __DATA_INJECTION__ */", json_str)
    final_html = final_html.replace("/* __BUILD_TIME__ */", now_kst)

    # 5. 결과 저장
    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"✨ HTML 뷰어 빌드 완료! (최신 갱신 시각: {now_kst}) -> {OUTPUT_HTML_PATH}")

if __name__ == "__main__":
    build_html()