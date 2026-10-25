"""One residual P/N/K single-step specialization of the exact admitted D board."""
import hashlib

ORIGINAL_SHA='3f04fedb7e449e69b47ac6f2b36eb89ebe193726ac5970b0ae3a4b28008e12dc'
BEFORE=b'''        int first=a==1?(s>0?12:14):a==2?0:a==3?12:8;
        int last=a==1?first+2:a==2?8:a==4?12:16;
        for(int i=first;i<last;i++){
            int d=steps[i];
            for(int to=from+d;!(to&0x88);to+=d){
                int target=p->b[to];
                if(!moves&&to==sq)return 1;
                if(target*s>0||(moves&&a==1&&!target&&to!=p->e))break;
                if(moves)add(moves,&n,from,to,a==1);
                if(target||a<3||a==6)break;
            }
        }
'''
AFTER=b'''        int first=a==1?(s>0?12:14):a==2?0:8;
        int last=a==1?first+2:a==2?8:16;
        for(int i=first;i<last;i++){
            int to=from+steps[i];if(to&0x88)continue;
            int target=p->b[to];
            if(!moves&&to==sq)return 1;
            if(target*s>0||(moves&&a==1&&!target&&to!=p->e))continue;
            if(moves)add(moves,&n,from,to,a==1);
        }
'''

def transform(original):
    if hashlib.sha256(original).hexdigest()!=ORIGINAL_SHA or original.count(BEFORE)!=1:
        raise ValueError('unknown exact D board/ray fragment')
    candidate=original.replace(BEFORE,AFTER)
    if candidate.count(AFTER)!=1 or candidate.replace(AFTER,BEFORE)!=original:
        raise ValueError('change escaped the one residual walker fragment')
    return candidate
