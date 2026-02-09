import requests
from bs4 import BeautifulSoup
import anthropic
import csv
from datetime import datetime
import time
import os
from typing import List, Dict, Optional

class ArticleSummarizer:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def fetch_article(self, url: str, timeout: int = 10) -> Optional[Dict[str, str]]:
        try:
            print(f"  📡 URL 요청 중...")
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            print(f"  ✓ 응답 받음 (상태: {response.status_code})")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 제목 추출 - 더 넓은 범위로 검색
            title = None
            title_selectors = [
                'h1',  # 가장 흔한 제목 태그
                'h2',  # 부제목으로도 사용
                '.article-title',
                '.news-title',
                '.title',
                'meta[property="og:title"]',
                'meta[name="title"]'
            ]
            
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title = element.get('content') if element.name == 'meta' else element.get_text(strip=True)
                    if title and len(title) > 5:  # 최소 길이 체크
                        print(f"  ✓ 제목 찾음 (선택자: {selector}): {title[:50]}...")
                        break
            
            if not title:
                print(f"  ✗ 제목을 찾을 수 없습니다")
                print(f"  🔍 시도한 선택자: {title_selectors}")
                return None
            
            # 본문 추출 - 더 넓은 범위로 검색
            content = None
            content_selectors = [
                'article',
                '.article-body',
                '.news-content',
                '.article-content',
                '#article-view-content-div',
                '.view-content',
                '.article_view'
            ]
            
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    # 불필요한 태그 제거
                    for tag in element.find_all(['script', 'style', 'nav', 'aside', 'header', 'footer']):
                        tag.decompose()
                    content = element.get_text(strip=True, separator='\n')
                    if content and len(content) > 100:  # 최소 길이 체크
                        print(f"  ✓ 본문 찾음 (선택자: {selector}): {len(content)}자")
                        break
            
            # 본문 못 찾으면 p 태그 모두 수집
            if not content or len(content) < 100:
                print(f"  ⚠️ 선택자로 본문 못 찾음, p 태그 수집 시도...")
                paragraphs = soup.find_all('p')
                content = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                if content:
                    print(f"  ✓ p 태그로 본문 수집: {len(content)}자")
            
            if not content or len(content) < 50:
                print(f"  ✗ 본문을 찾을 수 없거나 너무 짧습니다 ({len(content) if content else 0}자)")
                return None
            
            print(f"  ✅ 기사 수집 성공!")
            return {'title': title, 'content': content}
            
        except requests.exceptions.RequestException as e:
            print(f"  ❌ 네트워크 에러: {e}")
            return None
        except Exception as e:
            print(f"  ❌ 예상치 못한 에러: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def summarize_article(self, title: str, content: str) -> str:
        try:
            max_chars = 10000
            if len(content) > max_chars:
                content = content[:max_chars] + "..."
            
            prompt = f"""다음 기사를 2줄로 요약해주세요. 

형식: 각 줄은 "ㆍ"로 시작하는 불릿 포인트 형태
예시:
ㆍ중대재해법 시행과 정부 특별감독 영향으로 협력업체 선정 기준에서 '안전 역량' 비중 강화 
ㆍ포스코이앤씨는 상생기금·안전관리비 지원, 현대건설은 협력사 안전평가 배점 확대 등 안전 경쟁

제목: {title}

본문:
{content}

요약:"""
            
            print(f"  🤖 Claude API 호출 중...")
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            summary = message.content[0].text.strip()
            print(f"  ✓ 요약 완료: {summary[:50]}...")
            return summary
            
        except Exception as e:
            print(f"  ❌ 요약 에러: {e}")
            return "요약 실패"
    
    def process_urls(self, urls: List[str], output_file: str = "articles_summary.csv", 
                     delay: float = 1.0, save_interval: int = 20):
        results = []
        total = len(urls)
        
        print(f"📰 총 {total}개 기사 처리 시작...")
        print(f"=" * 80)
        
        for idx, url in enumerate(urls, 1):
            print(f"\n[{idx}/{total}] 처리 중: {url}")
            
            article = self.fetch_article(url)
            
            if article:
                summary = self.summarize_article(article['title'], article['content'])
                
                results.append({
                    'URL': url,
                    '제목': article['title'],
                    '요약': summary,
                    '처리시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '상태': '성공'
                })
            else:
                results.append({
                    'URL': url,
                    '제목': '',
                    '요약': '',
                    '처리시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '상태': '실패'
                })
            
            # 중간 저장
            if idx % save_interval == 0 or idx == total:
                self._save_csv(results, output_file)
                success = sum(1 for r in results if r['상태'] == '성공')
                fail = sum(1 for r in results if r['상태'] == '실패')
                print(f"\n💾 진행상황 저장: {idx}/{total} (성공: {success}, 실패: {fail})")
            
            if idx < total:
                time.sleep(delay)
        
        # 최종 통계
        success = sum(1 for r in results if r['상태'] == '성공')
        fail = sum(1 for r in results if r['상태'] == '실패')
        
        print(f"\n{'=' * 80}")
        print(f"🎉 완료! 총 {len(results)}개 처리됨")
        print(f"💾 결과 파일: {output_file}")
        print(f"\n=== 처리 결과 통계 ===")
        print(f"✅ 성공: {success}개")
        print(f"❌ 실패: {fail}개")
        print(f"{'=' * 80}")
    
    def _save_csv(self, results: List[Dict], output_file: str):
        """CSV 저장 (pandas 없이)"""
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
