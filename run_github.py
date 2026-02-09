import os
import sys
from article_summarizer_debug import ArticleSummarizer

# ========================================
# 1. API 키 로드 (환경변수 또는 직접 입력)
# ========================================
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

if not ANTHROPIC_API_KEY:
    print("❌ 에러: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
    print("GitHub 레포지토리 → Settings → Secrets and variables → Actions → New repository secret")
    print("Name: ANTHROPIC_API_KEY")
    print("Value: 여기에-API-키-입력")
    sys.exit(1)

# ========================================
# 2. URL 로드
# ========================================
try:
    with open('urls.txt', 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print("❌ 에러: urls.txt 파일을 찾을 수 없습니다.")
    print("레포지토리에 urls.txt 파일을 추가해주세요.")
    sys.exit(1)

if not urls:
    print("❌ 에러: urls.txt 파일이 비어있습니다.")
    sys.exit(1)

print(f"📰 총 {len(urls)}개 URL 로드 완료")

# ========================================
# 3. 실행
# ========================================
summarizer = ArticleSummarizer(ANTHROPIC_API_KEY)

summarizer.process_urls(
    urls=urls,
    output_file="articles_summary.csv",
    delay=1.5,          # 1.5초 대기
    save_interval=20    # 20개마다 중간 저장
)

print("\n🎉 모든 작업 완료!")
print("💾 결과 파일: articles_summary.csv")
print("📥 GitHub Actions → Artifacts에서 다운로드 가능")
