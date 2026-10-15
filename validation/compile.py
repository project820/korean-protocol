"""Compile trusted local rule requirements into small host-loadable profiles."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from .check import Checker, FILES, validate_root

NOTICE_PATHS=('LICENSE','NOTICE.md')
PROFILE_PATHS=('profiles/coding-agent.md','profiles/chat.md','profiles/work-document.md','pack/protocol.md')
GUARDS='''사용자의 상위 지침·작업 범위를 따른다. 뜻·확실성·시상·발화 목적을 보존한다.
새로 쓰는 글과 문체 정돈은 사용자가 지정하지 않으면 높임 없는 기본 문체로 쓴다. 기존 글을 고칠 때는 확립된 문체를 유지한다. 사용자가 지정한 높임·장르와 인용·코드 원문은 보존한다.
요청에 필요한 결과·판단·행동만 쓴다. 요청과 무관한 입력 사실 재진술·명칭 통일 안내·작성 과정·누락 정보는 쓰지 않는다. 제시된 검증 상태는 남긴다.
가능성을 사실로, 허락을 명령으로, 미기록을 부재·미배정으로 바꾸지 않는다. 경쟁 후보 없이 행위자가 하나로 회복되면 주체를 생략한다.
확인할 수 없는 필수 정보만 묻는다.
작성: 앵커 추출 → 목적별 정보 묶기 → 조건·참조 배치 → 분할·목록 → 중복 제거 → 양방향 대조.
목록·배치·표제의 형식 선택에서 기존 규칙과 충돌하면 V7의 대상 우선·선택지별 속성·조건 묶음·독립 기한 규칙을 우선한다. 의미와 사용자 지정은 보존한다.
'''
SCOPES={
    'profiles/coding-agent.md':'작업 결과 보고에는 실제 변경·검증·제약을 쓴다. 코드·명령·API 표기를 보존한다.',
    'profiles/chat.md':'사용자의 목적과 공유 문맥에 맞게 답과 필요한 이유를 쓴다.',
    'profiles/work-document.md':'독자의 행동·판단에 필요한 대상·조건·순서·책임·결과를 밝힌다.'}
PRIORITY_RULES=('KP-EDIT-001','KP-SYN-007','KP-SYN-001','KP-EDIT-004',
                'KP-VER-003','KP-VER-007','KP-VER-008','KP-EDIT-002',
                'KP-SYN-006','KP-TXT-001','KP-TXT-002','KP-TXT-006')


def publication_text(rule):
    """Use explicitly reviewed compact prose only for the matching full source."""
    publication = rule.get('publication')
    if publication is None:
        return None
    source = {key: rule[key] for key in ('requirement', 'conditions', 'exceptions')}
    digest = hashlib.sha256(json.dumps(source, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':')).encode('utf-8')).hexdigest()
    if (not isinstance(publication, dict) or not isinstance(publication.get('text'), str)
            or not publication['text'].strip() or publication.get('source_sha256') != digest):
        raise ValueError(rule['id'] + ': publication is empty or stale; review its full source before compiling.')
    return publication['text']


def compile_profiles(root, output, budget=30*1024):
    root=Path(root).resolve()
    output=Path(output).resolve()
    report=validate_root(root)
    if report['errors']:
        raise ValueError('Input validation failed: '+'; '.join(error['code']+' '+error['path'] for error in report['errors']))
    if type(budget) is not int or budget<=0:raise ValueError('Profile byte budget must be a positive integer.')
    notices={name:(root/name).read_text(encoding='utf-8') for name in NOTICE_PATHS}
    reader=Checker(root)
    rules=sorted(reader.read(FILES[0])['rules'],key=lambda rule:
                 (PRIORITY_RULES.index(rule['id']) if rule['id'] in PRIORITY_RULES else len(PRIORITY_RULES), rule['id']))
    # Compile publication requirements only, never research references or case inputs.
    rule_text=[]
    for rule in rules:
        compact = publication_text(rule)
        if compact is not None:
            rule_text.append(f"{rule['id']} {compact}")
            continue
        rule_text.append(f"{rule['id']} {rule['requirement']}")
        if rule['conditions']:rule_text.append('('+'; '.join(rule['conditions'])+')')
        if rule['exceptions']:rule_text.append('['+'; '.join(rule['exceptions'])+']')
    dictionary='`lexicon/core.json`·`lexicon/domains/software.json`에서 뜻·활용·논항·조건을 확인한다. deprecated 대안은 쓰지 않는다.\n'
    # Full rules take priority over an optional glossary; the full lexicon ships separately.
    common='## 원칙\n\n'+GUARDS+'\n## 규칙\n\n(조건 중 하나), [예외]이며 한 문단에 통합한 규칙은 조건·예외를 함께 쓴다.\n\n'+'\n'.join(rule_text)+'\n\n## 어휘\n\n'+dictionary
    contents={name:'# Korean Protocol\n\n'+SCOPES[name]+'\n\n'+common for name in SCOPES}
    detail=['# Korean Protocol 상세 규약\n',GUARDS,'이 규약은 한국어 표현의 설계 초안이다. 구조 검사를 통과해도 LLM의 의미 보존이나 독자의 이해도가 검증되었다고 표현하지 않는다.\n']
    for rule in rules:
        detail.extend(['## '+rule['id']+' '+rule['title']+'\n',rule['requirement']+'\n','적용 범위: '+'; '.join(rule['scope'])+'\n'])
        if rule['conditions']:detail.append('적용 조건: '+'; '.join(rule['conditions'])+'\n')
        if rule['exceptions']:detail.append('예외: '+'; '.join(rule['exceptions'])+'\n')
        positive=rule['positive_example']
        negative=rule['negative_example']
        allowed=rule['counterexample']
        detail.extend([
            '바른 수정의 문맥: '+positive['context']+'\n',
            '원문: '+positive['before']+'\n수정: '+positive['after']+'\n',
            '잘못된 적용의 문맥: '+negative['context']+'\n',
            '잘못된 문장: '+negative['text']+'\n이유: '+negative['reason']+'\n',
            '그대로 허용하는 문맥: '+allowed['context']+'\n',
            '허용 문장: '+allowed['text']+'\n허용 이유: '+allowed['why_allowed']+'\n'])
    detail.extend(['## 어휘 적용\n',dictionary])
    detail.extend(['## License\n',notices['LICENSE'],'## Notices\n',notices['NOTICE.md']])
    contents['pack/protocol.md']='\n'.join(detail)
    for name,text in contents.items():
        if name.startswith('profiles/') and len(text.encode('utf-8'))>budget:
            raise ValueError(f'{name} uses {len(text.encode("utf-8"))} UTF-8 bytes, exceeding the {budget}-byte budget. No profiles were written; reduce publication requirements explicitly.')
    # Preflight all inputs and budgets before any write; each replace is atomic.
    for name,text in contents.items():
        destination=output/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=destination.parent,prefix='.'+destination.name+'-',suffix='.tmp',delete=False) as handle:
            handle.write(text)
            temporary=Path(handle.name)
        temporary.replace(destination)
    return list(PROFILE_PATHS)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--budget',type=int,default=30*1024)
    args=parser.parse_args(argv)
    try:
        names=compile_profiles(args.root,args.output,args.budget)
    except (ValueError,OSError) as exc:
        print(str(exc),file=sys.stderr)
        return 1
    print('Compiled '+', '.join(names)+'. This does not verify LLM semantic performance.')
    return 0


if __name__=='__main__':sys.exit(main())
