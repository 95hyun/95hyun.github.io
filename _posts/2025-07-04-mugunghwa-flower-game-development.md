---
layout: post
title: "'무궁화 꽃이 피었습니다' 순서 추첨 웹게임 개발기"
date: 2025-07-04 09:00:00 +0900
categories: [frontend/react]
tags: [react, typescript, 웹게임, 순서추첨, 무궁화꽃이피었습니다, 게임개발, custom-hooks, 상태관리, useEffect, useState]
toc: true
toc_sticky: true
---
![게임 화면1](/assets/img/posts/2025-07-04-mugunghwa-flower-game-development/1.png)
![게임 화면2](/assets/img/posts/2025-07-04-mugunghwa-flower-game-development/2.png)

React와 TypeScript를 사용해 어린 시절의 추억이 담긴 '무궁화 꽃이 피었습니다' 게임을 웹으로 구현한 프로젝트 'mugunghwa'의 개발기를 적어보려고 합니다.

단순한 게임처럼 보이지만, 실시간 상태 동기화와 사용자 입력 처리에 있어 흥미로운 기술적 도전들이 있었습니다. 이 글에서는 특히 게임의 핵심 로직을 어떻게 설계하고 Custom Hooks로 분리했는지에 초점을 맞춰 이야기해 보겠습니다.

## 🎯 무궁화 꽃이 피었습니다로 순서 추첨?

백엔드 서버 구매 없이 간단한 프론트엔드 개발을 하고 싶었던 차에 방송인들이나 많은 사람들이 순서 추첨에 핀볼 추첨 웹 게임을 사용하는걸 보고 나도 저런거 하나 만들어두고 방치(?) 해두고 싶다 라는 생각에 개발하게 되었습니다.

오징어게임으로도 유명한 우리나라 전통 놀이 '무궁화 꽃이 피었습니다'의 Rule을 그대로 가져와서 아래의 간단한 규칙들로 순서를 추첨합니다.

1. 참가자들은 골인 지점까지 랜덤하게 전진합니다.
2. 술래는 '무궁화 꽃이 피었습니다'를 한 음절씩 랜덤한 속도로 외치고, 다 외치면 뒤돌아 봅니다.
3. 술래가 뒤돌아봤을때 전진하고 있던 참가자는 탈락합니다.
4. 등수(순서)는 골인 여부 + 전진 거리 로 배정됩니다.

PC뷰, 모바일뷰 반응형 최적화하였고, 게임 결과 공유 버튼을 누르면 등수 결과가 클립보드에 복사되어 다른 곳에 붙여넣기 할 수 있도록 만들었습니다.

구글 SEO 최적화도 조금 신경썻는데, React19를 사용했기 때문에 React Helmet은 의존성 충돌로 사용하지 못하고 React19에서 공식 지원하는 Document metadata를 사용했습니다.

![게임 화면3](/assets/img/posts/2025-07-04-mugunghwa-flower-game-development/3.png)
![게임 화면4](/assets/img/posts/2025-07-04-mugunghwa-flower-game-development/4.png)

*술래에게 걸리면 탈락할 수 있어서 역전당할 수 있어요*

## 🏗️ 프로젝트 아키텍처: 상태와 뷰의 분리

React 프로젝트의 핵심은 '상태(State)가 뷰(View)를 결정한다'는 것입니다. 저희는 이 원칙을 충실히 따르기 위해 게임의 모든 로직과 상태를 `useGameLogic`이라는 Custom Hook에 위임하고, 컴포넌트들은 이 훅이 제공하는 상태를 받아 렌더링에만 집중하도록 설계했습니다.

{% highlight text %}
GamePage.tsx
 │
 ├── useGameLogic.ts (게임의 모든 상태와 로직 관리)
 │
 ├── GameHeader.tsx (점수, 시간 등 표시)
 ├── GameField.tsx (플레이어, 술래 등 게임 필드)
 ├── SyllableOverlay.tsx ('무궁화 꽃이 피었습니다' 텍스트)
 └── GameOverlays.tsx (게임 결과 알림)
{% endhighlight %}

