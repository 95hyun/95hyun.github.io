---
layout: post
title: "[k8s] 5. 워크로드 리소스 (Deployment, ReplicaSet, StatefulSet, DaemonSet)"
date: 2025-05-19 13:00:00 +0900
categories: [devops/infrastructure]
tags: [kubernetes, k8s, deployment, replicaset, statefulset, daemonset, 워크로드, 롤링업데이트, hpa, 오토스케일링]
toc: true
toc_sticky: true
---

![k8s 썸네일](/assets/img/posts/2025-05-19-k8s-2-cluster-architecture-components/1.png)

## 🌟 들어가며

![워크로드 리소스](/assets/img/posts/2025-05-19-k8s-5-workload-resources/1.png)

쿠버네티스에서 "배포"란 단순히 컨테이너를 실행하는 걸 넘어서, 서비스가 안정적으로 살아 있고, 필요 시 자동으로 복구되며, 트래픽 변화에 따라 유연하게 확장되는 것까지를 포함한다.

그리고 이 전 과정을 책임지는 게 바로 **워크로드 리소스(Workload Resource)** 들이다.

## 🚀 Deployment - 애플리케이션 배포의 기본 단위

Deployment는 쿠버네티스에서 가장 기본이자 핵심이 되는 워크로드 리소스다. 단일 Pod을 수동으로 띄우는 것이 아니라, "이 애플리케이션이 몇 개의 인스턴스로, 어떤 방식으로 실행되어야 하는지"를 선언하고 그 선언대로 유지되도록 컨트롤러가 자동으로 관리한다.

### 실무에서 Deployment가 중요한 이유

- 배포/롤백을 안전하게 처리해야 한다.
- 트래픽 증가에 따라 수평 확장을 가능하게 해야 한다.
- 장애가 발생해도 스스로 복구되어야 한다.

### 구조 분석

{% highlight yaml %}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
          ports:
            - containerPort: 80
{% endhighlight %}

- **replicas**: 실행할 Pod의 수
- **selector**: 어떤 Pod을 관리할지 정의 (템플릿의 label과 반드시 일치해야 함)
- **strategy**: 롤링 업데이트 전략
- **template**: 결국 이 템플릿이 Pod의 스펙

### Deployment의 롤링 업데이트

![롤링 업데이트](/assets/img/posts/2025-05-19-k8s-5-workload-resources/2.png)

Deployment는 기본적으로 RollingUpdate 전략을 사용한다. 이는 애플리케이션을 중단 없이, 점진적으로 새 버전으로 교체하는 기본 업데이트 전략이다. 쉽게 말해, 한 번에 모든 파드를 내렸다 올리는 것이 아니라, 조금씩(롤링) 새 파드로 교체해서 서비스가 끊기지 않도록 하는 방식이다.

#### 어떻게 동작할까?

**1. 새 이미지(버전)로 업데이트 명령을 내리면**
{% highlight bash %}
kubectl set image deployment/my-app my-app=my-app:v2
{% endhighlight %}

**2. 쿠버네티스가 기존 파드 중 일부를 종료하고, 새 버전의 파드를 일부 생성한다.**

기본적으로는 기존 파드의 25%만큼 새 파드를 추가로 띄울 수 있고, 25%만큼 기존 파드를 동시에 내릴 수 있다(maxSurge, maxUnavailable 옵션으로 조정 가능).

**3. 새 파드가 정상적으로 동작(Ready)하는지 확인한다.**

readiness probe 등으로 새 파드가 준비됐는지 체크.

**4. 정상적으로 준비된 새 파드가 있으면, 남은 기존 파드를 또 하나씩 종료하고 새 파드를 추가한다.**

이 과정을 반복해서, 모든 파드가 새 버전으로 바뀔 때까지 진행한다.

**5. 중간에 문제가 생기면 롤백이 가능하다.**

새 파드가 준비되지 않거나 장애가 발생하면, 업데이트를 중단하거나 이전 버전으로 되돌릴 수 있다.

