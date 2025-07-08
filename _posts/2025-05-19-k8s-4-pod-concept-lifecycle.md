---
layout: post
title: "[k8s] 4. Pod의 개념과 생명 주기"
date: 2025-05-19 12:00:00 +0900
categories: [devops/infrastructure]
tags: [kubernetes, k8s, pod, 컨테이너, 생명주기, lifecycle, 네트워크, 볼륨, 멀티컨테이너, 사이드카]
toc: true
toc_sticky: true
---

![k8s 썸네일](/assets/img/posts/2025-05-19-k8s-2-cluster-architecture-components/1.png)

## 🌟 들어가며

쿠버네티스의 모든 실행 단위는 결국 Pod에서 시작된다. Pod는 우리가 실행하는 컨테이너의 직접적인 실행 환경이자, 쿠버네티스에서 가장 기본적인 단위다.

"쿠버네티스는 컨테이너를 관리한다"라고 말하지만, 정확히는 "컨테이너를 Pod이라는 추상화로 감싸서 관리한다"고 보는 게 맞다. 이번 글에서는 Pod이란 무엇인지, 어떤 구조로 되어 있는지, 어떤 식으로 동작하는지 정리해본다.

## 🧊 Pod란 무엇인가

Pod는 하나 이상의 컨테이너를 실행할 수 있는 논리적 단위로, 쿠버네티스에서 컨테이너가 배치되는 기본 단위다. 간단히 말하면, **Pod = 컨테이너 + 실행에 필요한 환경(네트워크, 볼륨, 설정 등)을 묶어놓은 상자**라고 생각하면 된다.

보통은 하나의 컨테이너를 하나의 Pod으로 실행하지만, 여러 개의 컨테이너를 한 Pod 안에 넣는 구성도 가능하다.

Pod 안에 있는 컨테이너들은 다음 자원을 공유한다:

- **네트워크 네임스페이스 (IP, 포트)**
- **스토리지 볼륨 (Volume)**
- **localhost 통신**

이런 이유로 긴밀하게 협업이 필요한 컨테이너들은 하나의 Pod에 넣는 방식으로 구성한다.

## 🔧 Pod, 단일 컨테이너 vs 멀티 컨테이너

### 단일 컨테이너 Pod

가장 흔한 구성이다. 실제로 대부분의 Pod는 단일 컨테이너만 실행한다. YAML 구조도 간단하고 관리도 쉽다.

{% highlight yaml %}
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:latest
{% endhighlight %}

### 멀티 컨테이너 Pod

컨테이너 간 tight coupling(강한 결합)이 필요할 때 사용한다. 대표적인 예: 사이드카(Sidecar), 앰배서더(Ambassador), 어댑터(Adapter) 패턴

{% highlight yaml %}
spec:
  containers:
    - name: main-app
      image: my-app
    - name: log-sidecar
      image: log-collector
{% endhighlight %}

- **사이드카 패턴**: 주 컨테이너의 기능을 보완 (예: 로그 수집, 프록시)
- **앰배서더 패턴**: 외부와의 통신을 중계
- **어댑터 패턴**: 데이터를 형변환, 포맷 변환 등

멀티 컨테이너는 설정과 디버깅이 복잡하므로 신중하게 사용해야 한다.

나는 lg cns camp 최종 프로젝트의 관제 시스템 구성을 위해서 각 파드에 사이드카로 fluentbit을 띄웠다.

## 🔄 Pod의 생명주기

Pod도 상태(State)를 가지며, 생성부터 종료까지 일련의 과정을 가진다.

![Pod 생명주기](/assets/img/posts/2025-05-19-k8s-4-pod-concept-lifecycle/1.jpeg)

다음은 Pod의 대표적인 상태들이다.

| 상태 | 설명 |
|------|------|
| **Pending** | Pod가 생성되었지만, 아직 컨테이너가 실행되기 전 |
| **Running** | 하나 이상의 컨테이너가 실행 중 |
| **Succeeded** | 모든 컨테이너가 정상 종료 (성공) |
| **Failed** | 하나 이상의 컨테이너가 비정상 종료 |
| **Unknown** | 노드에 연결할 수 없어 상태를 알 수 없음 |

Pod는 기본적으로 종료된 후 자동 재시작되지 않는다. 이 때문에 실제 운영에선 Pod만으로 애플리케이션을 배포하지 않고, Deployment나 ReplicaSet 같은 상위 리소스로 관리한다.

## 🔄 Pod 재시작 정책 (restartPolicy)

Pod 수준에서 재시작 정책을 설정할 수 있다.

{% highlight yaml %}
spec:
  restartPolicy: Always # 기본값
{% endhighlight %}

