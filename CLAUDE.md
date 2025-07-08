# Jekyll + Chirpy 블로그 포스팅 Rule Memory

## 📝 Jekyll 포스트 작성 규칙

### Front Matter 필수 구조
```yaml
---
layout: post                    # 필수! CSS 적용을 위해
title: "포스트 제목"
date: YYYY-MM-DD HH:MM:SS +0900
categories: [카테고리]           # 대괄호 형식
tags: [tag1, tag2, tag3]        # 대괄호 형식  
toc: true                       # 목차 표시
toc_sticky: true                # 목차 고정
---
```

### 파일명 및 위치 규칙
- **파일명 형식**: `YYYY-MM-DD-title.md`
- **저장 위치**: `_posts/` 폴더
- **파일명 생성**: 특수문자 제거, 공백을 하이픈으로 변경, 소문자 변환

### 이미지 처리 규칙
- **기본 확장자**: `.jpeg`
- **저장 경로**: `/assets/img/posts/YYYY-MM-DD-post-title/`
- **마크다운 참조**: `![설명](/assets/img/posts/YYYY-MM-DD-post-title/image.jpeg)`
- **캡션 형식**: 이미지 아래에 `*설명*` 형식으로 추가

### 콘텐츠 구조 규칙
- **헤딩**: `##`, `###` 사용 (이모지 활용 권장)
- **인용구**: `> 텍스트` 형식
- **강조**: `**텍스트**` 형식
- **리스트**: `-` 또는 `1.` 형식

### 코드 하이라이팅 규칙
Jekyll의 highlight 블록 사용:
```
{% highlight language %}
코드 내용
{% endhighlight %}
```

**지원 언어**: python, java, javascript, bash, yaml, json, html, css 등

## 🔄 Tistory → Jekyll 변환 프로세스

### 1. 사용자 입력 형식
```
날짜: YYYY.MM.DD
카테고리: 카테고리명
제목: 포스트 제목
내용:
[Tistory 포스트 내용]
```

### 2. 변환 작업 순서
1. **Front Matter 생성**
   - layout: post 필수 포함
   - 날짜를 Jekyll 형식으로 변환
   - 카테고리와 태그를 대괄호 형식으로 변환

2. **콘텐츠 변환**
   - HTML → Markdown 변환
   - 헤딩 구조 정리 (이모지 추가)
   - 리스트 형식 정리
   - 인용구 형식 적용

3. **코드 블록 변환**
   - ````language` → `{% highlight language %}`
   - 적절한 언어 지정

4. **이미지 처리**
   - 이미지 경로를 Jekyll 형식으로 변경
   - 확장자를 .jpeg로 통일
   - 캡션을 *텍스트* 형식으로 변경

5. **파일 생성**
   - 적절한 파일명으로 `_posts/` 폴더에 저장

### 3. 카테고리 매핑 (현재 블로그 구조)
**중요**: Jekyll 카테고리는 소문자와 슬래시 형식 사용

**Backend**:
- [backend/java] → Backend > Java
- [backend/spring] → Backend > Spring  
- [backend/kafka] → Backend > Kafka
- [backend/database] → Backend > Database

**Frontend**:
- [frontend/react] → Frontend > React
- [frontend/typescript] → Frontend > TypeScript

**DevOps**:
- [devops/monitoring] → DevOps > Monitoring
- [devops/infrastructure] → DevOps > Infrastructure
- [devops/git] → DevOps > Git

**Experience**:
- [experience/bootcamp] → Experience > 부트캠프
- [experience/activity] → Experience > 대외활동
- [experience/troubleshooting] → Experience > 트러블슈팅

**AI-Tech**:
- [aitech/genai] → AI-Tech > GenAI

**Thoughts**:
- [thoughts] → Thoughts

**카테고리 판단 기준**:
- 사용자가 "Experience/activity" 형식으로 지정하면 [experience/activity]로 변환
- 모든 카테고리는 소문자, 슬래시 형식으로 작성
- 카테고리 페이지의 category 필드와 정확히 매칭되어야 함

### 4. 주의사항
- 모든 포스트에 `layout: post` 필수 포함
- 날짜 형식 통일: `YYYY-MM-DD HH:MM:SS +0900`
- 이미지는 사용자가 별도 추가 예정
- 코드 블록은 Jekyll highlight 형식 사용

## 🛠️ 활용 도구
- `convert_post.py`: 대화형 변환 도구
- `post_template.md`: Jekyll 포스트 템플릿
- `migrate_tistory.py`: RSS 기반 자동 마이그레이션

## ✅ 블로그 기본 정보
- **플랫폼**: Jekyll 4.4.1 + Chirpy 7.0
- **배포**: GitHub Actions → GitHub Pages  
- **URL**: https://95hyun.github.io
- **완료 기능**: 카테고리 네비게이션, 댓글, SEO, 방문자 카운터