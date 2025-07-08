---
layout: post
title: "[k8s] 6. ConfigMap과 Secret으로 유연한 설정 구성"
date: 2025-05-21 09:00:00 +0900
categories: [devops/infrastructure]
tags: [kubernetes, k8s, configmap, secret, 설정관리, 환경변수, 보안, base64, 설정외부화]
toc: true
toc_sticky: true
---

![k8s 썸네일](/assets/img/posts/2025-05-19-k8s-2-cluster-architecture-components/1.png)

## 🌟 들어가며

현대적인 애플리케이션은 설정(configuration)과 코드의 분리를 기본 원칙으로 삼는다. 애플리케이션 코드를 변경하지 않고도 환경에 따라 동적으로 설정을 바꾸고, 민감한 정보(비밀번호, API 키 등)는 안전하게 다뤄야 한다.

쿠버네티스는 이를 위해 ConfigMap과 Secret이라는 리소스를 제공하며, 이 둘을 통해 설정의 외부화와 보안성을 동시에 달성할 수 있다.

## 🤔 왜 설정 외부화가 필요한가?

환경마다 달라지는 값들을 코드에 직접 넣는 건 유지보수와 보안 측면에서 매우 위험하다.

- **로컬**: `DB_HOST=localhost`
- **운영**: `DB_HOST=prod-db.internal`
- **테스트**: `DB_HOST=mock-db`

모든 환경에 맞는 설정을 코드가 아닌 외부 리소스에 선언하고, 애플리케이션이 이를 주입받는 방식이 환경 독립성, 유연성, 보안성을 모두 보장한다.

## 📋 ConfigMap

ConfigMap은 텍스트 기반의 일반 설정 데이터를 저장하는 리소스다. 예를 들어, 데이터베이스 호스트, 로그 레벨, API URL 등이 그 대상이다.

### ConfigMap 생성 방법

#### YAML 파일 정의 (선언형)

{% highlight yaml %}
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DB_HOST: mysql.default.svc.cluster.local
  LOG_LEVEL: DEBUG
{% endhighlight %}

{% highlight bash %}
kubectl apply -f configmap.yaml
{% endhighlight %}

#### 명령어로 생성

{% highlight bash %}
kubectl create configmap app-config \
  --from-literal=LOG_LEVEL=INFO \
  --from-literal=DB_HOST=localhost
{% endhighlight %}

### 주입 방법

ConfigMap은 환경 변수 또는 파일 형태로 주입할 수 있다.

#### 환경변수 방식

{% highlight yaml %}
envFrom:
  - configMapRef:
      name: app-config
{% endhighlight %}

#### 파일 마운트 방식

{% highlight yaml %}
volumeMounts:
  - name: config-volume
    mountPath: /etc/config

volumes:
  - name: config-volume
    configMap:
      name: app-config
{% endhighlight %}

이 경우 ConfigMap의 key-value가 `/etc/config/DB_HOST`, `/etc/config/LOG_LEVEL` 같은 파일로 마운트된다.

## 🔐 Secret

Secret은 이름 그대로 민감한 정보(예: 비밀번호, API 키, 인증서)를 저장하기 위한 리소스다. 기본적으로 base64로 인코딩되지만, 이는 암호화가 아닌 인코딩일 뿐이다.

쿠버네티스는 Secret을 기본적으로 etcd에 저장하므로, 운영 환경에서는 반드시 etcd 암호화 설정 또는 외부 KMS 연동이 필요하다.

### Secret 생성 예시

{% highlight yaml %}
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  username: dXNlcm5hbWU=  # base64 인코딩된 'username'
  password: cGFzc3dvcmQ=  # base64 인코딩된 'password'
{% endhighlight %}

base64 인코딩은 간단하게 터미널에서 `echo -n 'username' | base64`로 인코딩할 수 있다.

{% highlight bash %}
kubectl apply -f secret.yaml
{% endhighlight %}

### 주입 방식

#### 환경 변수

{% highlight yaml %}
env:
  - name: DB_USER
    valueFrom:
      secretKeyRef:
        name: db-secret
        key: username
{% endhighlight %}

#### 파일 마운트

{% highlight yaml %}
volumes:
  - name: secret-volume
    secret:
      secretName: db-secret

volumeMounts:
  - name: secret-volume
    mountPath: "/etc/secret"
    readOnly: true
{% endhighlight %}

이 경우 `/etc/secret/username`, `/etc/secret/password` 파일로 접근 가능하며, 기본적으로 읽기 전용이다.

## 📊 ConfigMap, Secret 차이 정리

| 항목 | ConfigMap | Secret |
|------|-----------|--------|
| **용도** | 일반 설정 | 민감한 정보 |
| **저장 방식** | 평문 | base64 인코딩 |
| **etcd 저장** | 평문 | 암호화 권장 |
| **권한 제어** | RBAC 가능 | 엄격한 권한 관리 필요 |
| **마운트 방식** | env, volume 모두 지원 | env, volume 모두 지원 |

## 🔄 설정 변경 시 애플리케이션에 자동 반영될까?

기본적으로 ConfigMap이나 Secret을 환경변수 방식으로 주입한 경우, 설정이 변경되어도 이미 실행 중인 컨테이너에는 적용되지 않는다.

하지만, 볼륨 마운트 방식을 사용하면 파일 내용은 실시간으로 반영되며, 애플리케이션이 파일 변경을 감지하는 로직이 있다면 바로 적용 가능하다.

내 경우 spring cloud config 대신 configMap, Secret을 사용하면서 spring cloud kubernetes라는 의존성을 사용해서 spring cloud bus, rabbitMQ 역할까지 대신했다.