---
layout: post
title: "[k8s] 7. 서비스와 네트워킹 구조 - Kubernetes에서 Pod 간 통신과 외부 노출은 어떻게 동작할까?"
date: 2025-05-21 10:00:00 +0900
categories: [devops/infrastructure]
tags: [kubernetes, k8s, service, networking, ingress, clusterip, nodeport, loadbalancer, coredns, networkpolicy]
toc: true
toc_sticky: true
---

![k8s 썸네일](/assets/img/posts/2025-05-19-k8s-2-cluster-architecture-components/1.png)

## 🌟 들어가며

쿠버네티스는 클러스터 내에 수많은 Pod을 생성하고, 이를 자동으로 복제하고 교체하면서도 서비스는 끊기지 않도록 유지해야 한다. 이를 위해 필수적인 기능이 바로 Service와 네트워크 추상화다.

이번 글에서는 다음과 같은 질문에 대해 정리해본다.

- Pod은 어떻게 서로 통신할까?
- 외부에서 내 서비스를 접근할 수 있게 하려면 어떻게 해야 할까?
- Pod이 없어졌다 다시 생성되면 IP가 바뀌는데, 어떻게 연결을 유지할까?
- 클러스터 내 통신은 안전한가? 제한 가능한가?

## 🌐 쿠버네티스 네트워킹의 기본

쿠버네티스는 다음과 같은 기본 네트워크 모델을 전제로 한다.

- **모든 Pod은 고유한 IP를 가진다.**
- **Pod 간에는 직접 IP로 통신 가능해야 한다.**
- **Node 간, Pod 간 통신은 NAT 없이 평면 네트워크를 구성해야 한다.**
- **외부 접근은 Service, Ingress를 통해 제어한다.**

즉, 모든 Pod는 같은 네트워크 상에 있고, 마치 하나의 거대한 LAN처럼 동작해야 한다.

이 모델을 실현하기 위해 대부분의 클러스터는 CNI(Container Network Interface) 플러그인을 설치한다.

