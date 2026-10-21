> 2026-10-21 로컬 normal: ordinary builder1회가 native/whole 각2회 byte재현했고, positive verifier1회(quit/EOF2세션·8GO)가 통과했다. 실제 main+worker9TID와 검색8worker의 CPU 활동, native/private-path identity, position fence, reader·물리 group/TID 종료를 확인했다. 강제 cleanup/error는0이다.
>
> VmSize74972kB, startupRSS7552kB, activeRSS8320/8064kB는 해당 시점 관측이다. peak·속도·확장성·최종4k자원 수용은 검증하지 않았다. Producing recipe와 source freeze는 외부 원본으로 보존하며, 이 상태 블록과 recipe의 local_normal_validation은 실행 이후 annotation이다. CI 등록·실행은 root가 별도로 관리한다.

# Full F 고정 자원 profile8

이 entry는 qualified full F2/18의 최종 compact C에 워커 수만 늦게 특수화하는 별도 출하 경로다. 기존 `tiny-entry-f`의 canonical/DEV/optional/profile2 소스·변환·핀을 변경하지 않는다. 검색 워커8, TTbits18, PLY128을 고정하며, 생성에 성공한 native의 총 TID는 main을 포함해9다. 공개 UCI 자원 옵션은 없다. 최종 TCEC4k의 core/RAM 할당과 many-core 기력·확장성 수용은 미확정이다.

`--base-source`는 기존 F ordinary producer가 만든8559 B / `65ca88c6…` 소스여야 한다. 이 entry의 recipe는 현재 project canonical/helper closure44개와 양성 helper2개를 고정한다. 빌더는 이 source closure와 base C를 검증하고 외부 출력에 freeze한다. 외부 연구 JSON·과거 native는 정상 빌드의 authority 입력이 아니다. 기존 producer가 만든 정확한 C를 재사용하므로 profile 비교마다 PP와 이전 변환 단계를 다시 실행하지 않고, engine.c 전체를 이 subtree에 복제하지 않는다. 전체 source closure는 이 subtree5개를 포함해51개다. LF 정규화 규약은 기존 F와 같다.

`specialize.py`는 input8559/65ca88… 한 종류만 받아6개 역할의 literal2를8로 바꾼다: worker 배열, startup pending, 결과 depth scan, GO pending, pthread handle 배열, 생성 bound다. 전체 역변환과7개 gap을 검사한다. king k[2], castle/EP/repetition/TT bound/PLY-2/오류 상태 등 다른2들은 그대로다. 종료 join은 성공 생성 수를 사용하므로8로 바꾸지 않는다. 워커 id0..7의 ordering noise는 같은 unsigned 식으로0..16 범위를 유지한다. worker private key/learners, HCE/full-key TT/full-depth MTD(f)/QS, mutex·epoch·idle·취소·출력 후 완료 fence와 join은 유지한다. 워커 수 변경이므로2-worker와 실행 결과·native 동일성을 주장하지 않는다.

포장은 기존 project `pack_stream.source_literal`에 qualified `shipping_common.source_literal`의 raw-bytes envelope를 적용하고 원 F bootstrap/launcher와 고정 LZMA1 ALONE 모델을 사용한다. source8559 B, native18576 B, bootstrap9532 B, complete4478 B의 새로운 literal identity를 recipe에 등록했다. same-context2-worker4479 B보다1 B 작지만4096 B를 넘는다. 모든 source/native/bootstrap/whole은 일반 builder에서 각각2회 재현해야 한다. 이전 비용 시도의 envelope 누락 실패와 성공 native 재사용은 외부 원기록으로 보존했고 이 일반 빌드와 구분한다.

Linux x86-64, GCC13.3/binutils2.42, Python3.12.3, XZ5.4.5를 사용한다. 출력은 모두 새 절대 외부 경로에 둔다.

```sh
python3 -I -B engines/compact/tiny-entry-f/build.py --out /absolute/base
python3 -I -B engines/compact/tiny-entry-f-resource8/build.py --base-source /absolute/base/main.c --out /absolute/profile8
python3 -I -B engines/compact/tiny-entry-f-resource8/verify.py --build /absolute/profile8 --out /absolute/profile8-runtime
```

CI에서 기존 F 생성 단계가 `tiny-entry-f/main.c`를 제공한 뒤 새 build/verify를 실행할 수 있다. workflow 등록은 이 subtree 범위가 아니다.

새 positive verifier는 기존 generic Owned/Reader/mapping과 project chess oracle만 재사용한다. 기존3-TID main/assertion을 monkeypatch하거나 완화하지 않고, 자체9-TID 조건을 쓴다. quit/EOF2세션의 총8GO에서 실제 native identity·삭제된 private r4 경로·persistent9TID·idle/active8worker·합법 결과·position fence·reader와 물리 process/group 종료를 확인한다. source-compiling wrapper가 실행 중 C를 컴파일하는 단계와 최종 native 단계를 구분한다.

builder와 verifier는 유한 AS/CPU/wall/output 한계 및 소유 group cleanup을 사용한다. 정상 관찰의 startup/active VmSize·VmRSS/maps는 해당 시점 자료이며 stack peak·속도·확장성 결과가 아니다. source 계산에서 Worker 약68976 B,8개 배열551808 B, TT18 약6MiB라는 값은 ABI 가정과 실제 런타임 메모리를 구분해야 한다. 새로운 negative/fault/ptrace/RIE/trace/SAN/기력 캠페인은 포함하지 않는다.