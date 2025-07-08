#!/usr/bin/env python3
"""
간단한 포스트 변환 도구
붙여넣은 내용을 Jekyll 포스트로 변환
"""

import html2text
from datetime import datetime
import re

def convert_to_jekyll_post():
    """대화형 포스트 변환"""
    print("🔄 Tistory → Jekyll 포스트 변환기")
    print("=" * 40)
    
    # 기본 정보 입력
    title = input("포스트 제목: ")
    date_str = input("작성일 (YYYY-MM-DD, 엔터시 오늘): ").strip()
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    categories = input("카테고리 (쉼표로 구분): ").split(',')
    categories = [cat.strip() for cat in categories if cat.strip()]
    
    tags = input("태그 (쉼표로 구분): ").split(',')
    tags = [tag.strip() for tag in tags if tag.strip()]
    
    print("\n📝 포스트 내용을 붙여넣고 엔터 두 번 누르세요:")
    print("(HTML 또는 일반 텍스트)")
    
    # 멀티라인 입력
    content_lines = []
    empty_lines = 0
    
    while True:
        line = input()
        if line.strip() == "":
            empty_lines += 1
            if empty_lines >= 2:
                break
        else:
            empty_lines = 0
            content_lines.append(line)
    
    content = '\n'.join(content_lines)
    
    # HTML을 Markdown으로 변환
    if '<' in content and '>' in content:
        h2t = html2text.HTML2Text()
        h2t.ignore_links = False
        h2t.ignore_images = False
        content = h2t.handle(content)
    
    # 파일명 생성
    filename_title = re.sub(r'[^\w\s-]', '', title)
    filename_title = re.sub(r'[-\s]+', '-', filename_title).strip('-').lower()
    filename = f"{date_str}-{filename_title}.md"
    
    # Front Matter 생성
    front_matter = f"""---
title: "{title}"
date: {date_str} 09:00:00 +0900
categories: {categories}
tags: {tags}
toc: true
toc_sticky: true
---

"""
    
    # 최종 파일 생성
    final_content = front_matter + content.strip()
    
    # 파일 저장
    output_path = f"_posts/{filename}"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"\n✅ 변환 완료!")
    print(f"📁 파일 위치: {output_path}")
    print(f"🔗 파일명: {filename}")

if __name__ == "__main__":
    convert_to_jekyll_post()