자세한 내용은 아래 공식문서 참고:
[네트워크 플러그인 - Kubernetes 공식 문서](https://kubernetes.io/ko/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)

## 🎯 Service

**Service = Pod들의 추상화된 집합 + 고정된 접근 지점**

Pod는 생성될 때마다 랜덤한 IP를 부여받고, 삭제되면 그 IP도 사라진다. 때문에 Pod를 직접 접근 대상으로 삼는 것은 매우 불안정하다.

쿠버네티스는 이런 불안정성을 해결하기 위해 **Service**라는 리소스를 제공한다.

### 기본 구조 예시

{% highlight yaml %}
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
{% endhighlight %}

- **selector**: 어떤 Pod들과 연결할 것인지 지정 (label 기반)
- **port**: 외부에서 Service에 접근할 포트
- **targetPort**: 연결된 Pod이 실제로 사용하는 포트

이렇게 선언하면, 쿠버네티스는 이 Service에 대해 가상 IP(ClusterIP)를 생성하고, 그 IP로 들어온 요청을 연결된 Pod 중 하나로 라우팅해준다.

## 🚪 Service의 타입들

Service는 접근 대상에 따라 3가지 주요 타입으로 나뉜다.

| 타입 | 설명 |
|------|------|
| **ClusterIP** | 기본값. 클러스터 내부에서만 접근 가능 |
| **NodePort** | 모든 노드의 고정 포트를 열어 외부에서 접근 가능 |
| **LoadBalancer** | 클라우드 환경에서 외부 로드밸런서를 자동으로 생성 |

### ClusterIP

{% highlight yaml %}
type: ClusterIP
{% endhighlight %}

- 클러스터 내부에서만 접근 가능
- 일반적인 내부 마이크로서비스 간 통신에 사용

### NodePort

{% highlight yaml %}
type: NodePort
{% endhighlight %}

- 각 노드의 포트를 고정으로 열고, 외부에서 `노드IP:노드포트`로 접근
- 테스트 환경이나 로컬 개발에 주로 사용

### LoadBalancer

{% highlight yaml %}
type: LoadBalancer
{% endhighlight %}

- 클라우드 서비스(AWS, GCP 등)에서 외부 로드밸런서 생성 자동화
- 실제 외부 서비스 노출용으로 가장 많이 사용됨

## 🔍 CoreDNS - 쿠버네티스 내부 DNS

Service에 접근할 때 IP로 직접 접근하는 것은 비효율적이고 가독성이 떨어진다. 쿠버네티스는 내부 DNS 시스템인 CoreDNS를 통해 각 리소스에 대해 도메인 주소를 자동으로 생성해준다.

{% highlight text %}
<service-name>.<namespace>.svc.cluster.local
{% endhighlight %}

즉, `user-service.default.svc.cluster.local`과 같은 형식으로 네임스페이스를 포함한 DNS 이름으로 Pod이나 Service를 조회할 수 있다.

대부분은 단순히 `http://user-service`만으로도 요청이 가능하다. (기본 namespace 기준)

## 🌐 Ingress - 외부 트래픽을 내부 서비스로 라우팅

Service의 NodePort나 LoadBalancer는 단일 포트 기준의 외부 노출만 가능하다. 하지만 실제 서비스에서는 도메인 기반 라우팅, TLS 인증서, 경로 기반 분기 등이 필요하다.

이를 해결해주는 게 바로 **Ingress**다.

Ingress는 다음 역할을 수행한다:

- `https://api.example.com` → user-service
- `https://example.com/products` → product-service
- TLS 인증서 연결 (Let's Encrypt 연동 가능)

{% highlight yaml %}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: example.com
      http:
        paths:
          - path: /user
            pathType: Prefix
            backend:
              service:
                name: user-service
                port:
                  number: 80
{% endhighlight %}

Ingress를 사용하려면 반드시 Ingress Controller(NGINX 등)가 먼저 설치되어 있어야 한다.

## ⚖️ Ingress vs Spring Cloud Gateway

Spring Boot로 개발한 MSA 서비스를 Kubernetes 환경에서 사용하다 보면 다음과 같은 두 가지 요소를 접하게 된다.

둘 다 트래픽을 라우팅하는 기능을 가지고 있어 헷갈릴 수 있다.

### 개념적 차이

| 항목 | Ingress | Spring Cloud Gateway |
|------|---------|---------------------|
| **위치** | 클러스터 경계 진입점 (L7 Load Balancer) | 클러스터 내부 마이크로서비스의 API 게이트웨이 |
| **동작 위치** | Kubernetes 리소스 (Ingress + Controller) | 애플리케이션 레벨 (Spring Boot 앱) |
| **트래픽 처리 대상** | 외부 → 내부 (서비스 단위 라우팅) | 내부 → 내부 (MSA 단위 API 라우팅 + 보안/필터) |
| **설정 방식** | YAML 기반 (Ingress 리소스 정의) | Java/Kotlin YAML or Java Config |
| **기능 범위** | 도메인/패스 기반 라우팅, TLS 종료 | 라우팅 + 인증 + 필터링 + 로깅 + rate limit 등 |
| **확장성** | Controller마다 다름 (NGINX, Traefik 등) | 코드 수준에서 자유롭게 확장 가능 |

### 구조적 차이

![k8s 썸네일](/assets/img/posts/2025-05-21-k8s-7-service-networking/1.jpeg)

{% highlight text %}
[외부 요청]
     |
     v
[Ingress Controller (예: NGINX)]
     |
     v
[Spring Cloud Gateway 서비스 (내부 Pod)]
     |
     v
[개별 마이크로서비스들]
{% endhighlight %}

- **Ingress**는 클러스터 입구로서 외부 트래픽을 적절한 서비스로 분배해주는 Load Balancer 역할이다.
- **Spring Cloud Gateway**는 내부의 하나의 서비스로, 주로 인증, 필터링, 로깅, 속도 제한 등의 기능을 수행하는 API Gateway 역할이다.

즉 목적 자체가 다르다.

## 🛡️ NetworkPolicy - 네트워크 통신 제어 방화벽

쿠버네티스는 기본적으로 모든 Pod 간 통신이 허용되어있다. 하지만 보안이나 멀티테넌시 환경에서는 이 통신을 제한해야 할 경우가 많다.

이때 사용하는 리소스가 **NetworkPolicy**다.

이를 통해 다음과 같은 설정이 가능하다:
- 특정 namespace의 Pod 끼리만 통신을 허용
- 외부 요청은 Ingress Controller만 받게 설정
- DB Pod는 특정 앱 Pod만 접근 가능하게 등

{% highlight yaml %}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web
spec:
  podSelector:
    matchLabels:
      role: db
  ingress:
    - from:
        - podSelector:
            matchLabels:
              access: web
{% endhighlight %}

예시로 특정 label을 가진 Pod만 접근 허용하는 경우다.

네트워크 정책이 동작하려면 CNI 플러그인이 NetworkPolicy를 지원해야 한다.

### 멀티테넌시 환경?

[멀티 테넌시(multi-tenancy) - Kubernetes 공식 문서](https://kubernetes.io/ko/docs/concepts/security/multi-tenancy/)

**멀티테넌시(Multi-tenancy)**는 하나의 시스템(예: 소프트웨어, 클라우드 인프라, 쿠버네티스 클러스터 등)이 여러 사용자(테넌트)에게 서비스를 제공하는 아키텍처를 의미한다. 여기서 테넌트란 회사, 팀, 프로젝트, 고객 등 논리적으로 분리된 사용자 집단을 말한다.

#### 주요 특징

- **리소스 공유**: 여러 테넌트가 하나의 시스템 인스턴스(예: 쿠버네티스 클러스터, 데이터베이스, 애플리케이션)를 공유
- **논리적 격리**: 각 테넌트는 독립적인 환경처럼 느끼지만, 실제로는 물리적으로 같은 시스템을 사용한다. 데이터, 네트워크, 리소스 등이 서로 분리되어야 하며, 무단 접근이 없어야 함.
- **효율성**: 시스템을 여러 번 구축하지 않고도 여러 고객이나 팀에 서비스를 제공할 수 있어, 비용과 운영 효율성이 높아진다.

#### 쿠버네티스에서의 멀티테넌시

쿠버네티스에서는 한 클러스터를 여러 팀이나 프로젝트가 네임스페이스, RBAC(권한 관리), 리소스 쿼터, 네트워크 정책 등을 통해 논리적으로 분리해서 사용하는 것이 대표적인 멀티테넌시 사례이다.

예를 들어, 한 회사의 개발팀과 운영팀이 같은 클러스터를 사용하더라도, 각 팀의 파드와 서비스는 네임스페이스로 분리하고, 네트워크 정책(NetworkPolicy)으로 서로의 통신을 제한할 수 있다. 이를 통해 보안과 독립성을 보장한다.