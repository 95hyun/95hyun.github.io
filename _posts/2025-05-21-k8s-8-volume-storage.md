---
layout: post
title: "[k8s] 8. 볼륨과 스토리지 - 데이터의 영속성을 보장하는 k8s의 저장 전략"
date: 2025-05-21 11:00:00 +0900
categories: [devops/infrastructure]
tags: [kubernetes, k8s, volume, storage, pv, pvc, storageclass, 영속성, 스토리지, csi, 볼륨]
toc: true
toc_sticky: true
---

![k8s 썸네일](/assets/img/posts/2025-05-19-k8s-2-cluster-architecture-components/1.png)

## 🌟 들어가며

쿠버네티스는 본질적으로 컨테이너의 실행을 관리하는 플랫폼이다. 그런데, 컨테이너의 가장 큰 특징 중 하나는 **휘발성(volatility)**이다. 즉, 컨테이너가 종료되면 그 안의 데이터도 함께 사라진다.

예를 들어 이런 상황을 생각해보자.

{% highlight bash %}
docker run -it busybox
# echo "hello" > /data.txt
# exit
{% endhighlight %}

컨테이너를 다시 시작하면 `/data.txt`는 사라져 있다. 왜? 컨테이너는 영속적인 저장소를 갖지 않기 때문이다.

Kubernetes 환경도 마찬가지다. Pod이 재시작되면 그 안에서 생성한 데이터는 모두 사라진다.

그럼 어떻게 영속적인 데이터 저장이 가능할까?

## 📁 Pod 안에서 파일을 저장하려면? Volume!

![볼륨 개념](/assets/img/posts/2025-05-21-k8s-8-volume-storage/1.jpeg)
*이 볼륨이 아니다.*

쿠버네티스는 이 휘발성을 해결하기 위해 **Volume**이라는 개념을 도입했다.

Volume은 Pod의 생명주기와 동기화되지 않는 저장 공간이다.

- 즉, 컨테이너는 재시작되더라도 Volume은 그대로 유지된다.
- Pod 안의 여러 컨테이너가 Volume을 공유할 수도 있다.

{% highlight yaml %}
volumes:
  - name: shared-data
    emptyDir: {}

volumeMounts:
  - name: shared-data
    mountPath: /data
{% endhighlight %}

여기서 `emptyDir`은 Pod가 살아있는 동안 유지되며, 컨테이너끼리 파일을 공유할 때 유용하다. 하지만, Pod 자체가 삭제되면 emptyDir도 함께 사라진다.

그렇기 때문에 Pod 외부에 살아있는 영속 스토리지가 필요하다. 쿠버네티스는 이에 **PersistentVolume (PV)**와 **PersistentVolumeClaim (PVC)**이다.

## 🗄️ PV와 PVC

Kubernetes는 스토리지를 두 개의 리소스로 분리해서 관리한다.

| 리소스 | 설명 |
|--------|------|
| **PV** | 실제 물리적인 스토리지 자원 (AWS EBS, NFS ...) |
| **PVC** | 애플리케이션(Pod)에서 요청하는 스토리지 사양 (크기, access mode 등) |

비유하자면, PV는 아파트. PVC는 세입자의 임대 요청서이다. Kubernetes는 이 둘을 연결해주는 역할을 한다.

### 기본 구조

**PersistentVolume (PV)**

{% highlight yaml %}
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-example
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
{% endhighlight %}

**PersistentVolumeClaim (PVC)**

{% highlight yaml %}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-example
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
{% endhighlight %}

Pod에서는 이 PVC를 참조해서 마운트한다.

{% highlight yaml %}
volumes:
  - name: app-storage
    persistentVolumeClaim:
      claimName: pvc-example
{% endhighlight %}

## 🔐 AccessModes - 볼륨 공유가 가능한가?

스토리지 볼륨은 동시에 하나 이상의 Pod에서 접근할 수 있을까? 이를 `accessModes` 필드를 통해 접근 방식을 제어할 수 있다.

