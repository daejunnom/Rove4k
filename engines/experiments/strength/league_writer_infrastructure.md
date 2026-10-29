# 리그 진단 writer 및 anchor 준비

`league_writer_history.py`는 별도의 writer-v2 이력을 정의한다. 모든 이벤트는 고정
genesis·앞선 hash·순차 revision·epoch·owner·전체 payload에 묶인다. 전체 재생은
event 누락·변조, 중복 attempt와 action/subject를 거부한다. 기존 `league_epoch_store.py`
v1과 별도이며 이행 도구가 아니다. 이력 해시 자체는 저장소·입력 출처를 인증하지 않는다.

`league_writer_lambda.py`는 전용 `writer-v2#` 영역의 진단 bootstrap, diagnostic,
drain만 수락한다. 호출자 입력으로 AWS 테이블, DDB 표현식, owner 변경이나 예산 조정을
받지 않는다. 환경에 고정된 genesis만 조건부로 초기화하며, 기존 v1 영역의 존재 여부는
확인하지 않는다. 이 bootstrap은 빈 v2 영역 조회와 HEAD 생성이 원자적이라는 증거가
아니다. 실제 배포에서는 별도 테이블과 writer 격리가 필요하다.

추가 기록 전에는 일관된 HEAD를 읽고 해당 v2 영역 전체를 페이지 조회한 뒤 HEAD를 다시
읽는다. 수집된 이벤트와 attempt/subject 인덱스를 전수 재생하고, HEAD 변경·누락·변조를
거부한다. 다음 HEAD, event와 인덱스를 고정된 조건식을 가진 단일 DynamoDB 트랜잭션으로
작성한다. 진단 재생은 100,000행·32 MiB를 넘으면 중단하고 일부 이력만 승인하지 않는다.
강한 Query의 여러 페이지도 원자 snapshot은 아니며, 악의적인 다른 writer가 동시에
변경하는 상황이나 HEAD를 되돌리는 행위는 이 절차만으로 배제할 수 없다.

`league_anchor_verify.py`는 이 writer의 실제 이력 재생을 사용해 인접한 독립 anchor
receipt와 명시된 S3 version ID·manifest hash를 대조한다. 업로드 전 자기 자신의 S3
version ID를 알 수 없으므로 manifest와 업로드 후 서명된 receipt는 분리한다. 테스트는
임시 HMAC verifier와 모의 DynamoDB를 사용한다. 실제 KMS 서명 확인기, S3 Object Lock
version/retention, 독립적인 최신 watermark, DynamoDB TableId·읽기 출처, 예산 원본,
서로 다른 관리 권한의 독립성은 구현·검증되지 않았다. 호출자가 임의의 verifier를
주입할 수 있으므로 반환된 signature claim도 진위 증명이 아니다.

`league_writer_infrastructure.py`는 이 진단 writer를 위한 **별도** CloudFormation
템플릿 생성 소스다. 지정된 계정·home region·campaign 테이블만 대상으로 하는 Lambda
서비스 역할과, 별도 GitHub OIDC environment의 게시된 Lambda 버전 호출 역할을 정의한다.
템플릿의 호출 역할 Allow는 해당 버전에 한정되지만 다른 IAM 또는 리소스 정책의 추가
권한까지 배제하지 않는다. DynamoDB 직접 writer는 호출자에 부여하지 않는다. 그러나
Lambda 실행 역할의 Put/Update 권한 자체는 IAM만으로 올바른 조건식 사용을 강제하지
못한다. `PassRole`, 함수 코드·환경·역할·서명 설정을 바꿀 수 있는 다른 principal 및
관리자의 통제와 IAM 실효 정책은 배포 전에 별도 검증해야 한다.

