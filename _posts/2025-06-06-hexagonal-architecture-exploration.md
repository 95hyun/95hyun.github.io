---
layout: post
title: "헥사고날 아키텍처에 대해 알아보았다."
date: 2025-06-06 09:00:00 +0900
categories: [backend/spring]
tags: [헥사고날아키텍처, hexagonal-architecture, 클린아키텍처, 도메인주도설계, ddd, spring, 아키텍처패턴, port-adapter, 계층형아키텍처]
toc: true
toc_sticky: true
---

## 🌟 들어가며

교육 중 총괄님의 코드리뷰를 받던 중 헥사고날 아키텍처에 대한 언급이 있었다. 간단한 예제를 통해 구조를 보여주시고 설명해주셨는데 찾아보니, 최근 도메인 중심 아키텍처 설계에서 점점 많이 언급되고 있는 아키텍처라고 한다.

전통적인 계층형 아키텍처 (Layered Architecture)와 비교하면서 구조적 차이, 장단점, 그리고 왜 헥사고날 아키텍처가 점점 주목받고있는지 알아보고 정리해보았다.

## 🏗️ 기존의 계층형 아키텍처는 어떤 모습인가?

우리가 흔히 사용해왔던 구조는 다음과 같다.

{% highlight text %}
Presentation Layer (Controller)
         ↓
Business Layer (Service)
         ↓
Persistence Layer (Repository)
{% endhighlight %}

이런 아키텍처는 구현이 단순하고, 관심사를 층별로 분리하기 쉬우며, 스프링 프레임워크 같은 현대적인 웹 프레임워크들이 자연스럽게 지원하기 때문에 널리 사용되어 왔다.

하지만 시간이 지나고 프로젝트가 복잡해질수록 몇 가지 문제점이 드러난다.

## ⚠️ 계층형 아키텍처의 한계

### 2.1 도메인 로직의 진입점이 애플리케이션 외부에 있다

대부분의 비즈니스 로직은 Service에 존재하지만, 실제로 외부 요청을 받는 Controller가 시스템 진입점 역할을 한다.

이 구조는 도메인 자체보다 외부 흐름(웹, API 등)에 더 의존적이다.

### 2.2 테스트가 UI/DB 중심이 되기 쉽다

도메인 로직만 테스트하고 싶어도, DB나 Web Layer 없이 테스트하기 어렵다.

결국 테스트 코드도 스프링 컨텍스트, MockMvc, Embedded DB를 계속 띄우게 된다.

### 2.3 외부 의존성과 도메인이 명확히 분리되지 않는다

도메인이 외부 기술 (JPA, Web, Kafka 등)에 직접 노출되는 구조가 되기 쉽다.

`@Entity`, `@Repository`, `@Transactional` 등은 도메인 로직 안에서도 자주 등장한다.

## 🏛️ 헥사고날 아키텍처란?

헥사고날 아키텍처(Hexagonal Architecture)는 2005년, Alistair Cockburn이 제안한 아키텍처 스타일로 다른 이름으로는 "Ports and Adapters Architecture", 혹은 유사 구조로 클린 아키텍처, 온리온 아키텍처 등으로 불리기도 한다.

핵심 철학은 단순하다.

> **비즈니스 로직(도메인)은 시스템의 중심이며, 외부와는 엄격히 분리되어야 한다.**

즉, DB, 웹, 메시징, 파일, 외부 API, 프레임워크는 도메인과 완전히 분리된 "외부 세계"로 간주되며, 이 외부 세계는 반드시 포트(Port)와 어댑터(Adapter)라는 중간 계층을 거쳐 도메인에 접근해야 한다.

## 🔧 아키텍처 구성 설명 (중심 → 바깥 방향)
![아키텍처](/assets/img/posts/2025-06-06-hexagonal-architecture-exploration/1.png)

헥사고날 아키텍처는 이름처럼 육각형처럼 표현되지만, 실제로는 "레이어 구조"에 가깝다. 다만 레이어 간의 방향성과 의존성을 정확히 정의한다는 데 핵심이 있다.

### 4.1 중심 - Domain Core (도메인)
- 엔티티, 밸류 오브젝트, 도메인 서비스 등 핵심 로직이 위치
- 어떤 외부 기술에도 의존하지 않음
- 모든 입/출력은 인터페이스(Port)를 통해 전달됨

