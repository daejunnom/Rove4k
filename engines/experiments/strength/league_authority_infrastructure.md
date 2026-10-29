# 리그 권한 인프라 준비 범위

`league_authority_infrastructure.py`는 별도 CloudFormation 템플릿을 생성하는 소스다.
이 템플릿에는 DynamoDB 테이블과 GitHub OIDC **읽기 전용 관측 역할**만 있다.
기존 단일 인스턴스 캠페인의 테이블·12시간 종료 Lambda·Scheduler·인스턴스 역할과
리소스를 공유하지 않는다. 리그 시작, GO, 인스턴스 생성·종료 또는 쓰기 권한을
부여하지 않으며 초기 HEAD도 만들지 않는다. 템플릿 생성은 AWS API를 호출하지 않는다.

정본의 키는 `campaign_id`와 `record_id`다. 명시한 home region과 스택 리전이 같아야
하며 테이블은 단일 리전에 유지한다. TTL은 구성하지 않는다. 삭제 방지, 연속 백업,
삭제·교체 시 보존, 서버 측 암호화와 종량제 용량을 설정한다. 실제 배포와 백업은
요금을 발생시킬 수 있으므로 기존 전체 $120 캠페인 예산에 반영해야 한다. 이 리소스의
설정이나 삭제 방지 자체가 행의 불변성·완전성 또는 원격 단일 소유권을 증명하지는 않는다.

관측 역할은 같은 AWS 계정의 기존 GitHub OIDC provider를 신뢰하고 `aud`와 정확한
`repo:daejunnom/Rove4k:environment:<환경>` subject를 요구한다. 환경명은 필수
파라미터로 제공하며 대상 GitHub 환경의 보호 설정과 provider·계정은 배포 전에 별도로
검증해야 한다. 환경 subject만으로 workflow 파일을 특정할 수는 없다. 항목 읽기는
지정된 campaign partition으로 제한하고, table의 쓰기·변경을 역할 정책에서 명시적으로
거부한다. 다른 관리자나 별도 principal에 의한 수정과 해당 역할 자체의 정책 변경까지
차단한다는 뜻은 아니다.

## 실행 전 필요한 권한 경계

현재 `league_epoch_store.py`는 원장 head를 `UpdateItem`으로 갱신하고 각 시도를
`TransactWriteItems`로 기록한다. DynamoDB는 트랜잭션의 각 항목에 필요한
`PutItem`·`UpdateItem` 등의 권한을 평가한다. `dynamodb:EnclosingOperation`은
트랜잭션 사용을 제한할 수 있으나 올바른 `ConditionExpression`의 존재·내용을
강제하지 않는다. 따라서 직접 writer에게 해당 권한을 주면 조건 없는 갱신이나 기존
항목 덮어쓰기를 정책만으로 배제할 수 없다. `dynamodb:LeadingKeys` 역시 partition
키를 다루므로 동일 campaign의 head·attempt·subject sort key를 구분하지 못한다.
[DynamoDB 트랜잭션 IAM](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis-iam.html),
[DynamoDB 조건 키](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html)

실제 writer를 추가하기 전에는 다음을 독립적으로 검증해야 한다.

1. 조건식을 생략한 직접 호출·과거 항목의 삭제와 덮어쓰기를 막는 신뢰된 coordinator
   경로, 그 역할에 접근할 수 있는 주체 및 조직·IAM 관리자 경계.
2. 전체 attempt/subject 이력을 묶는 인증된 독립 anchor와 원격·로컬 이력의 롤백,
   부분 삭제, 새로운 버전 또는 권한 변경 감지. 단순 HEAD와 자가 해시만으로는 부족하다.
3. 시작 요청의 선행 durable intent, 호스트·시도별 fence와 수신 확인, 실제 소유한
   프로세스의 정산, 통신 실패 및 만료 후 중복 시작을 막는 인계·복구 절차.
4. 두 인스턴스의 공유 비용과 사용자 예산 조건: $120 초과 시 새 경기는 시작하지 않고
   이미 시작한 모든 경기를 마친 뒤 추가 예산을 기다린다. Spot 중단 등 인프라 실패는
   정상적인 예산 drain과 구분한다. 이전 12시간 인스턴스 강제 종료는 재사용하지 않는다.
5. 실제 GitHub environment 보호·OIDC 역할, 서버의 부팅·SSM·cgroup/NUMA 및
   신뢰할 수 있는 최신 Spot Advisor <5% 조건. 이 템플릿은 그 조건을 검증하지 않는다.

DynamoDB PITR은 과거 시점의 **새 테이블**로 복원한다. 복원 테이블의 ARN, IAM,
백업·삭제 보호 등 설정과 독립 anchor를 재검토하고 현재 진행 경기와 미확정 요청을
정산하기 전까지는 이를 기존 head로 자동 승격하지 않는다.
[DynamoDB PITR 복원](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/pointintimerecovery_restores.html)

S3 Object Lock을 나중에 anchor로 도입하더라도 잠기는 것은 특정 객체 버전이다.
동일 키에 새 버전이나 삭제 마커가 생길 수 있으므로 정확한 version ID, 순서·인증과
DynamoDB/S3 간 비원자 실패 복구가 필요하다. 현재 템플릿은 독립 anchor 버킷을
생성하거나 Object Lock을 구성하지 않는다.
[S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)

`ValidateTemplate` 성공은 템플릿 본문 수준의 검사다. 실제 role trust·GitHub 환경·IAM
유효 권한, 계정 정책·할당량, cfn-guard 보안 규칙이나 비용·실행 준비까지 증명하지 않는다.