{% highlight bash %}
# 배포 이력 확인
kubectl rollout history deployment nginx-deployment

# 롤백 실행
kubectl rollout undo deployment nginx-deployment
{% endhighlight %}

- **maxUnavailable**: 기존 Pod 중 몇 개까지 동시에 종료 가능?
- **maxSurge**: 새롭게 뜨는 Pod은 몇 개까지 허용?

이력 관리까지 가능하다는 점에서, Deployment는 GitOps 기반 배포 전략과도 매우 잘 맞는다.

#### 왜 중요할까?

- **무중단 배포**: 사용자는 서비스 중단 없이 새 버전을 사용할 수 있다.
- **가용성 보장**: 항상 일정 수 이상의 파드가 살아있기 때문에 요청이 끊기지 않는다.
- **자동화**: 사람이 직접 파드를 내렸다 올릴 필요 없이, 쿠버네티스가 알아서 안전하게 업데이트한다.
- **문제 발생 시 롤백**: 새 버전에서 문제가 생기면 빠르게 이전 버전으로 복구할 수 있다.

## 🔄 ReplicaSet - 실질적으로 Pod를 복제하는 주체

![레플리카셋](/assets/img/posts/2025-05-19-k8s-5-workload-resources/3.png)

Deployment는 Pod을 직접 생성하지 않는다. 실제로는 **ReplicaSet**이라는 리소스를 통해 Pod을 복제하고 관리한다.

사용자가 원하는 파드 개수(replicas)를 선언하면, ReplicaSet이 항상 그 개수를 유지한다.

- 파드가 죽거나 삭제되면, ReplicaSet이 자동으로 새로운 파드를 생성해서 다시 원하는 개수를 맞춘다.
- 반대로 파드가 너무 많아지면, 초과된 파드를 자동으로 삭제한다.
- 이 과정을 통해 서비스의 가용성(항상 일정 수의 파드가 서비스 중임)을 보장한다.

{% highlight bash %}
kubectl get rs
kubectl describe rs <name>
{% endhighlight %}

Deployment는 전략과 상태를 추상화한 상위 리소스이고, ReplicaSet은 실제 Pod을 만드는 실행 단위다.

## 🗃️ StatefulSet - 고유 ID와 상태를 가진 Pod

Deployment로는 MySQL, Kafka, Redis Cluster 같은 상태를 가진 애플리케이션을 운영하기 어렵다. 이런 애플리케이션은 보통 다음과 같은 특성이 있다.

- Pod 간 순서가 중요하다 (예: master → replica 순서)
- Pod마다 고유한 이름이나 네트워크 ID가 필요하다
- 각각의 Pod이 고유한 Volume을 가져야 한다

이럴 때는 **StatefulSet**을 사용한다.

### StatefulSet의 특징

#### 안정적이고 고유한 네트워크 식별자
- 각 Pod는 고유한 호스트명을 가진다 (예: web-0, web-1, web-2).
- Pod가 재시작되거나 다른 노드로 이동해도 호스트명이 유지된다.
- 클러스터 내부 DNS를 통해 안정적으로 접근 가능하다 (예: web-0.nginx.default.svc.cluster.local).

#### 영구 스토리지(Persistent Storage)
- volumeClaimTemplates를 사용해 각 Pod마다 독립적인 영구 볼륨(PersistentVolume)을 할당한다.
- Pod가 재생성되더라도 동일한 볼륨에 연결되어 데이터를 유지한다.

#### 순차적 배포 및 스케일링
- Pod 생성 시 0번부터 순서대로 생성된다. (예: web-0 → web-1 → web-2).
- 삭제 시 역순으로 종료된다 (예: web-2 → web-1 → web-0).
- 주로 마스터-슬레이브 구성에서 마스터 Pod(web-0)가 먼저 실행되어야 할 때 유용하다.

#### 롤링 업데이트 지원
- 업데이트 시에도 순서를 보장하며, 새 버전의 Pod가 준비된 후에 기존 Pod를 종료한다.

### 구조 분석

