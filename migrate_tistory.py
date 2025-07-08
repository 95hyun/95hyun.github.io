#!/usr/bin/env python3
"""
Tistory RSS 피드를 Jekyll 포스트로 변환하는 스크립트

Usage:
    python migrate_tistory.py
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
import html2text
import urllib.parse
from urllib.parse import urljoin, urlparse
import time

class TistoryMigrator:
    def __init__(self, blog_url, output_dir="_posts"):
        self.blog_url = blog_url
        self.rss_url = f"{blog_url}/rss"
        self.output_dir = output_dir
        self.image_dir = "assets/img/posts"
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        self.h2t.ignore_emphasis = False
        
    def fetch_rss_feed(self):
        """RSS 피드 가져오기"""
        try:
            print(f"RSS 피드 가져오는 중: {self.rss_url}")
            feed = feedparser.parse(self.rss_url)
            print(f"총 {len(feed.entries)}개의 포스트 발견")
            return feed
        except Exception as e:
            print(f"RSS 피드 가져오기 실패: {e}")
            return None
    
    def clean_title(self, title):
        """파일명에 사용할 수 있도록 제목 정리"""
        # 특수문자 제거 및 공백을 하이픈으로 변경
        title = re.sub(r'[^\w\s-]', '', title)
        title = re.sub(r'[-\s]+', '-', title)
        return title.strip('-').lower()
    
    def extract_images(self, html_content, post_slug):
        """HTML에서 이미지 추출 및 로컬 저장"""
        soup = BeautifulSoup(html_content, 'html.parser')
        images = soup.find_all('img')
        
        post_image_dir = os.path.join(self.image_dir, post_slug)
        if images and not os.path.exists(post_image_dir):
            os.makedirs(post_image_dir, exist_ok=True)
        
        for i, img in enumerate(images):
            src = img.get('src')
            if not src:
                continue
                
            # 상대 URL을 절대 URL로 변환
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = urljoin(self.blog_url, src)
            
            try:
                # 이미지 다운로드
                response = requests.get(src, timeout=10)
                response.raise_for_status()
                
                # 파일 확장자 추출
                parsed_url = urlparse(src)
                filename = os.path.basename(parsed_url.path)
                if not filename or '.' not in filename:
                    filename = f"image_{i+1}.jpg"
                
                # 로컬 파일 저장
                local_path = os.path.join(post_image_dir, filename)
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                # HTML에서 이미지 경로 수정
                new_src = f"/{post_image_dir}/{filename}"
                img['src'] = new_src
                
                print(f"이미지 저장: {new_src}")
                
            except Exception as e:
                print(f"이미지 다운로드 실패 ({src}): {e}")
                continue
            
            # 요청 간격 (서버 부하 방지)
            time.sleep(0.5)
        
        return str(soup)
    
    def html_to_markdown(self, html_content):
        """HTML을 Markdown으로 변환"""
        # BeautifulSoup으로 HTML 정리
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 불필요한 태그 제거
        for tag in soup(['script', 'style', 'meta', 'link']):
            tag.decompose()
        
        # HTML을 Markdown으로 변환
        markdown = self.h2t.handle(str(soup))
        
        # 마크다운 정리
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)  # 중복 줄바꿈 제거
        markdown = markdown.strip()
        
        return markdown
    
    def create_jekyll_post(self, entry):
        """Jekyll 포스트 파일 생성"""
        # 제목 및 날짜 추출
        title = entry.title
        pub_date = datetime(*entry.published_parsed[:6])
        
        # 카테고리 추출
        categories = []
        if hasattr(entry, 'tags') and entry.tags:
            categories = [tag.term for tag in entry.tags]
        
        # 파일명 생성
        post_slug = self.clean_title(title)
        filename = f"{pub_date.strftime('%Y-%m-%d')}-{post_slug}.md"
        
        # 이미지 처리
        html_content = entry.description
        html_content = self.extract_images(html_content, post_slug)
        
        # Markdown 변환
        markdown_content = self.html_to_markdown(html_content)
        
        # Front Matter 생성
        front_matter = f"""---
title: "{title}"
date: {pub_date.strftime('%Y-%m-%d %H:%M:%S')} +0900
categories: {categories}
tags: {categories}
toc: true
toc_sticky: true
original_url: "{entry.link}"
migrated_from: "tistory"
---

"""
        
        # 최종 콘텐츠
        final_content = front_matter + markdown_content
        
        # 파일 저장
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"포스트 생성: {output_path}")
        return output_path
    
    def migrate_all_posts(self):
        """모든 포스트 마이그레이션"""
        # 출력 디렉토리 생성
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
        
        # RSS 피드 가져오기
        feed = self.fetch_rss_feed()
        if not feed:
            return
        
        # 각 포스트 처리
        for entry in feed.entries:
            try:
                self.create_jekyll_post(entry)
                time.sleep(1)  # 서버 부하 방지
            except Exception as e:
                print(f"포스트 처리 실패 ({entry.title}): {e}")
                continue
        
        print(f"\n마이그레이션 완료! 총 {len(feed.entries)}개 포스트 처리")
        print(f"출력 디렉토리: {self.output_dir}")
        print(f"이미지 디렉토리: {self.image_dir}")


def main():
    """메인 실행 함수"""
    blog_url = "https://helloresekai.tistory.com"
    
    print("🚀 Tistory → Jekyll 마이그레이션 시작")
    print("=" * 50)
    
    migrator = TistoryMigrator(blog_url)
    migrator.migrate_all_posts()
    
    print("\n✅ 마이그레이션 완료!")
    print("\n📋 후속 작업:")
    print("1. 생성된 포스트 파일 검토")
    print("2. 이미지 경로 확인")
    print("3. 카테고리 및 태그 정리")
    print("4. Jekyll 빌드 테스트")


if __name__ == "__main__":
    main()