환경값을 CloudFormation 파라미터로 따로 전달하지 않는다. 템플릿 생성기의 표준
입력에 `campaign_id`, `epoch_table_name`, `genesis_json` 문자열만 담은 JSON 객체를
제공하면 생성기는 세 값을 함수 환경과 IAM 범위에 직접 고정하고 환경 객체의 정규
JSON SHA-256을 `WriterVersion.Description`에 넣는다. 매번 생성기를 실행해 템플릿을
재생성해야 한다. 세 값 중 하나라도 변경하면 description이 변하므로 CloudFormation은
버전을 교체한다. 수동으로 템플릿을 편집하거나 생성 과정이 변조되는 경우 이 연결은
보장되지 않는다. 해시는 입력값의 연결을 위한 식별자이며 데이터의 진위를 보장하지
않는다. `CodeSha256`은 코드만 확인하고 환경 설정의 동시 수정을 차단하지 않는다.

`WriterVersion`의 함수 참조는 CloudFormation의 함수 업데이트 후 버전 생성 의존성을
만든다. 함수의 설정 변경과 코드 변경은 순차 실행되므로 `$LATEST`의 중간 상태가
노출될 수 있다. 버전 호출 정책을 사용해도 공유 역할 정책은 업데이트 중 이전 버전의
권한에 영향을 주며, 호출자 정책 갱신·기존 호출 완료·버전 교체는 원자적이지 않다.
따라서 업데이트 전 호출을 중지하고 진행 중 요청을 격리한 뒤, 업데이트 완료 후 게시된
버전의 환경·코드 digest, 역할 정책, 호출자 권한을 독립적으로 조회·대조해야 한다.
외부 principal의 동시 변경 및 이미 진행 중인 호출은 이 템플릿이 fence하지 못한다.
실제 change set, 업데이트 및 게시 결과는 아직 검증하지 않았다. 환경 이외의 함수
설정 변경 시에도 게시된 버전 일치 여부를 별도로 확인해야 한다.

코드 object의 S3 version과 Lambda Version의 `CodeSha256`을 필수 입력으로 받고,
지정한 AWS Signer profile version의 CodeSigningConfig를 `Enforce`로 생성한다. 서명
profile의 실제 소유권과 CI 승인 경계는 별도 확인한다. `league_writer_package.py`는
두 source 파일만 넣은 재현 가능한 **서명 전** ZIP을 메모리에서 만들며 업로드하거나
서명하지 않는다. 서명이 ZIP 바이트를 바꿀 수 있으므로 `CodeSha256`에는 서명 후 실제
S3 object의 정확한 digest를 사용해야 한다. 코드 SHA는 Lambda 관리형 런타임과 내장
boto3/botocore의 버전이나 실제 실행 동작을 고정하지 않는다.

Lambda의 비동기 호출은 오류 재시도와 중복 전달이 가능하며, DynamoDB transaction의
자동 생성될 수 있는 client token도 제한된 시간의 멱등성만 제공한다. 함수의 응답 유실
또는 DDB 성공 후 anchor 실패는 미결로 남겨 독립 reconciliation을 요구한다. 현재
진단 코드는 지속적 미결 quarantine·원격 수신자 fence·이전 writer 차단을 제공하지
않는다. 성공 응답은 항상 GO·인스턴스 생성·종료 권한을 모두 `false`로 반환한다.

사용자 조건은 전체 두 인스턴스 합산 $120이며, 한도에 도달하면 새 경기를 시작하지
않고 이미 시작한 경기는 정상 종료까지 관측한다. 이전 12시간 강제 종료는 적용하지
않는다. 이 템플릿은 비용을 관측하거나 게임을 제어하지 않으며 위 정책을 자체적으로
집행한다고 주장하지 않는다. 코드 패키지 서명, AWS 업로드·배포 및 실제 Lambda/DynamoDB
실행은 아직 수행하지 않았다.

참고: [DynamoDB 트랜잭션](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html),
[Lambda 비동기 재시도](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-error-handling.html),
[Lambda 코드 서명](https://docs.aws.amazon.com/lambda/latest/dg/configuration-codesigning.html),
[Lambda Version 업데이트](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-lambda-version.html),
[Lambda 함수 업데이트 순서](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-lambda-function.html),
[Lambda 런타임 업데이트](https://docs.aws.amazon.com/lambda/latest/dg/runtimes-update.html).