### 4.2 포트(Port)
도메인이 외부와 소통하기 위해 정의하는 인터페이스. 일반적으로 두 가지 종류로 나뉜다.

| Port 유형 | 설명 | 예시 |
|-----------|------|------|
| **Inbound Port** | 외부에서 도메인을 호출하는 진입점 | UserUseCase, RegisterServicePort |
| **Outbound Port** | 도메인이 외부 기능을 호출하는 인터페이스 | UserRepository, NotificationSender |

### 4.3 어댑터(Adapter)
포트를 구현하는 실제 코드. 외부 시스템(웹, DB, MQ, 3rd party API 등)과 연결됨.

| Adapter 유형 | 설명 | 예시 |
|--------------|------|------|
| **Inbound Adapter** | Web, REST, GraphQL, CLI | UserController, BatchRunner |
| **Outbound Adapter** | JPA, RestTemplate, Kafka 등 | JpaUserRepository, SlackNotificationSender |

## 💻 예제 코드

회원 등록 서비스로, 사용자가 회원가입을 하면 정보를 저장하고 알림을 보낸다고 가정해보겠다.

먼저 예제코드들에 대한 디렉토리 구조 예시이다.

{% highlight text %}
src/
└── main/
    └── java/
        └── com/example/userservice/
            ├── UserServiceApplication.java     # 애플리케이션 진입점

            ├── domain/                         # 💡 도메인 계층 (순수 비즈니스 로직)
            │   ├── model/
            │   │   └── User.java               # Entity
            │   ├── port/
            │   │   ├── in/
            │   │   │   └── UserRegisterUseCase.java      # Inbound Port (사용자 유스케이스 인터페이스)
            │   │   └── out/
            │   │       ├── UserRepository.java           # Outbound Port (데이터 저장)
            │   │       └── NotificationSender.java       # Outbound Port (알림 전송)
            │   └── service/
            │       └── UserRegisterService.java          # 도메인 유스케이스 구현 (도메인 내부)

            ├── adapter/                       # 💡 어댑터 계층
            │   ├── in/                        # Inbound Adapter (입력, 진입점)
            │   │   └── web/
            │   │       └── UserController.java           # REST API 컨트롤러
            │   └── out/                       # Outbound Adapter (출력, 외부 연결)
            │       ├── persistence/
            │       │   ├── JpaUserRepositoryAdapter.java # JPA 어댑터
            │       │   └── SpringDataJpaRepository.java  # Spring Data 인터페이스
            │       └── notification/
            │           └── SlackNotificationAdapter.java # 알림 전송 어댑터

            └── config/
                └── BeanConfig.java                       # 포트-어댑터 연결 (수동 DI 설정)
{% endhighlight %}

| 디렉토리 | 설명 |
|----------|------|
| **domain/model** | 도메인 엔티티와 밸류 객체 (비즈니스 상태 표현) |
| **domain/port/in** | 외부에서 도메인을 호출할 수 있는 인터페이스 (유스케이스) |
| **domain/port/out** | 도메인이 외부 의존성(DB, 외부 API 등)에 접근하기 위한 인터페이스 |
| **domain/service** | 도메인 유스케이스의 실제 구현체 |
| **adapter/in/web** | 웹 API, CLI, 메시지 핸들러 등 외부 진입점 |
| **adapter/out/persistence** | DB 접근을 위한 어댑터 (JPA, MyBatis, Redis 등) |
| **adapter/out/notification** | 외부 시스템 연동 어댑터 (Slack, Email, REST API 등) |
| **config** | Spring Bean 설정. 어댑터와 포트를 연결하는 수동 DI (또는 @Configuration) |

### 5.1 도메인 계층 (Core Domain)

{% highlight java %}
// User.java - Entity
public class User {
    private final String email;
    private final String name;

    public User(String email, String name) {
        this.email = email;
        this.name = name;
    }

    // getter 생략
}
{% endhighlight %}

{% highlight java %}
// UserRepository.java - Outbound Port
public interface UserRepository {
    void save(User user);
    Optional<User> findByEmail(String email);
}
{% endhighlight %}

