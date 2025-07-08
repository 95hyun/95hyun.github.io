---
layout: post
title: "[k8s] 9. 인증과 보안을 다루는 쿠버네티스의 몇가지 방법들"
date: 2025-05-22 09:00:00 +0900
categories: [devops/infrastructure]
tags: [kubernetes, k8s, rbac, serviceaccount, security, authentication, authorization, podsecurity, networkpolicy, 보안, 인증, 권한관리]
toc: true
toc_sticky: true
---

![k8s 썸네일](/assets/img/posts/2025-05-19-k8s-2-cluster-architecture-components/1.png)

## 🌟 들어가며

쿠버네티스는 매우 유연하고 강력한 플랫폼이지만, 그만큼 보안이 제대로 설정되지 않으면 무방비 상태의 뒷문이 열려 있는 셈이다.

- 누가 클러스터에 접근할 수 있는가?
- 어떤 리소스를 읽고, 생성하고, 삭제할 수 있는가?
- 어떤 Pod이 누구와 통신할 수 있어야 하는가?
- 애플리케이션이 실행되는 환경은 충분히 안전한가?

이 모든 질문은 쿠버네티스의 보안 모델(Security Model)에 의해 결정된다.

이 글에서는 다음 4가지를 중심으로 보안 기능을 정리해본다.

## 🔐 RBAC - 리소스 접근 권한을 제어하는 시스템

RBAC를 처음 알게된건 argoCD로 쿠버네티스 CD를 맡았을 때 처음 접하게 되었다.

RBAC(Role-Based Access Control)은 사용자 또는 서비스 계정이 어떤 리소스를 어떤 권한으로 접근할 수 있는지 제어하는 쿠버네티스의 권한 관리 시스템이다.

| 리소스 | 설명 |
|--------|------|
| **Role** | 특정 namespace 내 권한 묶음 |
| **ClusterRole** | 전체 클러스터 수준 권한 묶음 |
| **RoleBinding** | Role을 사용자/SA에 연결 |
| **ClusterRoleBinding** | ClusterRole을 사용자/SA에 연결 |

아래 yaml 예시들을 살펴보자.

{% highlight yaml %}
kind: Role
metadata:
  name: pod-reader
  namespace: default
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
{% endhighlight %}

이 Role은 default namespace 내의 pods 리소스에 대해 get, list 권한만 부여한다.

{% highlight yaml %}
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
  - kind: ServiceAccount
    name: my-sa
    namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
{% endhighlight %}

해당 Role을 특정 ServiceAccount에 바인딩한다.

결과적으로, `default:my-sa`는 default namespace 내의 Pod 목록만 조회할 수 있게 된다.

### 🔒 최소 권한 원칙(Principle of Least Privilege)

RBAC를 사용할 때 가장 중요한 원칙은, **필요한 최소 권한만 부여하라**이다.

너무 광범위하게 ClusterRole로 묶어주면, 의도하지 않은 권한 상승(RBAC Escalation)으로 이어질 수 있다고 한다.

## 👤 ServiceAccount - Pod의 인증 주체

쿠버네티스에서 Pod는 클러스터 API와 상호작용할 수 있는데, 그 요청은 ServiceAccount (SA)라는 신원 주체(identity)를 통해 이루어진다.

각 Pod는 기본적으로 하나의 SA에 연관되어 있는데 (default), SA에는 토큰이 주어지고, 이 토큰이 API Server에 인증 수단으로 사용된다.

SA에 할당된 Role/RBAC에 따라 클러스터에서 수행할 수 있는 액션이 제한된다.

### 🆕 새로운 SA 생성 및 Pod에 적용

{% highlight bash %}
kubectl create serviceaccount dashboard-sa
{% endhighlight %}

Pod 스펙에서 다음처럼 SA를 지정할 수 있다.

{% highlight yaml %}
spec:
  serviceAccountName: dashboard-sa
{% endhighlight %}

이 Pod가 실행되면 `/var/run/secrets/kubernetes.io/serviceaccount/token`에 SA 토큰이 자동 마운트된다.

## 🏗️ MSA를 위한 rbac와 SA는?

쿠버네티스는 보통 MSA를 컨테이너들로 편하게 관리하기 위해서 사용하는데, Kubernetes 기반의 MSA 아키텍처에서는 마이크로서비스 각각이 별도 Pod(혹은 Deployment)로 배포되고, 이들이 `http://user-service`, `http://order-service` 식으로 Service 이름 기반 REST 통신을 하게 된다.

그럼 Pod마다 서로 다른 Pod와 통신하기 위한 권한, 즉 rbac와 sa 설정이 필요할까?

대부분의 통신은 Cluster 내부의 DNS + ClusterIP를 통해 직접 라우팅되며, **Kubernetes API Server를 거치지 않는다**.

즉, order-service가 user-service의 `/users` 엔드포인트에 HTTP 요청을 보내는 건 그냥 일반적인 TCP 통신이기 때문에, RBAC 대상이 아니다.

그럼 MSA를 위한 rbac, SA는 없을까?

결론은 아니다. 있다.

왜냐면 argoCD로 kubernetes에 MSA를 배포할때 사용했었기 때문에 찾아보다가 정리하는 글이기도 하기 때문에..

바로 이유로 들어가자면, **spring cloud kubernetes + configMap, Secret 조합을 사용했을 때 필요해진다**.

