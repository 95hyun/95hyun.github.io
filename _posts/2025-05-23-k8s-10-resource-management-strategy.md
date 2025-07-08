---
layout: post
title: "[k8s] 10. 쿠버네티스에서의 리소스 관리 전략"
date: 2025-05-23 09:00:00 +0900
categories: [devops/infrastructure]
tags: [kubernetes, k8s, resources, limits, requests, qos, quota, scheduling, affinity, taint, toleration, 리소스관리, 스케줄링]
toc: true
toc_sticky: true
---

![k8s 썸네일](/assets/img/posts/2025-05-19-k8s-2-cluster-architecture-components/1.png)

## 🌟 들어가며

Kubernetes 클러스터는 수많은 Pod들이 노드 위에 올라가서 동작하는 구조다. 각 Pod은 컨테이너들을 실행시키고, 컨테이너는 당연히 CPU와 메모리 같은 자원을 소비하게 된다.

그런데 쿠버네티스는 기본적으로 Pod이 얼마만큼의 자원을 쓰는지 제한하지 않으면 무제한으로 사용하게 두는 구조다.

즉, 메모리를 많이 쓰는 Pod 하나가 클러스터 전체를 불안정하게 만들 수도 있다는 뜻이다.

그래서 등장한 개념이 바로 `resources.requests`, `resources.limits`이고, 이걸 기반으로 QoS 클래스, 쿼터, 스케줄링 전략 등이 이어진다.

## 📊 리소스 요청(request)과 제한(limit)의 개념

쿠버네티스는 컨테이너별로 자원 요청량과 제한량을 설정할 수 있도록 resources 필드를 제공한다.

{% highlight yaml %}
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"
{% endhighlight %}

**requests**는 스케줄러가 Pod를 배치할 때 기준이 되는 최소 요구 자원이고, 스케줄링 판단 기준이다. 이는 Pod를 어느 노드에 배치할지 결정할 때 이 값이 쓰인다.

**limits**는 런타임 사용 제한을 의미하고, 컨테이너가 절대 초과할 수 없는 최대 사용 자원이다.

## ⚠️ 리소스 미설정 시의 위험성

만약 리소스 설정이 없는 상태로 배포된다면 어떻게 될까..

{% highlight yaml %}
resources: {}
{% endhighlight %}

메모리 사용량에 제한이 없기 때문에, OOM(Out of Memory) 발생 시 노드 전체에 영향을 줄 수 있다.

CPU도 무제한 사용 가능해지기 때문에, 다른 Pod들의 성능 저하가 유발된다.

또한, Pod가 무조건 BestEffort 등급으로 분류되어 스케줄링 우선순위에서 밀려, 쉽게 kill 된다.

리소스 설정 없이 배포된 서비스가 OOM으로 다른 서비스까지 죽이는 사례들이 종종 있다고 한다.

## 🏆 QoS Class - 쿠버네티스의 자원 보장 정책

Kubernetes는 Pod에 할당된 자원 설정에 따라 Quality of Service (QoS) 등급을 부여한다.

이 등급은 Pod가 리소스 부족 시 누가 먼저 희생될지 결정하는 기준이 된다.

| 클래스 | 조건 |
|--------|------|
| **Guaranteed** | requests == limits, 모두 지정된 경우 |
| **Burstable** | 일부만 설정된 경우 |
| **BestEffort** | requests, limits 모두 미설정 |

보통, 중요한 서비스 (DB, API Gateway)는 Guaranteed 등급으로 보장하고, 일반 마이크로서비스는 Burstable로 적절히 설정하며, 비핵심 작업 (캐시 빌더, 알림 worker 등)은 BestEffort로 두고 쓰기도 한다.

## 🚫 ResourceQuota - 네임스페이스별 자원 상한선 설정

하나의 클러스터를 여러 팀/서비스가 함께 사용하는 경우, 특정 네임스페이스가 자원을 과도하게 쓰는 걸 방지하기 위해 ResourceQuota를 설정한다.

{% highlight yaml %}
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "2"
    requests.memory: "4Gi"
    limits.cpu: "4"
    limits.memory: "8Gi"
    pods: "20"
{% endhighlight %}

team-a 네임스페이스에서는 최대 4코어, 8Gi 메모리만 사용할 수 있고, Pod도 최대 20개까지만 생성이 가능하다.

## 📏 LimitRange - Pod/Container 단위의 기본 리소스값 설정

LimitRange는 리소스를 설정하지 않고 배포된 Pod에게 기본값을 강제 적용하는 역할을 한다.

