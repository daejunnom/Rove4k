> 2026-10-22 path-only Worker 후속 profile8: ordinary builder의 첫 성공 실행이 source/native/bootstrap/payload/whole을 각각2회 동일하게 재현했고, 기존 byte-unchanged positive verifier1회(quit/EOF2세션·8GO)가 통과했다. 실제 main+worker9TID, 검색8worker의 CPU 활동, native/private-path identity, position fence, reader·물리 group/TID 종료를 확인했다. 강제 cleanup과 실행 오류는0이다. Whole4474 B는 이전 fixed8의4478 B보다4 B 작다.
>
> VmSize74716kB, startupRSS7552kB, activeRSS8192/7936kB는 해당 시점 관측이다. Peak·속도·확장성·최종4k자원 수용은 검증하지 않았다. Producing recipe와 source freeze 및 초기 두 precompile 실패는 외부 원본으로 보존한다. 이 상태 블록과 recipe.local_normal_validation은 실행 이후 annotation이다. CI 등록·실행은 root가 별도로 관리한다.

# Full F 고정 자원 profile8

이 entry는 qualified full F2/18의 이름 축소 직전 compact C에 워커 수만 늦게 특수화하는 별도 출하 경로다. 기존 `tiny-entry-f`의 canonical/DEV/optional/profile2 소스·변환·핀을 변경하지 않는다. 검색 워커8, TTbits18, PLY128을 고정하며, 생성에 성공한 native의 총 TID는 main을 포함해9다. 공개 UCI 자원 옵션은 없다. 최종 TCEC4k의 core/RAM 할당과 many-core 기력·확장성 수용은 미확정이다.

`--base-source`는 F ordinary producer의 명시적 `source-before-names.c`, 즉 이름 축소 직전 path-only Worker의8538 B / `47353a15…` 소스여야 한다. 이 entry의 recipe는 현재 project canonical/helper closure47개와 양성 helper2개를 고정한다. Path-only 이력 승격 당시 바뀐 항목은 F builder와 새 `shipping_history_path.py`였다. 후속 F producer 포장 분리는 F builder의 LF pin을 갱신하고 새 `source_package.py`를 provenance closure에 추가했다. 빌더는 이 source closure와 base C를 검증하고 외부 출력에 freeze한다. 외부 연구 JSON·과거 native는 정상 빌드의 authority 입력이 아니다. 기존 producer가 만든 정확한 C를 재사용하므로 profile 비교마다 PP와 이전 변환 단계를 다시 실행하지 않고, engine.c 전체를 이 subtree에 복제하지 않는다. 전체 source closure는 이 subtree5개를 포함해54개다. LF 정규화 규약은 기존 F와 같다.

`specialize.py`는 input8538/47353a15… 한 종류만 받아6개 역할의 literal2를8로 바꾼다: worker 배열, startup pending, 결과 depth scan, GO pending, pthread handle 배열, 생성 bound다. 출력은8538 B / `91162258…`이며 전체 역변환과7개 gap을 검사한다. king k[2], castle/EP/repetition/TT bound/PLY-2/오류 상태 등 다른2들은 그대로다. 종료 join은 성공 생성 수를 사용하므로8로 바꾸지 않는다. 워커 id0..7의 ordering noise는 같은 unsigned 식으로0..16 범위를 유지한다. worker private path key/learners, HCE/full-key TT/full-depth MTD(f)/QS, mutex·epoch·idle·취소·출력 후 완료 fence와 join은 유지한다. 워커 수 변경이므로2-worker와 실행 결과·native 동일성을 주장하지 않는다.

Worker의128개 key는 검색 중 추가된 private path만 보관한다. root history는 GO 전체에서 불변인 global qg/qh를 읽으며, position은 모든8-worker의 think·결과 게시가 끝나는 k/drain 뒤에만 갱신된다. 다음 GO의 mutex·epoch publication이 새 root를 게시한다. public4096 history cap과 전체 repetition 비교는 유지한다. Worker layout과 뒤 member offset은 이전 형태와 다르므로 예전 raw Worker ABI나 메모리 관측을 새 profile의 증거로 재사용하지 않는다.

포장은 기존 project `pack_stream.source_literal`에 qualified `shipping_common.source_literal`의 raw-bytes envelope를 적용하고 원 F bootstrap/launcher와 고정 LZMA1 ALONE 모델을 사용한다. source8538 B, native18576 B, bootstrap9511 B, complete4474 B의 새 literal identity를 recipe에 등록했다. 별도 first cost에서 이전 fixed8 whole4478 B를 재컴파일·재압축 없이 복원·대조한 뒤 새 profile만 compile1/encode1하고 old/new strict Python2·CLI2를 확인했다. whole 감소4 B는 직접 측정한 값이며2-worker의 감소3 B에서 추정하지 않았다. 4096 B를 넘고, 일반 builder의 각2회 재현과 정상 검증도 위 별도 normal 단계에서 확인했다. 이전 비용 시도의 envelope 누락 실패와 성공 native 재사용도 외부 원기록으로 보존한다.

73 B 헤더 도입 당시 F producer는 full 기본 profile만73 B stdin header·BT2로 포장했고, 그 단계의 생성 C는8538 B / `47353a15…`로 동일했다. 이 entry는 자체 legacy77 B launcher·BT4/64MiB 모델과 source/native/bootstrap/whole 기대값을 그대로 사용하며 새 공통 패키저를 호출하지 않는다. 이번 갱신은 producer 코드 출처를 명시한 것으로, 기존 producing recipe 원본과4474 B 각2회 재현·9TID/8GO 양성 근거를 재사용한다. 새 컴파일·압축·runtime 검증은 수행하지 않았다.

