---
layout: post
title: "[k8s] 12. Helm Chart로 선언적 배포를 해보자"
date: 2025-05-24 09:00:00 +0900
categories: [devops/infrastructure]
tags: [kubernetes, k8s, helm, helm-chart, 패키지매니저, 선언적배포, templates, values, configmap, secret, 템플릿화]
toc: true
toc_sticky: true
---

![k8s 썸네일](/assets/img/posts/2025-05-19-k8s-2-cluster-architecture-components/1.png)

## 🌟 들어가며

Helm은 Kubernetes 환경에서 애플리케이션을 패키징하고 배포할 수 있는 패키지 매니저다. 우리가 Kubernetes에 리소스를 배포할 때 YAML을 일일이 관리하는 건 한계가 있다. 이를 템플릿화하고 변수로 관리할 수 있게 해주는 도구가 바로 Helm이다.

즉, Helm은 **Kubernetes의 apt, yum, npm 같은 역할**을 하는 도구다.

Helm은 대강 알겠고, **Helm Chart는 뭘까?**

Helm Chart는 하나의 애플리케이션을 정의하는 디렉터리 구조의 패키지 단위다. Chart에는 Deployment, Service, ConfigMap 등의 Kubernetes 리소스를 템플릿화한 YAML 파일들과, 해당 템플릿에 주입될 변수(values)가 포함되어 있다.

아래는 기본 구조 예시다.

{% highlight text %}
my-chart/
  Chart.yaml
  values.yaml
  templates/
    deployment.yaml
    service.yaml
    _helpers.tpl
{% endhighlight %}

