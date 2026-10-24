"""Specialize private non-B fixed-Loose shipping search arguments.

This consumes compiler-specialized owned sources. Callback members named search
retain their three arguments. Only the actual eight-argument chess search and its
prototype are changed; unsupported contexts fail instead of guessing.
"""
import re

def _mask(text):
    pattern=re.compile(r'(?m)^[ \t]*\#[^\n]*(?:\\\n[^\n]*)*|//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    return pattern.sub(lambda m:''.join('\n' if c=='\n' else ' ' for c in m.group()),text)

def compact_search_arguments(files,*,variant,development,parallel=0):
    if development or parallel!=0 or variant not in 'ACDEF' or len(variant)!=1:
        raise ValueError('private search arguments require non-B fixed-Loose shipping')
    output=dict(files);observations=[];definitions=0
    for name,data in files.items():
        if not name.endswith('.c'):continue
        text=data.decode();mask=_mask(text);edits=[];calls=0;body_range=None
        for match in re.finditer(r'\bsearch\s*\(',mask):
            start=match.end();paren=1;bracket=brace=0;parts=[];begin=start;end=start
            for end in range(start,len(mask)):
                ch=mask[end]
                if ch=='(':paren+=1
                elif ch==')':
                    paren-=1
                    if not paren:parts.append((begin,end));break
                elif ch=='[':bracket+=1
                elif ch==']':bracket-=1
                elif ch=='{':brace+=1
                elif ch=='}':brace-=1
                elif ch==',' and paren==1 and bracket==0 and brace==0:
                    parts.append((begin,end));begin=end+1
            if paren:raise ValueError('unbalanced search call')
            if len(parts)!=8:continue
            if mask[:match.start()].rstrip().endswith(('.', '>')):
                raise ValueError('unexpected eight-argument search callback member')
            arg=lambda n:re.sub(r'\s+',' ',text[parts[n][0]:parts[n][1]].strip())
            formal=arg(6) in ('unsigned','unsigned excluded') and arg(7) in ('int','int learning')
            if not formal and not (arg(6)=='0' and arg(7) in ('1','learning')):
                raise ValueError('non-B search gained excluded or frozen-learning caller')
            if not formal and arg(7)=='learning' and (body_range is None or not body_range[0]<match.start()<body_range[1]):
                raise ValueError('learning argument is not the specialized search local')
            edits.append((parts[5][1],end,''));calls+=1
            after=end+1
            while after<len(mask) and mask[after].isspace():after+=1
            if formal and after<len(mask) and mask[after]=='{':
                definitions+=1
                nesting=1;stop=after+1
                while stop<len(mask) and nesting:
                    if mask[stop]=='{':nesting+=1
                    elif mask[stop]=='}':nesting-=1
                    stop+=1
                if nesting:raise ValueError('unbalanced search definition')
                body_range=(after,stop)
                edits.append((after+1,after+1,'enum{excluded=0,learning=1};'))
        for begin,end,replacement in sorted(edits,reverse=True):text=text[:begin]+replacement+text[end:]
        output[name]=text.encode()
        observations.append({'file':name,'eight_argument_sites':calls,'bytes_before':len(data),'bytes_after':len(output[name])})
    if definitions!=1:raise ValueError('expected one non-B search definition')
    return output,observations
