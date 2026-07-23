import os
import json
import time
import requests
from datetime import datetime

# ==========================================
# 설정
# ==========================================
USER_ID = "charming09"
BASE_API_URL = "https://api.pandalive.co.kr/v1/bj_notice/index"
SAVE_DIR = f"./pandalive_{USER_ID}"
MASTER_JSON_PATH = os.path.join(SAVE_DIR, "notices_master.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://m.pandalive.co.kr/bjInfo/{USER_ID}",
}

# ==========================================
# 마스터 데이터 로드 & 저장
# ==========================================
def load_master_data():
    if os.path.exists(MASTER_JSON_PATH):
        try:
            with open(MASTER_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[경고] 마스터 파일 로드 실패, 새로 생성합니다: {e}")
    return {}

def save_master_data(master_data):
    with open(MASTER_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=4)

# ==========================================
# 이미지 다운로드
# ==========================================
def download_image_if_needed(idx, img_src, save_dir):
    if not img_src:
        return
    
    img_dir = os.path.join(save_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    clean_img_url = img_src.split("?")[0]
    img_name = f"{idx}_{os.path.basename(clean_img_url)}"
    local_img_path = os.path.join(img_dir, img_name)

    if not os.path.exists(local_img_path):
        try:
            res = requests.get(img_src, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                with open(local_img_path, "wb") as f:
                    f.write(res.content)
                print(f"  └ [이미지 다운로드 성공] {img_name}")
        except Exception as e:
            print(f"  └ [이미지 에러] 글번호 {idx}: {e}")

# ==========================================
# 변경 감지 및 데이터 병합 (UPSERT)
# ==========================================
def sync_with_master(fetched_items, save_dir):
    master_data = load_master_data()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_count = 0
    updated_count = 0

    for item in fetched_items:
        idx_str = str(item.get("idx"))
        contents = item.get("contents", "")
        img_src = item.get("imgMainSrc", "")
        is_top = item.get("isTop", False)

        # 1. 신규 게시글
        if idx_str not in master_data:
            master_data[idx_str] = {
                "idx": item.get("idx"),
                "date": item.get("insertDateTime", ""),
                "isTop": is_top,
                "contents": contents,
                "imgMainSrc": img_src,
                "firstSeenAt": now_str,
                "lastUpdatedAt": now_str,
                "history": [] # 변경 이력 보관용
            }
            download_image_if_needed(item.get("idx"), img_src, save_dir)
            new_count += 1
            print(f"✨ [신규 게시글 감지] #{idx_str}")

        # 2. 기존 게시글 -> 내용 또는 이미지 변경 확인
        else:
            old_item = master_data[idx_str]
            has_content_changed = old_item.get("contents") != contents
            has_img_changed = old_item.get("imgMainSrc") != img_src
            has_top_changed = old_item.get("isTop") != is_top

            if has_content_changed or has_img_changed or has_top_changed:
                # 이전 버전 기록 남기기
                history_entry = {
                    "updatedAt": now_str,
                    "previousContents": old_item.get("contents"),
                    "previousImgMainSrc": old_item.get("imgMainSrc")
                }
                
                if "history" not in old_item:
                    old_item["history"] = []
                old_item["history"].append(history_entry)

                # 최신 데이터로 갱신
                old_item["contents"] = contents
                old_item["imgMainSrc"] = img_src
                old_item["isTop"] = is_top
                old_item["lastUpdatedAt"] = now_str

                # 새로 추가되거나 변경된 이미지 다운로드
                if has_img_changed:
                    download_image_if_needed(item.get("idx"), img_src, save_dir)

                updated_count += 1
                print(f"✏️ [게시글 수정 감지] #{idx_str} (수정 시각: {now_str})")

    # 결과 마스터 저장
    save_master_data(master_data)
    print(f"📊 [동기화 완료] 신규: {new_count}건 / 수정: {updated_count}건 / 총 관리 글: {len(master_data)}개")

# ==========================================
# API 수집 함수
# ==========================================
def fetch_notice_data(fetch_all: bool = False):
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    limit = 20
    first_url = f"{BASE_API_URL}?limit={limit}&userId={USER_ID}&offset=0"
    
    print(f"[{now_str}] 데이터 요청 중...")
    try:
        response = requests.get(first_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        first_data = response.json()
    except Exception as e:
        print(f"API 호출 실패: {e}")
        return []

    if not fetch_all:
        return first_data.get("list", [])

    # 전체 백업 모드
    page_info = first_data.get("page", {})
    total_count = page_info.get("total", 0)
    print(f"-> [전체 백업 모드 시작] 총 게시글 수: {total_count}개")

    all_items = []
    all_items.extend(first_data.get("list", []))

    for offset in range(limit, total_count, limit):
        url = f"{BASE_API_URL}?limit={limit}&userId={USER_ID}&offset={offset}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                items = res.json().get("list", [])
                if not items:
                    break
                all_items.extend(items)
        except Exception as e:
            print(f"요청 중 예외 발생 (offset={offset}): {e}")
        time.sleep(0.3)

    return all_items

if __name__ == "__main__":
    import sys

    # 1. 커맨드라인 인자(Argument)가 전달된 경우
    if len(sys.argv) > 1:
        mode_arg = sys.argv[1].lower().strip()

        if mode_arg == "all":
            is_fetch_all = True
            print("🔄 [자동 실행] 전체 게시글 수집 및 동기화 시작")
        elif mode_arg == "recent":
            is_fetch_all = False
            print("⚡ [자동 실행] 최근 20개 게시글 수집 및 동기화 시작")
        else:
            print(f"❌ [오류] 잘못된 인자입니다: '{sys.argv[1]}'")
            print("사용법:")
            print("  - 인자 없이 실행: 대화형 메뉴 선택")
            print("  - python getnotice.py recent : 최근 20개 수집")
            print("  - python getnotice.py all    : 전체 게시글 수집")
            sys.exit(1)

    # 2. 인자가 없는 경우 (직접 물어보기)
    else:
        print("=== 수집 모드를 선택하세요 ===")
        print("1: 최근 20개 수집 및 동기화 (주기적 실행용)")
        print("2: 전체 과거 게시글 마스터 DB 생성 (하루 1회/정기 백업)")
        choice = input("선택 (1 또는 2 입력 후 엔터): ").strip()
        is_fetch_all = True if choice == "2" else False

    # 수집 및 동기화 실행
    fetched_items = fetch_notice_data(fetch_all=is_fetch_all)

    if fetched_items:
        sync_with_master(fetched_items, save_dir=SAVE_DIR)
    else:
        print("가져온 데이터가 없습니다.")