{% highlight yaml %}
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  clusterIP: None # 헤드리스 서비스
  selector:
    app: nginx
  ports:
    - port: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: "nginx" # 헤드리스 서비스 이름
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:latest
          ports:
            - containerPort: 80
          volumeMounts:
            - name: www
              mountPath: /usr/share/nginx/html
  volumeClaimTemplates: # 각 Pod마다 영구 볼륨 생성
    - metadata:
        name: www
      spec:
        accessModes: [ "ReadWriteOnce" ]
        resources:
          requests:
            storage: 1Gi
{% endhighlight %}

- **헤드리스 서비스(Headless Service)**: Pod의 고유 DNS 레코드를 생성한다.
- **volumeClaimTemplates**: 각 Pod(web-0, web-1, web-2)마다 독립적인 영구 볼륨을 생성한다.

StatefulSet을 쓸 땐 반드시 Headless Service (clusterIP: None)도 함께 정의해야 한다.

### 주의할 점

#### Scale Down 시 PVC가 삭제되지 않음 (영속성 유지)

StatefulSet을 축소(Scale Down)하면 Pod만 삭제되고, 연결된 PVC(PersistentVolumeClaim)는 기본적으로 삭제되지 않는다.

예를들어, replicas를 3 → 1로 줄이면 web-2, web-1 Pod가 삭제되지만, 해당 PVC(pvc-web-2, pvc-web-1)는 유지된다. 이는 데이터 손실을 방지하고, 향후 Scale Up 시 동일한 PVC를 재사용하기 위함이다.

이때, 미사용 PVC가 누적되어 스토리지 리소스 낭비가 발생할 수 있는데, Scale Down 후 PVC를 삭제하려면 수동으로 제거해야 한다.

{% highlight bash %}
kubectl delete pvc <pvc-name>
{% endhighlight %}

Kubernetes 1.27+에서는 persistentVolumeClaimRetentionPolicy를 설정해 Scale Down 시 PVC 자동 삭제를 활성화할 수 있다.

{% highlight yaml %}
spec:
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain  # 기본값 (삭제 유지)
    whenScaled: Delete   # Scale Down 시 PVC 삭제
{% endhighlight %}

#### Pod 간 호스트명 기반 통신

ReplicaSet의 Pod의 이름은 무작위 해시값이 포함된다. 보통 서비스를 이용해서 접근하기 때문에 무상태(Stateless) 애플리케이션에 활용된다.

하지만, StatefulSet의 각 Pod는 안정적인 DNS 이름을 가진다. (예: web-0.nginx.default.svc.cluster.local)

즉, Pod가 재생성되거나 다른 노드로 이동해도 DNS 이름은 유지된다.

Pod의 이름이 순차적이고 고정되어있기 때문에, ScaleUp, ScaleDown이 발생하면 StatefulSet을 DB 등으로 바라보고 있던 애플리케이션은 web-0, web-1 등의 다음 호스트명으로 피어 노드를 찾도록 구성해야 한다.

## 🔧 DaemonSet - 노드마다 Pod 1개 자동 실행

특정 작업은 모든 노드에서 반드시 실행되어야 한다.

예를 들면,
- 로그 수집기 (Fluentd, Filebeat)
- 메트릭 수집기 (Node Exporter)
- kube-proxy 같은 네트워크 플러그인

왜냐면 각 노드별로 모이는 메트릭, 로그들과 각 노드 안에서 실행되고 있는 파드들에 달려있는 사이드카에서 수집된 메트릭, 로그들이 파드 내 컨테이너 별로 다르기 때문이다.

이럴 때 사용하는 리소스가 바로 **DaemonSet**이다.

{% highlight yaml %}
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      containers:
        - name: exporter
          image: prom/node-exporter
{% endhighlight %}

DaemonSet은 새로운 노드가 클러스터에 추가될 때도 자동으로 Pod을 1개 배치한다. 또한 특정 레이블이 붙은 노드에만 배치할 수도 있다.