{% highlight java %}
// NotificationSender.java - Outbound Port
public interface NotificationSender {
    void sendWelcomeEmail(User user);
}
{% endhighlight %}

{% highlight java %}
// UserRegisterUseCase.java - Inbound Port
public interface UserRegisterUseCase {
    void register(String email, String name);
}
{% endhighlight %}

{% highlight java %}
// UserRegisterService.java - UseCase 구현 (도메인 내부)
public class UserRegisterService implements UserRegisterUseCase {

    private final UserRepository userRepository;
    private final NotificationSender notificationSender;

    public UserRegisterService(UserRepository userRepository, NotificationSender notificationSender) {
        this.userRepository = userRepository;
        this.notificationSender = notificationSender;
    }

    @Override
    public void register(String email, String name) {
        if (userRepository.findByEmail(email).isPresent()) {
            throw new IllegalArgumentException("이미 존재하는 사용자입니다.");
        }
        User user = new User(email, name);
        userRepository.save(user);
        notificationSender.sendWelcomeEmail(user);
    }
}
{% endhighlight %}

### 5.2 어댑터 - 실제 구현

{% highlight java %}
// JpaUserRepositoryAdapter.java - DB 저장소 구현
@Repository
public class JpaUserRepositoryAdapter implements UserRepository {

    private final SpringDataJpaRepository jpaRepository;

    public JpaUserRepositoryAdapter(SpringDataJpaRepository jpaRepository) {
        this.jpaRepository = jpaRepository;
    }

    @Override
    public void save(User user) {
        jpaRepository.save(new UserEntity(user));
    }

    @Override
    public Optional<User> findByEmail(String email) {
        return jpaRepository.findByEmail(email).map(UserEntity::toDomain);
    }
}
{% endhighlight %}

{% highlight java %}
// SlackNotificationAdapter.java
@Component
public class SlackNotificationAdapter implements NotificationSender {

    @Override
    public void sendWelcomeEmail(User user) {
        // Slack API 호출 로직
        System.out.println("Slack 으로 가입 환영 메시지 전송: " + user.getEmail());
    }
}
{% endhighlight %}

### 5.3 웹 어댑터 (Inbound Adapter)

{% highlight java %}
// UserController.java - REST 진입점
@RestController
@RequestMapping("/users")
public class UserController {

    private final UserRegisterUseCase userRegisterUseCase;

    public UserController(UserRegisterUseCase userRegisterUseCase) {
        this.userRegisterUseCase = userRegisterUseCase;
    }

    @PostMapping
    public ResponseEntity<Void> register(@RequestBody UserRequest req) {
        userRegisterUseCase.register(req.email(), req.name());
        return ResponseEntity.ok().build();
    }
}
{% endhighlight %}

## 🤔 왜 이렇게 구성하는가?

### 5.4.1 도메인만 테스트하고 싶을 때, 외부 의존성이 없다

`UserRegisterService`는 단순한 Java 클래스다.

외부 의존성 없이 테스트가 가능하고, Mock 객체만 주입하면 끝이다.

### 5.4.2 의존성 방향이 반대다

기존 계층형 아키텍처에서는 Service -> Repository(JPA) 로 의존하지만, 헥사고날에서는 도메인코드가 Repository의 인터페이스만 바라본다.

즉, JPA, Mongo, 외부 API든 다 구현체(어댑터)에서만 변경하면 된다.

### 5.4.3 진짜 도메인 중심 구조

서비스가 외부 입출력에 끌려다니지 않는다.

어떤 채널 (Web, CLI, Kafka 등) 도 도메인 로직을 동일한 방식으로 재사용 가능하다.

따라서, 테스트, 유지보수, 변경 대응이 훨씬 유연해지게 된다.

## 🎯 마치며

간단하게 알아보며 정리했지만, 다음에는 직접 프로젝트에 적용해보며 헥사고날 아키텍처의 장단점을 직접 느껴봐야겠다.

백문이 불여일타.. 이니까..

마지막으로, 직접 도입해보며 기술적으로 엄청 잘 정리해두신 카카오페이의 기술블로그 글을 첨부한다.

[카카오페이 기술블로그 - 헥사고날 아키텍처 적용기](https://tech.kakaopay.com/post/home-hexagonal-architecture/)