| 파일 | 설명 |
|------|------|
| **Chart.yaml** | 차트의 메타데이터 (이름, 버전 등) |
| **values.yaml** | 템플릿에 주입될 변수 값 정의 |
| **templates/** | Kubernetes 리소스 템플릿 모음 |
| **_helpers.tpl** | 공통 템플릿 함수 정의 (이름 규칙 등) |

## 🎯 직접 helm을 만들어서 배포해보자. 상황 설정부터

이번 예제에서는 user-service라는 이름의 마이크로서비스를 Helm Chart로 배포한다. 이 서비스는 Spring Boot 기반이고, 다음과 같은 요구사항을 가진다고 가정한다.

- 환경 변수를 받아야 하며 (예: SPRING_PROFILES_ACTIVE, MYSQL_HOST)
- DB 비밀번호 등 민감 정보는 Secret으로 분리해야 하고
- /health로 헬스 체크를 제공한다
- 환경마다 (개발/운영) 설정값이 달라야 한다
- 선언적으로 배포, 업그레이드, 롤백할 수 있어야 한다

→ 이걸 Helm으로 설계해보자.

## 📁 Helm Chart 생성 - 기본 틀부터

우선 Helm Chart 디렉토리를 만든다

{% highlight bash %}
helm create user-service
{% endhighlight %}

Helm은 다음과 같은 구조로 Chart의 뼈대를 자동 생성한다.

{% highlight text %}
user-service/
├── Chart.yaml          # 메타정보
├── values.yaml         # 변수 파일 (사용자 정의 값)
└── templates/          # 리소스 템플릿
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── _helpers.tpl
{% endhighlight %}

이제 여기에 ConfigMap과 Secret 템플릿을 추가로 만든다.

{% highlight text %}
templates/
├── configmap.yaml      ← 환경 변수용
└── secret.yaml         ← 민감 정보용
{% endhighlight %}

## ⚙️ values.yaml

values.yaml은 Helm Chart에서 가장 핵심적인 사용자 정의 입력값 파일이다. 우리는 운영/개발 환경에 따라 값이 달라지길 원한다.

따라서 아래처럼 구조화한다.

{% highlight yaml %}
replicaCount: 2

image:
  repository: myregistry.com/user-service
  tag: "1.0.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8080

# 일반 환경 변수 (→ ConfigMap으로 주입)
config:
  SPRING_PROFILES_ACTIVE: prod
  MYSQL_HOST: mysql.default.svc.cluster.local
  MYSQL_PORT: "3306"

# 민감한 값 (→ Secret으로 주입)
secret:
  DB_USERNAME: user_admin
  DB_PASSWORD: supersecret123

resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
{% endhighlight %}

### 🔐 왜 config와 secret을 분리했을까?

- **config**: → 환경에 따라 바뀔 수 있지만 민감하진 않은 설정
- **secret**: → 비밀번호, 인증토큰처럼 암호화되어야 할 값

이렇게 분리하면 Helm Chart 내부에서도 자연스럽게 ConfigMap / Secret 리소스를 따로 구성할 수 있게 된다.

## 📄 ConfigMap 템플릿

{% highlight yaml %}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "user-service.fullname" . }}-config
data:
  {{- range $key, $val := .Values.config }}
  {{ $key }}: {{ $val | quote }}
  {{- end }}
{% endhighlight %}

여기서 중요한 점은

- `.Values.config`는 Key-Value 쌍으로 정의된 일반 환경 변수들
- `range`를 통해 Helm이 YAML 템플릿 안에서 반복 처리
- 모든 값은 `quote` 처리 ("값" 형태)로 타입 오류 방지

이 ConfigMap은 Deployment에 `envFrom`으로 한 번에 주입할 수 있도록 구성된다.

## 🔒 Secret 템플릿

{% highlight yaml %}
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "user-service.fullname" . }}-secret
type: Opaque
data:
  {{- range $key, $val := .Values.secret }}
  {{ $key }}: {{ $val | b64enc | quote }}
  {{- end }}
{% endhighlight %}

- Kubernetes의 Secret 리소스는 모든 값을 **base64로 인코딩**해야만 저장할 수 있음
- Helm은 템플릿에서 `.Values.secret` 값을 받아 `b64enc` 필터로 처리
- 이 과정을 템플릿 안에서 처리하므로 개발자는 평문으로 작성 가능 → 실무 편의성 높음

## 🚀 Deployment 템플릿 수정

{% highlight yaml %}
spec:
  containers:
    - name: user-service
      image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
      ports:
        - containerPort: {{ .Values.service.port }}
      envFrom:
        - configMapRef:
            name: {{ include "user-service.fullname" . }}-config
        - secretRef:
            name: {{ include "user-service.fullname" . }}-secret
{% endhighlight %}

`envFrom:`은 여러 개의 Key-Value 쌍을 한 번에 환경 변수로 주입할 수 있다.

- **코드 간결함**: envFrom으로 전체 ConfigMap / Secret 주입
- **유지보수 용이성**: ConfigMap만 수정해도 자동 반영 가능

또한, livenessProbe, readinessProbe도 `/health` 경로에 맞춰 추가한다.

## 🌐 Service 설정

{% highlight yaml %}
spec:
  type: {{ .Values.service.type }}
  selector:
    app: {{ include "user-service.name" . }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.port }}
{% endhighlight %}

- 서비스 타입은 ClusterIP로 내부 통신용
- 외부 노출이 필요하다면 LoadBalancer나 Ingress와 함께 설정 가능

## 📦 설치 및 확인

{% highlight bash %}
helm install user-service ./user-service
{% endhighlight %}

→ 모든 리소스가 생성된다: Deployment, Service, ConfigMap, Secret

{% highlight bash %}
kubectl get pods
kubectl get configmap user-service-config -o yaml
kubectl get secret user-service-secret -o yaml
{% endhighlight %}

## 🔄 환경 분리 - dev, prod를 한 Chart로 배포하려면?

Helm은 values.yaml 외에 `-f` 옵션으로 다른 파일을 주입할 수 있다.

{% highlight bash %}
helm install user-service-dev ./user-service -f values-dev.yaml
helm install user-service-prod ./user-service -f values-prod.yaml
{% endhighlight %}

→ 같은 Chart로 환경마다 다른 설정, 다른 배포가 가능
→ CI/CD 파이프라인에도 쉽게 통합 가능

## 🎯 마치며

각 요소를 표로 정리하자면,

| 구성 요소 | 이유 |
|-----------|------|
| **values.yaml** | 운영환경 변수 분리 및 재사용성 |
| **configmap.yaml** | 일반 설정 데이터 주입용 |
| **secret.yaml** | 민감한 데이터 주입용 (base64 인코딩 포함) |
| **deployment.yaml** | ConfigMap, Secret을 envFrom으로 한번에 주입 |
| **service.yaml** | 내부 or 외부 접근 설정 |
| **환경 분리** | -f values-xxx.yaml로 context 별 배포 가능 |

여러모로 쿠버네티스를 쓰면서 많이 쓰이는 놈이다.

아직 대부분 bitnami나 다른 사람이 만들어둔 chart만 쓰고 value만 커스텀해서 쓰고 있어서, 직접 만들어 쓰는 경험은 많이 없다.

배우면서 더 경험해봐야겠다.

자세한 내용은 공식 문서를 참고하자.

[Helm 공식 문서](https://helm.sh/docs/)