이 구조 덕분에 게임 로직의 변경이 UI 컴포넌트에 미치는 영향을 최소화할 수 있었고, 복잡한 게임 상태를 중앙에서 관리하여 디버깅을 용이하게 만들었습니다.

## 🧠 게임의 두뇌: 'useGameLogic' 커스텀 훅

`useGameLogic.ts`는 이 게임의 심장과도 같습니다. 내부적으로 `useState`와 `useReducer`를 사용하여 다음과 같은 핵심 상태들을 관리합니다.

- **gameState**: READY, PLAYING, RED_LIGHT, GREEN_LIGHT, CAUGHT, FINISHED 등 게임의 현재 상태
- **playerPosition**: 플레이어의 현재 위치
- **taggerCall**: 술래가 외치는 구호 ('무궁화 꽃이 피었습니다')의 진행 상태

`useEffect`를 사용하여 `gameState`가 변경될 때마다 게임의 흐름을 제어합니다. 예를 들어, GREEN_LIGHT 상태에서는 플레이어가 움직일 수 있도록 허용하고, `setTimeout`으로 다음 RED_LIGHT 상태를 예약합니다.

{% highlight typescript %}
// src/hooks/useGameLogic.ts (개념 코드)

export const useGameLogic = () => {
  const [gameState, setGameState] = useState('READY');
  const [playerPosition, setPlayerPosition] = useState(0);

  // 'RED_LIGHT' 상태 감지 로직
  useEffect(() => {
    if (gameState !== 'RED_LIGHT') return;

    const handleMovement = (event: KeyboardEvent) => {
      // 이 상태에서 움직임이 감지되면 'CAUGHT' 상태로 변경
      setGameState('CAUGHT');
    };

    window.addEventListener('keydown', handleMovement);
    return () => window.removeEventListener('keydown', handleMovement);
  }, [gameState]);

  // 'GREEN_LIGHT' 상태에서 전진 로직
  const moveForward = () => {
    if (gameState === 'GREEN_LIGHT') {
      setPlayerPosition(pos => pos + 1);
    }
  };

  return { gameState, playerPosition, moveForward };
};
{% endhighlight %}

## 🔍 가장 까다로웠던 부분: '움직임'을 어떻게 감지할 것인가?

'무궁화 꽃이 피었습니다'의 핵심은 술래가 뒤를 돌아봤을 때(RED_LIGHT) 움직이는 사람을 잡아내는 것입니다. 저희는 이 로직을 다음과 같이 구현했습니다.

1. `gameState`가 RED_LIGHT로 변경되는 순간, window에 keydown 이벤트를 리스너를 등록합니다.
2. 플레이어가 어떤 키든 누르면, 즉시 `gameState`를 CAUGHT로 변경하여 탈락처리합니다.
3. `gameState`가 다시 GREEN_LIGHT로 바뀌면, `useEffect`의 cleanup 함수를 통해 이벤트 리스너를 제거하여 불필요한 감지를 방지합니다.

이 간단한 아이디어 덕분에 'RED_LIGHT' 상태에서의 모든 키보드 입력을 '움직임'으로 간주하여 긴장감 넘치는 게임 플레이를 구현할 수 있었습니다.

## 🎮 마치며

![게임 화면5](/assets/img/posts/2025-07-04-mugunghwa-flower-game-development/5.png)

'Mugunghwa' 프로젝트는 단순한 토이프로젝트를 넘어 React의 상태 관리와 Custom Hooks의 중요성을 다시 한번 체감하게 된 계기였습니다. 특히 복잡한 인터랙션과 상태 변화를 가진 애플리케이션일수록, 로직과 뷰를 분리하는 설계가 얼마나 중요한지 깨달을 수 있었습니다.

프로젝트는 현재 GitHub에 공개되어 있으며, 배포된 링크를 통해 직접 플레이해보실 수도 있습니다.

- **게임 플레이**: [https://mugunghwarun.netlify.app/](https://mugunghwarun.netlify.app/)
- **GitHub 저장소**: [https://github.com/95hyun/mugunghwa](https://github.com/95hyun/mugunghwa)