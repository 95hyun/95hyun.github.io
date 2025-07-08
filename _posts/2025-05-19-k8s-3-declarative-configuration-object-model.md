---
layout: post
title: "[k8s] 3. 선언형 구성과 객체 모델"
date: 2025-05-19 11:00:00 +0900
categories: [devops/infrastructure]
tags: [kubernetes, k8s, 선언형, declarative, imperative, yaml, 객체모델, kubectl, gitops, iac]
toc: true
toc_sticky: true
---

![k8s 썸네일](/assets/img/posts/2025-05-19-k8s-2-cluster-architecture-components/1.png)

## 🌟 들어가며

쿠버네티스를 배우기 시작하면서 자주 마주하게 되는 키워드가 있다. 바로 **선언형(Declarative)**이다. 그리고 쿠버네티스의 모든 구성요소는 **리소스(객체, Object)**라는 개념으로 정의된다. 이 글에서는 쿠버네티스가 리소스를 어떻게 정의하고, 개발자들은 그것을 어떻게 선언적으로 작성해서 관리하는지를 정리해본다.

## 🤔 선언형 vs 명령형

쿠버네티스에서는 리소스를 두 가지 방식으로 관리할 수 있다.

### 명령형 (Imperative) 방식

{% highlight bash %}
kubectl run nginx --image=nginx
{% endhighlight %}

- 단일 명령어로 리소스를 생성하거나 제어
- 빠르게 실험하거나 일회성으로 쓸 땐 편리함
- 하지만 상태 관리가 어렵고 이력 추적이 불가능

### 선언형 (Declarative) 방식

{% highlight yaml %}
# YAML
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  containers:
    - name: nginx
      image: nginx
{% endhighlight %}

- YAML 또는 JSON 파일로 원하는 상태(desired state)를 선언
- `kubectl apply -f` 명령어로 적용
- Git에 선언 파일을 저장함으로써 GitOps, CI/CD 파이프라인 구성이 쉬움
- 리소스 변경 사항을 명확하게 추적 가능

## 🧩 쿠버네티스의 객체(Object)란?

Kubernetes는 모든 리소스를 **객체(Object)**로 취급한다.

Pod, Deployment, Service, ConfigMap, Secret, Ingress 등 우리가 쿠버네티스에서 다루는 거의 모든 개념은 "하나의 객체"로 표현된다.

이 객체들은 클러스터의 상태를 설명하는 선언적 단위이며, API Server에 의해 etcd에 저장된다.

## 📝 객체 YAML의 기본 구조

쿠버네티스 리소스를 선언할 때 사용되는 YAML 파일은 보통 다음과 같은 구조를 가진다.

{% highlight yaml %}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  labels:
    app: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: app-container
          image: my-image:latest
          ports:
            - containerPort: 8080
{% endhighlight %}

- **apiVersion**: 어떤 API 그룹의 리소스인지 지정 (예: v1, apps/v1)
- **kind**: 리소스의 종류 (Pod, Deployment, Service 등)
- **metadata**: 리소스의 이름(name), 레이블(labels), 주석(annotations) 등 메타정보
- **spec**: "이 리소스가 어떻게 동작해야 하는가"를 정의하는 실제 스펙

### kubectl apply vs create 차이

- `kubectl create -f pod.yaml`: 리소스가 없을 때만 생성. 이미 있으면 에러 발생
- `kubectl apply -f pod.yaml`: 리소스가 있으면 업데이트, 없으면 생성 (GitOps에서 권장)

apply는 원하는 상태를 선언하고, 클러스터가 그 상태에 맞춰 알아서 조정되도록 하는 방식이다.

## 🔧 kubectl로 객체 다루기

쿠버네티스 객체는 CLI로도 손쉽게 관리할 수 있다.

{% highlight bash %}
# 리소스 생성
kubectl apply -f deployment.yaml

# 리소스 상태 조회
kubectl get pods
kubectl describe pod <pod-name>

# 리소스 수정
kubectl edit deployment <name>

# 리소스 삭제
kubectl delete -f deployment.yaml
{% endhighlight %}

이러한 명령어는 리소스를 직접 다루는 수단이지만, 핵심은 YAML을 통해 리소스를 "선언"하고, "실제 상태"가 그 선언대로 유지되는지 컨트롤러가 관리하는 구조라는 것이다.

## ⚙️ 컨트롤러와 쿠버네티스가 객체를 관리하는 방식

![컨트롤러 루프](/assets/img/posts/2025-05-19-k8s-3-declarative-configuration-object-model/2.gif)
*이미지 출처: https://www.kerno.io/learn/kubernetes-operators*

쿠버네티스 내에는 **컨트롤러(Controller)**라는 클러스터 내의 다양한 리소스(Pod, Deployment, Service 등)가 사용자가 선언한 원하는 상태를 항상 유지할 수 있도록 자동으로 관리해주는 핵심 컴포넌트이다.