| AccessMode | 설명 |
|------------|------|
| **ReadWriteOnce** | 한 Pod만 읽기/쓰기 가능 (EBS, GCE PD 등 대부분) |
| **ReadOnlyMany** | 여러 Pod이 읽기 전용으로 공유 |
| **ReadWriteMany** | 여러 Pod이 동시에 읽기/쓰기 가능 (NFS, Ceph 등) |

## ⚡ StorageClass - 동적 볼륨 생성

그런데 접근 권한도 설정해줘야하고 PV에 PVC에.. 우리는 매번 PV를 만들어야 할까?

PV를 수동으로 생성하고 PVC가 그것을 연결하는 방식은 불편하고 자동화가 어렵다. 그래서 등장한 개념이 **StorageClass**다.

StorageClass는 PVC가 생성될 때 알아서 PV까지 자동으로 만들어주는 설정이다. 이는 특히 클라우드 환경(AWS, GCP, Azure)에서 매우 유용하다.

{% highlight yaml %}
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp2
{% endhighlight %}

PVC가 이렇게 선언되어 있다면:

{% highlight yaml %}
spec:
  storageClassName: fast
  resources:
    requests:
      storage: 5Gi
{% endhighlight %}

→ 이 PVC가 생성되면, EBS 볼륨이 자동으로 생성되고 해당 PVC에 바인딩 된다.

## 🔌 Container Storage Interface (CSI) - 쿠버네티스의 스토리지 확장성

Kubernetes는 다양한 스토리지 시스템과 연동할 수 있어야 하므로 **CSI**라는 표준을 도입했다.

CSI는 다음과 같은 기능을 제공한다:

- **Volume 동적 생성 / 삭제**
- **Snapshots**
- **Resize**
- **Attach / Detach 처리**

CSI를 지원하면 Ceph, Longhorn, OpenEBS, Portworx 같은 다양한 스토리지를 쉽게 붙일 수 있다.

## 📚 예제를 보면서 다시 정리

오늘 공부하고 정리하면서 쓰는 이 글의 내용이 오늘 반나절을 날렸던 트러블 슈팅의 주인공들이다.

그 문제의 예제를 보면서 윗 내용들을 다시 정리해본다. 아래 내용은 Helm chart로 OpenSearch 클러스터를 구성할 때 사용하는 설정 파일이다.

{% highlight yaml %}
clusterName: "opensearch-cluster"
nodeGroup: "master"

# 단일 노드 설정 (개발환경 용도)
# 프로덕션 환경에서는 false로 설정하고 replicas를 3으로 설정하는 것이 좋습니다.
singleNode: false

# 마스터 서비스 이름 설정
masterService: "opensearch-cluster-master"

# 노드 역할 설정
roles:
  - master
  - ingest
  - data
  - remote_cluster_client

# 복제본 수 설정 (프로덕션은 최소 3개 권장)
replicas: 1

# 리소스 설정
resources:
  requests:
    cpu: "1000m"
    memory: "2Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"

# JVM 힙 크기 설정 (리소스의 50% 정도로 설정하는 것이 좋음)
opensearchJavaOpts: "-Xmx2g -Xms2g"

# OpenSearch 2.12.0 이상 버전에서는 초기 관리자 비밀번호 설정 필요
extraEnvs:
  - name: OPENSEARCH_INITIAL_ADMIN_PASSWORD
    value: "YourStrongPassword123!"  # 실제 환경에서는 안전한 비밀번호로 변경하세요

# 퍼시스턴트 볼륨 설정
persistence:
  enabled: true
  accessModes:
    - ReadWriteOnce
  size: 30Gi
  storageClass: "gp2"  # AWS EKS에서는 gp2 또는 gp3를 일반적으로 사용

# 보안 설정
securityConfig:
  enabled: true
  # 기본 데모 인증서로는 보안에 취약하므로 프로덕션에서는 사용하지 마세요
  allowDefaultInitContainer: true

# 서비스 설정
service:
  type: ClusterIP  # 클러스터 내부에서만 접근 가능
  # LoadBalancer로 변경하면 외부에서 접근 가능

# Ingress 설정 (필요한 경우)
ingress:
  enabled: false
{% endhighlight %}