Linux x86-64, GCC13.3/binutils2.42, Python3.12.3, XZ5.4.5를 사용한다. 출력은 모두 새 절대 외부 경로에 둔다.

```sh
python3 -I -B engines/compact/tiny-entry-f/build.py --out /absolute/base
python3 -I -B engines/compact/tiny-entry-f-resource8/build.py --base-source /absolute/base/source-before-names.c --out /absolute/profile8
python3 -I -B engines/compact/tiny-entry-f-resource8/verify.py --build /absolute/profile8 --out /absolute/profile8-runtime
```

CI에서 F 생성 단계가 `tiny-entry-f/source-before-names.c`를 제공한 뒤 새 build/verify를 실행할 수 있다. 이 연결의 CI dispatch·완료는 root가 별도로 확인한다.

새 positive verifier는 기존 generic Owned/Reader/mapping과 project chess oracle만 재사용한다. 기존3-TID main/assertion을 monkeypatch하거나 완화하지 않고, 자체9-TID 조건을 쓴다. quit/EOF2세션의 총8GO에서 실제 native identity·삭제된 private r4 경로·persistent9TID·idle/active8worker·합법 결과·position fence·reader와 물리 process/group 종료를 확인한다. source-compiling wrapper가 실행 중 C를 컴파일하는 단계와 최종 native 단계를 구분한다.

builder와 verifier는 유한 AS/CPU/wall/output 한계 및 소유 group cleanup을 사용한다. 정상 관찰의 startup/active VmSize·VmRSS/maps는 해당 시점 자료이며 stack peak·속도·확장성 결과가 아니다. path-only Worker의 실제 메모리 관측은 새 positive 실행 자료로 구분한다. 새로운 negative/fault/ptrace/RIE/trace/SAN/기력 캠페인은 포함하지 않는다.

초기 ordinary 호출은 출력 부모 폴더 부재로 도구 실행 전에 끝났고, 다음 호출은 CRLF raw helper hash와 LF freeze hash의 등록 불일치로 컴파일 전에 끝났다. 두 실패를 그대로 보존한 뒤 parent만 준비하고 recipe.specialize_sha256을 명시된 LF 계약에 맞췄다. Helper 원문과 builder/verifier 본문, source/native/whole 기대값, compiler/codec은 바꾸지 않았다. `specialize_sha256`은 LF2529 B / `86fbfe65…`를 뜻하며 Windows raw helper2555 B / `a5a2158d…`와 구분한다.

## Full-profile bootstrap environment reuse — 2026-10-22

The base producer's full-only bootstrap preparation now inlines its one-use
Popen environment dictionary. Its F source remains8538 B/47353a15…; F8 still
consumes the original shared template and its own77-byte/BT4 packaging. This
profile's source/native/bootstrap/whole, compiler, codec, builder and positive
verifier are unchanged. Only the producer Fbuild provenance pin is updated.
Existing4474-byte reproduction and nine-TID positive receipts are reused;
no new F8 compiler/codec/runtime execution is claimed by this metadata change.


## Explicit pre-spelling input stage — 2026-10-22

Full F now applies its NVCompact-derived private-name spelling after the existing history-path source stage. Its selected main.c has the new spelling, while the ordinary producer explicitly preserves source-before-names.c at each attempt and at the selected output root. This is a development source output, not another submitted/runtime file. F8 consumes that earlier8538-byte stage, never the renamed final main.c. The CI --base-source argument and the example above name this file directly.

F8 retains exactly base8538/47353a15… and specialized8538/91162258…, native18576/33509091…, bootstrap9511/95d0410d…, whole4474/65a1ed9a…. Its six-role specialize helper, constructor/TT/history/search/resource behavior, legacy77-byte template/header, BT4 codec, builder and positive verifier are unchanged. The recipe updates only producer build provenance and adds shipping_names.py to its source closure. That helper belongs to the producer provenance; F8 does not apply it.

The actual new ordinary producer's selected and two attempt pre-spelling files are read back against the unchanged F8 base identity, and existing source_closure() verifies the current ordinary inputs. Prior4474 independent reproduction and9-TID/8GO positive receipts remain exact raw-hash reuse, rather than a new F8 execution. No F8 compiler, encoder, source specialization or engine run is added by this consumer-path update. Final source/readbase evidence is external; root owns Git and exact-head CI.


## Full-only handler-loop producer provenance — 2026-10-22

The full F producer now emits handler registration/reset as two ordered
`for s in 2,15` loops. This bootstrap-only choice does not change the shared
legacy template, the explicit pre-spelling source, or any F8 packaging input.
The producer's selected and two attempt source-before-names.c files still
match8538/47353a15… exactly. Only the Fbuild pin is refreshed in the F8 recipe;
all other recipe fields and F8 source/native/bootstrap/whole4474 identities,
specialize helper, builder, positive verifier and CI input path are unchanged.
The existing54-file source_closure() is checked against current source. Prior
4474 reproduction and nine-TID positive evidence is reused by exact identity;
no new F8 compilation, encoding, specialization or engine execution is claimed.