대표적으로는 파드의 개수를 보장하는 ReplicaSet 컨트롤러, 롤링 업데이트와 롤백을 지원하는 Deployment 컨트롤러, 상태가 필요한 워크로드를 위한 StatefulSet 컨트롤러, 클러스터 전체에 파드를 배포하는 DaemonSet 컨트롤러, 일회성 작업을 위한 Job/CronJob 컨트롤러 등이 있다.

컨트롤러는 대부분 쿠버네티스 클러스터를 설치하면 주요 컨트롤러들이 자동으로 생성되고 동작된다.

### 컨트롤러의 동작 흐름

쿠버네티스의 컨트롤러는 항상 다음과 같은 흐름을 따른다.

#### 1. 사용자가 원하는 상태(Desired State)를 선언함 (YAML 파일)
- 사용자는 Deployment, Service, Pod 등 리소스의 YAML 파일을 작성해 "내가 원하는 상태"를 정의한다.
- 예를 들어, nginx 파드를 3개 띄우고 싶다면 `replicas: 3`으로 선언한다.

#### 2. API Server에 전달되고 etcd에 저장됨
- `kubectl apply` 등으로 YAML을 적용하면, 이 정보가 Kubernetes API Server로 전달되고, etcd에 저장된다.

#### 3. Controller가 현재 상태(Current State)를 점검
- 각 컨트롤러(예: Deployment Controller, ReplicaSet Controller)는 자신이 관리하는 리소스의 "원하는 상태(Desired State)"와 "현재 상태(Current State)"를 계속 감시한다.
- 이 과정을 **Reconciliation Loop(조정 루프)**라고 부른다.

#### 4. 상태가 다르면 실제로 조정(Action)을 수행 (예: Pod 생성, 종료 등)
- 만약 현재 상태가 원하는 상태와 다르면, 컨트롤러가 자동으로 조치를 취한다.
- 예를 들어, 파드가 2개만 살아 있다면 1개를 추가로 생성해서 3개로 맞춘다.
- 반대로, 파드가 너무 많으면 초과된 파드를 자동으로 삭제한다.

이 구조 덕분에, 사람이 수시로 개입하지 않아도 클러스터는 스스로 상태를 유지하고 복구할 수 있게 된다.

## 🎯 선언형 구성이 중요한 이유

사용자가 시스템의 "원하는 최종 상태(yaml)"만을 명확하게 정의하면, 쿠버네티스가 자동으로 현재 상태를 감시하고 이를 일치시키기 위해 필요한 모든 작업을 알아서 수행하기 때문이다. 즉, 사용자는 **무엇(What)**을 원하는지만 기술하고, **어떻게(How)** 그 상태에 도달할지는 쿠버네티스가 책임진다.

이 방식의 가장 큰 장점은 **자동화와 일관성**이다. 예를 들어, YAML 파일로 파드, 서비스, 디플로이먼트 등 리소스의 원하는 상태를 선언해두면, 쿠버네티스 컨트롤러가 클러스터의 실제 상태를 지속적으로 감시하다가, 만약 파드가 죽거나 설정이 바뀌는 등 원하는 상태와 어긋나는 일이 생기면 자동으로 복구하거나 조정한다. 이로써 관리자가 수동으로 개입하지 않아도 클러스터가 항상 선언된 상태를 유지할 수 있다.

또한, 선언형 구성은 **IaC(Infrastructure as Code)**를 실현할 수 있게 해준다. YAML 파일 등 구성 파일 기반으로 인프라를 코드처럼 버전 관리(Git 등)할 수 있고, 변경 이력 추적과 협업이 쉬워진다. 여러 명의 엔지니어가 동시에 작업해도 충돌이나 설정 불일치가 줄어들며, 실수로 잘못된 명령을 내려도 선언된 상태만 올바르게 수정하면 시스템이 자동으로 복구한다.

마지막으로, 선언형 구성은 **시스템의 안정성과 예측 가능성**을 높여준다. 관리자는 반복적인 명령 실행이나 상태 점검 대신, 원하는 상태만 선언하면 되고, 쿠버네티스가 이를 자동으로 맞추기 때문에 운영 효율이 크게 향상된다.

정리해서 추려보자면 아래와 같다.

- **코드를 통해 인프라를 정의 (Infrastructure as Code)**
- **버전 관리 가능 (Git으로 이력 추적)**
- **리뷰, 테스트, 배포 자동화 가능 (CI/CD와 연계)**
- **장애 발생 시 빠르게 원상 복구 가능 (롤백 또는 재적용)**

## 🌟 마치며

쿠버네티스는 명령으로 지시하는 시스템이 아니라, 원하는 상태를 선언하고 시스템이 그 상태로 유지되도록 관리하는 구조로 설계 되어있다. 이는 Orchestration이라는 Kubernetes의 목적에 걸맞는 것 같다. 선언형 구성을 이해함으로써 ArgoCD를 통해 GitOps로 Pod, Deployment, Service, ConfigMap 등의 다양한 리소스를 미리 yaml 파일로 설정해두고 CD 했던 내용이 더 잘 이해될 수 있었다.