위 설정 파일에서 이 글과 연관된 주목할 부분은 아래와 같다.

{% highlight yaml %}
persistence:
  enabled: true
  accessModes:
    - ReadWriteOnce
  size: 30Gi
  storageClass: "gp2"
{% endhighlight %}

### persistence.enabled: true

→ 해당 Pod이 데이터를 외부 스토리지에 영속적으로 저장하겠다는 의미다.

즉, emptyDir 같은 휘발성 볼륨이 아닌, PVC(PersistentVolumeClaim)를 통해 연결되도록 구성되어 있다.

### accessModes: [ReadWriteOnce]

→ 한 Pod만 이 볼륨에 읽기/쓰기가 가능하다는 뜻. 이 설정은 Amazon EBS와 같은 블록 스토리지에서는 일반적으로 사용하는 접근 방식이다.

만약 다중 Pod이 동시에 쓰기를 해야 한다면 ReadWriteMany를 요구하게 되고, 이 경우 NFS나 Ceph 같은 스토리지가 필요하다.

#### 만약 Pod의 replicas가 1이 아니라면? ReadWriteMany를 써야하나?

AWS EBS는 ReadWriteOnce만 지원한다.

만약 `replicas: 3`으로 설정하면 같은 EBS를 3개의 Pod이 동시에 쓰게 되지 않나?

ReadWriteOnce는 "여러 Pod이 동시에 같은 볼륨을 쓰는 것"을 허용하지 않는다.

그래서 하나의 PVC로 묶인 EBS 볼륨을 여러 Pod이 동시에 공유해서 쓰려고 하면 에러가 난다. 
- → mount conflict 발생
- 동일한 노드에서라도 동시에 여러 Pod이 쓰려 해도 에러가 난다. → volume busy, read-only 발생

예를 들어 다음처럼 Deployment를 구성했다고 해보자.

{% highlight yaml %}
spec:
  replicas: 3
  template:
    spec:
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: my-pvc
{% endhighlight %}

여기서 `my-pvc`는 RWO인 EBS 볼륨을 참조하고 있고, 3개의 Pod가 동시에 같은 PVC를 사용하도록 되어 있다.

이렇게 되면, Pod 중 하나는 정상으로 Running 되지만, 나머지 2개는 Pending 상태에 빠져 에러 메시지를 출력한다.

#### 그럼 StatefulSet은 어떻게 EBS와 함께 여러 Pod를 쓰는가?

StatefulSet은 이런 문제를 해결하기 위해 **Pod마다 고유한 PVC를 자동 생성**해주는 기능을 제공한다.

{% highlight yaml %}
volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
{% endhighlight %}

이렇게 하면,
- my-app-0 → PVC: data-my-app-0 (→ EBS 1개)
- my-app-1 → PVC: data-my-app-1 (→ EBS 1개)
- my-app-2 → PVC: data-my-app-2 (→ EBS 1개)

각각 독립된 EBS 볼륨을 가지고, ReadWriteOnce 조건을 만족하면서 Pod마다 고립된 데이터 공간을 유지할 수 있다.

즉, EBS는 블록 스토리지고 ReadWriteOnce만 지원하기 때문에 복제(replica) 구조에서는 **StatefulSet + volumeClaimTemplates 조합이 필수**이다.

### size: 30Gi

→ 이 PVC는 30Gi 크기의 스토리지를 요청한다. PVC가 생성되면 이 요청에 맞는 PV가 바인딩되며, 없을 경우 StorageClass를 통해 자동 생성된다.

### storageClass: "gp2"

→ 스토리지 프로비저닝을 자동화하는 설정이다. 이 예시는 AWS EKS 기준이며, gp2는 General Purpose SSD 볼륨 클래스다.

Kubernetes는 이 StorageClass 정보를 바탕으로 PVC 생성 시 EC2의 EBS 볼륨을 백그라운드에서 자동 생성해 붙여준다.

실제로는 클라우드마다 기본 StorageClass가 다르기 때문에, 클러스터마다 적절한 클래스를 선택해야 한다.