이 조합은 spring cloud config, spring cloud bus, rabbitMQ를 이용한 Github repository에 저장되어있는 config에 변경사항이 생기면 그 즉시 연관된 서비스에 config 설정이 주입되는 방식을 대체하는 방식이다.

이때, github repository에 있는 configMap, Secret에 변경사항이 생기면, argoCD가 이를 감지하고, 컨트롤 플레인(마스터 노드)에 마이크로서비스에 config를 주입하라고 명령(apply)을 내린다.

그러면 자연스레 argoCD는 create, patch, delete 등의 권한(rbac)가 필요하게 되고, 마이크로서비스(pod)는 get, watch, list 등의 권한(rbac)가 필요하게 된다.

rbac가 필요하기 때문에 kubernetes API를 사용하기 위한 신원 주체인 SA도 함께 필요하게 된다.

## 🛡️ PodSecurity & SecurityContext - 실행 환경 보안 설정

**Q. 아무 컨테이너나 실행할 수 있는 건 안전하다고 할 수 있나?**

절대 아니다.

컨테이너라고 해서 루트 권한으로 아무거나 실행하게 해서는 안 된다. 이를 통제하기 위해 사용하는 보안 설정이 SecurityContext와 Pod Security Admission이다.

### 🔒 PodSecurity admission(PSA)

Kubernetes 1.25 부터는 PodSecurityPolicy가 제거되고, **PodSecurity Admission(PSA)**이 공식 보안 메커니즘으로 대체되었다.

3가지 모드로 나뉘며, 네임스페이스 단위로 적용이 가능하다.

| 모드 | 설명 |
|------|------|
| **privileged** | 모든 Pod 허용 (비권장) |
| **baseline** | 일반적인 보안 요구 충족 |
| **restricted** | 루트 금지, 호스트 네트워크 금지 등 최강 제한 |

{% highlight bash %}
kubectl label ns my-namespace pod-security.kubernetes.io/enforce=restricted
{% endhighlight %}

이제 이 네임스페이스 안에서는 보안 기준을 통과한 Pod만 배포가 가능하다.

### 🔧 SecurityContext 설정 예시

{% highlight yaml %}
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
{% endhighlight %}

이 설정은 루트 권한 없이 앱을 실행하고, 파일시스템도 읽기 전용으로 만든다.

## 🌐 NetworkPolicy - Pod 간 네트워크 보안 경계

![k8s 썸네일](/assets/img/posts/2025-05-22-k8s-9-kubernetes-authentication-security/1.png)

### 🔐 연관 있는 개념인 제로 트러스트(Zero trust)

기본적으로 쿠버네티스는 모든 Pod 간 통신을 허용한다. 하지만 이는 제로 트러스트 보안 모델에 위배된다.

NetworkPolicy는 Pod 간 네트워크 흐름을 제어하는 방화벽 역할을 한다.

{% highlight yaml %}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-db
spec:
  podSelector:
    matchLabels:
      role: db
  ingress:
    - from:
        - podSelector:
            matchLabels:
              access: backend
{% endhighlight %}

`role=db` Pod는 `access=backend` Pod에서만 접근 허용되고 그 외는 차단된다는 내용이다.

보통은 default deny all 정책을 기본값으로 두고, 필요한 통신만 허용하는 방식이 일반적이다.

## 🤔 헷갈리는 부분들 추가 정리

### ❓ RBAC만 설정해도 충분할까?

RBAC는 **API 접근 제어에만 적용된다**.

서비스 단에서 말하는 REST API 이런게 아니라, **Kubernetes API 접근 제어에만 적용된다**.

실제 네트워크, 파일 접근, 실행 권한 등은 SecurityContext, NetworkPolicy를 병행해야 완전한 보안이 된다.

### 🔑 ServiceAccount를 분리해야 하는 이유는?

서비스별로 자동으로 생성되는 default SA에 너무 많은 권한이 몰리면, 모든 Pod가 API Server에 관리자 권한으로 접근할 수 있는 꼴이 된다.

그러므로 각 어플리케이션마다 전용 SA를 만들고, RBAC도 개별로 설정해야 한다.

### 🚫 NetworkPolicy를 설정해도 안 먹히는 것 같은데?

현재 클러스터에 적용된 CNI 플러그인이 NetworkPolicy를 지원하는지 확인해야 한다.

예: Calico, Cilium은 지원 / Flannel은 기본적으로 미지원

## 🎯 마치며

좀 헷갈리는 개념이 많아서 표로 정리해보면 아래와 같다.

| 계층 | 보안 기능 |
|------|-----------|
| **API 접근** | RBAC, ServiceAccount |
| **실행 환경** | PodSecurity, SecurityContext |
| **네트워크 경계** | NetworkPolicy + CNI 플러그인 |
| **리소스 권한 관리** | Namespace 분리, RoleBinding 제한 |

LG CNS KDT 최종 프로젝트 중간 발표 피드백에서 인프라 단에서도 (쿠버네티스) 보안 설정을 더 확실히 해야할 것 같다고 피드백을 받았었는데, 아무래도 금융 관련 프로젝트이다보니까 더 보안 관련 피드백이 많았던 것 같다.

이 글에 정리된 내용들을 더 찾아보고 디밸롭해서, 프로젝트에 더 타이트하게 적용하고 보안 관련 피드백 반영했다는 걸 최종 발표때는 당황하지 않고 보여주리라.....