{% highlight yaml %}
apiVersion: v1
kind: LimitRange
metadata:
  name: default-resources
  namespace: team-a
spec:
  limits:
    - default:
        memory: 512Mi
        cpu: 500m
      defaultRequest:
        memory: 256Mi
        cpu: 250m
      type: Container
{% endhighlight %}

만약 배포 시 resources 설정이 비어 있다면, 위 기본값이 자동으로 적용된다.

## 🎯 스케줄링 제어 - Affinity, Taint, Toleration

자원 설정만으로는 부족하고, 때때로 Pod가 어떤 노드에 올라가야 하는지를 세밀하게 제어해야 한다.

### 💕 Node Affinity - 조건 기반 스케줄링

Node Affinity는 "이 Pod는 어떤 조건을 가진 노드에 배치되어야 한다"라는 요구사항을 설정하는 기능이다.

말 그대로 친화도(affinity), 즉 특정 속성을 가진 노드에 붙으려는 성향을 명시하는 것이다.

Affinity에는 2가지 종류가 있다.

| 유형 | 설명 |
|------|------|
| **requiredDuringSchedulingIgnoredDuringExecution** | 반드시 조건을 만족하는 노드에만 스케줄됨 (필수) |
| **preferredDuringSchedulingIgnoredDuringExecution** | 만족하는 노드를 우선 배치하지만, 없으면 다른 곳에도 갈 수 있음 (권장) |

Affinity는 기본적으로 노드에 부착된 라벨(label)을 기준으로 작동한다.

{% highlight yaml %}
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: disktype
              operator: In
              values:
                - ssd
{% endhighlight %}

`disktype = ssd` (key = value) 라벨이 붙은 노드에만 스케줄링 하라는 뜻이다.

조건이 복잡한 경우 matchExpressions를 여러 개 사용할 수도 있다.

{% highlight yaml %}
matchExpressions:
  - key: team
    operator: In
    values: [a, b]
  - key: region
    operator: NotIn
    values: [ap-northeast-2]
{% endhighlight %}

### 🚫 Taints & Tolerations - 특정 노드 회피 or 허용

Taint는 노드에다가 '오지 마!'라고 써붙이는 것, Toleration은 Pod이 '나는 괜찮아, 갈 수 있어!'라고 말하는 것이다.

Taint가 있는 노드에는 기본적으로 아무 Pod도 배치되지 않는다. 하지만, Toleration을 가진 Pod는 예외적으로 허용되는 구조이다.

**노드에 Taint 설정**

{% highlight bash %}
kubectl taint nodes node1 dedicated=analytics:NoSchedule
{% endhighlight %}

node1은 dedicated=analytics 목적을 가진 Pod만 들어올 수 있다는 뜻이다. (key = value)

그 외 Pod는 이 노드에 스케줄링되지 않는다.

**Pod에 Toleration 설정**

{% highlight yaml %}
tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "analytics"
    effect: "NoSchedule"
{% endhighlight %}

나는 dedicated=analytics Taint를 이해할 수 있어서 이 노드에 들어갈 자격이 있다는 뜻이다.

### 🆚 Node Affinity vs Taints & Tolerations

Affinity와 Taints & Tolerations는 비슷하지만 차이점이 있다.

표로 정리하면 아래와 같다.

| 항목 | Node Affinity | Taints & Tolerations |
|------|---------------|----------------------|
| **목적** | "어디에 가야 하나?" | "어디에는 못 가" (except 내가 허락받은 경우) |
| **적용 주체** | Pod이 특정 노드로 향함 | 노드가 Pod을 밀어냄 |
| **기본 상태** | 조건 없는 한, 어디든 갈 수 있음 | 기본적으로 막혀 있음, 허용된 Pod만 스케줄됨 |
| **강제성** | required or preferred | 무조건 강제 (NoSchedule, NoExecute) |

## 🎯 마치며

쿠버네티스의 리소스 관리는 단순히 CPU, 메모리만 설정하는 것이 아니라, QoS 클래스, 쿼터, 스케줄링 전략까지 아우르는 종합적인 접근이 필요하다.

특히 운영 환경에서는 예상치 못한 리소스 고갈로 인한 장애를 방지하기 위해, 적절한 requests/limits 설정과 함께 ResourceQuota, LimitRange를 활용한 다층 방어 전략이 중요하다.

또한, Node Affinity와 Taints & Tolerations를 통해 워크로드의 특성에 맞는 노드 배치 전략을 수립하면, 클러스터 자원을 더욱 효율적으로 활용할 수 있다.