## 📊 리소스 요청/제한과 오토스케일링(HPA) 적용

쿠버네티스에서 리소스 요청(Requests)과 제한(Limits) 설정은 클러스터의 안정성, 효율성, 비용 최적화를 위한 핵심 메커니즘이며, HPA(Horizontal Pod Autoscaler)는 이를 기반으로 동적 확장을 구현하는 표준 도구이다.

### 리소스 요청(Requests)과 제한(Limits)의 중요성

#### 스케줄링 결정 프로세스

requests 값은 쿠버네티스 스케줄러가 Pod을 노드에 할당할 때 사용하는 최소 보장 리소스이다. 스케줄러는 노드의 할당 가능한 리소스(Allocatable Resources)에서 requests를 차감하며, `kubectl describe node`로 확인 가능하다.

{% highlight yaml %}
resources:
  requests:
    cpu: "250m"  # 0.25 CPU 코어 (1 Core = 1000m)
    memory: "128Mi" # 128 Mebibytes
{% endhighlight %}

이 설정으로 스케줄러는 최소 0.25 CPU와 128Mi 메모리가 남은 노드에만 Pod을 배치한다.

#### 리소스 제한의 실행 시맨틱스

limits는 컨테이너가 사용할 수 있는 절대적 상한치를 정의한다.

- **CPU**: 제한 초과 시 Throttling 발생 (CPU 사용 시간 제한)
- **메모리**: 제한 초과 시 컨테이너가 즉시 OOMKilled (Out-Of-Memory Kill)

{% highlight yaml %}
resources:
  limits:
    cpu: "1"      # 1 CPU 코어
    memory: "256Mi"
{% endhighlight %}

#### QoS (Quality of Service) 클래스와 장애 대응

쿠버네티스는 Pod을 다음 3가지 QoS 클래스로 분류하며, 노드 압박(Resource Pressure) 시 퇴출(Eviction) 순서를 결정한다.

| QoS 클래스 | 조건 | Eviction 우선순위 |
|-----------|------|------------------|
| **Guaranteed** | 모든 컨테이너의 requests == limits | 가장 낮음 (마지막) |
| **Burstable** | 최소 한 컨테이너가 requests < limits | 중간 |
| **BestEffort** | requests/limits 미설정 | 가장 높음 (첫 번째) |

**Guaranteed의 예시**

{% highlight yaml %}
resources:
  requests:
    cpu: "1"
    memory: "1Gi"
  limits:
    cpu: "1"
    memory: "1Gi"
{% endhighlight %}

### HPA (Horizontal Pod Autoscaler)의 동작 메커니즘

HPA는 메트릭 서버(Metrics Server) 또는 커스텀 메트릭 API를 통해 주기적으로(기본 15초 간격) 메트릭을 수집한다. 대상 메트릭이 사용자 정의 임계값을 초과/미달 시 ReplicaSet/Deployment의 replica 수를 조정한다.

{% highlight bash %}
kubectl autoscale deployment nginx-deployment --cpu-percent=60 --min=2 --max=10
{% endhighlight %}

CPU 사용률이 60%를 초과하면 Pod 수를 최소 2개에서 최대 10개까지 확장한다.

메트릭 종류에 따라서 확장 전략을 달리 할 수도 있다.

{% highlight yaml %}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: custom-metric-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: 100
{% endhighlight %}

- **리소스 메트릭**: CPU/Memory 사용률 (Metrics Server 제공)
- **커스텀 메트릭**: HTTP 요청률, 큐 대기 시간 등 (Prometheus Adapter 연동 필요)
- **외부 메트릭**: 클라우드 서비스 지표 (AWS CloudWatch 등)

## 🎯 마치며

이 글에서는 Pod를 실질적으로 운영 가능한 단위로 감싸는 4가지 워크로드 리소스를 정리했다.

이들 리소스를 적절히 선택하고 조합하면 무중단 배포, DB, 관제, 오토스케일링 같은 다양한 운영 시나리오에 유연하게 대응할 수 있을 것 이다.