- **Always**: 컨테이너가 죽으면 항상 재시작 (Deployment 등에서 사용됨)
- **OnFailure**: 실패했을 때만 재시작
- **Never**: 절대 재시작하지 않음 (Job, 수동 테스트 등에서 사용)

## 🌐 Pod의 IP와 네트워크

![Pod의 IP와 네트워크](/assets/img/posts/2025-05-19-k8s-4-pod-concept-lifecycle/1.jpeg)

Pod는 생성될 때 클러스터 내 고유한 IP 주소를 부여받는다. 동일 노드든 다른 노드든 관계없이 Pod 간 직접 통신이 가능하며, 이건 쿠버네티스 네트워크 모델의 핵심이다.

{% highlight text %}
Pod A (10.244.0.2) --> Pod B (10.244.1.5)
{% endhighlight %}

하지만 Pod는 삭제되면 IP도 바뀐다. 그래서 직접 IP로 접근하기보다는 Service 리소스를 통해 안정적인 네트워크 경로를 제공한다. (이후 글에서 정리)

### Pod의 IP, 포트와 Pod의 컨테이너 안에서 실행되는 애플리케이션의 IP, 포트

쿠버네티스에서 Pod, 컨테이너, 그리고 그 안에서 실행되는 Spring Boot 애플리케이션의 IP와 포트 개념이 헷갈릴 수 있다.

일단 Spring Boot는 기본 8080포트로 실행된다. 근데, Pod 내 컨테이너로 실행되어 있기 때문에 해당 Spring boot에 요청을 보내기 위해서는 `{Pod IP : Spring Boot port}`가 된다.

하지만, Pod IP는 위에 말했 듯 삭제되면 IP가 변경되기 때문에 직접 IP 접근하기보다 Service를 통해 고정된 가상 IP를 제공하고, 이 IP로 들어온 요청을 실제 Pod IP로 라우팅 해준다.

### 그럼 MSA의 경우에는 어떨까?

spring으로 개발된 msa의 경우 spring cloud gateway를 보통 사용하게 된다.

그러면 gateway, 각 마이크로 서비스가 모두 pod로 띄워져있을 때 ip:port 는 어떻게 되는걸까?

#### 외부에서 접근 가능한 IP : 포트

쿠버네티스 클러스터에서 외부(인터넷, 회사 내부망 등)에서 직접 접근할 수 있는 IP와 포트는 "Service" 리소스의 타입에 따라 달라진다. Spring Cloud Gateway도 하나의 마이크로서비스처럼 Pod 안에서 실행되고, 반드시 Service로 노출해야 외부에서 접근할 수 있다.

일반적으로 외부 노출이 필요한 서비스(Gateway 등)는 Service 타입을 LoadBalancer 또는 NodePort로 설정한다.

**LoadBalancer 타입:**
- 클라우드 환경(GCP, AWS 등)에서는 외부에 할당된 퍼블릭 IP(예: 104.198.205.71)와 지정 포트(예: 80, 443 등)로 접근한다.
- 예) `http://104.198.205.71:80`
- 이 IP와 포트가 외부에서 접근 가능한 주소.

**NodePort 타입:**
- 클러스터의 각 노드(서버) IP와 할당된 NodePort(기본 30000~32767 포트)로 접근한다.
- 예) `http://<노드IP>:30080`

**Ingress(로드밸런서/프록시):**
- Ingress 리소스를 사용하면, 도메인 기반(예: my-api.example.com)으로도 접근할 수 있다.

#### 실제로 API 요청을 보내야 하는 IP : 포트

**(1) 외부 클라이언트 → Gateway**

외부에서 API 요청을 보낼 때는 Gateway의 Service에 할당된 외부 IP와 포트를 사용한다.

예시: `http://104.198.205.71:80/api/orders`  
(여기서 104.198.205.71은 Gateway Service의 LoadBalancer IP)

**(2) Gateway → 각 마이크로서비스**

Gateway는 클러스터 내부에서 각 마이크로서비스의 Service 이름과 포트로 요청을 전달한다.

주문 서비스가 `order-service`라는 이름의 Service로 8080 포트에 노출되어 있다면, Gateway는 내부적으로 `http://order-service:8080`으로 라우팅한다.

이때 Pod의 IP:포트로 직접 접근하지 않고, 반드시 Service를 통해 접근한다. (Pod IP는 동적으로 바뀌기 때문에 직접 사용 X)

## 🎯 마치며

Pod는 단일 또는 다중 컨테이너의 실행 단위이며, 네트워크, 스토리지, 설정을 함께 묶어주는 역할을 한다.

IP 포트 쪽에 대해서 내부 컨테이너 IP, 포트와 헷갈렸었는데 이번에 정리하면서 개념이 좀 잡힌 것 같아 다행이다.