"""Pure fixed C composition: actual signed-net SIMD state on common PVS/runtime.

The existing C chain is the source/model entry guard. Actual weights, scalar
HCE, remove/store/add setter and 128-bit SIMD bodies come from its passed bytes.
Readable C-owned common regions below regenerate the selected source; previous
C regions regenerate the exact old source for the original literal consumer.
This source+compiler policy variant does not claim old C execution-trace equality.
DEV, canonical C, preprocessing, and earlier guard/helper stages remain separate.
No files, external report, native or A module are read by this helper.
"""
import ast
import hashlib

INPUT_PIN = (9527, '38886cea518a700b7d6f209475dbd80055becce8e4599377a7de0966494f7796')
OUTPUT_PIN = (9093, 'da74d1c079ad0abebbb5a63040ca6f3306943ffb271b00e0117267bce0ee2d93')
PREVIOUS_COMPILER = ['cc', '-std=c11', '-Os', '-pthread', '-DWORKERS=2', '-DTT_BITS=18', '-mavx2', '-DDEV=0', '-x', 'c', '-', '-o', 'x']
_INPUT_MODELS = {'weights-HCE': (975, 232, '63e34ffd42ca656c609cdcc59211f5524eff56522d0cacaa882b7f91c2c92521'), 'sidehash-setter': (1207, 300, '00d772cd802961a7e49b92d0614a40d253ec6855a2cb6771bb4a0e3f9c4fa9c5'), 'SIMD128': (3722, 183, 'c068346cc6ad5f3ff14f42bd2a70630274da43962db7fc9f9edf63b1f7b082c0')}
_OUTPUT_MODELS = {'weights-HCE': (1022, 232, 'dec7e994c60cac349fe7bd469a1160332644d0f042507aa253194e25c8bba4a4'), 'sidehash-setter': (1254, 298, 'd87b3f93ab839ad75080567a10cdc6015e55f42e3cb0e75a05bedbcd21799b24'), 'SIMD128': (3738, 182, '2e1e41758e55d0aa5ede5443a2b62105d67047f63ff73a5fbcf8f5a5b59a492a')}
_BINDINGS = {'weights-HCE': [(b'qm', b'qs', 2), (b'int h(', b'int r(', 1)], 'sidehash-setter': [(b'static M R(const za*p)', b'static W l(const E*p)', 1), (b'return c(', b'return e(', 1), (b'?c(', b'?e(', 1), (b':c(', b':e(', 1), (b'static void K(za*p', b'static void b(E*p', 1), (b'n*h(a,q)', b'n*r(a,q)', 1), (b'qm[k]', b'qs[k]', 1), (b'^=c((M)', b'^=e((W)', 1)], 'SIMD128': [(b'const za*p', b'const E*p', 1), (b'qm', b'qs', 1)]}
_INPUT_GAPS = [(0, 975, '372e381bb67440b5a014f163abd45e03901501eca6421770f7ebfcd3a891608d'), (1207, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1507, 2215, '66b3798b04e3e040197910c0778dd8e299a7a466c82bbb5c0066bafbe5ee576e'), (3905, 5622, '1b6a6009c2f8dc4489561250e86c237750f8287ab122d5b524262efb0ace32a6')]
_OUTPUT_GAPS = [(0, 1022, '56a580a524719c9f588810b0a7631196f1197561aaed74838c81988204ee7be5'), (1254, 0, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'), (1552, 2186, '7dbcc83c196b59a34953d7b02a6de8bb7ab25ba17cf48a2743cd7e3af8b64919'), (3920, 5173, '469c987e58f9e62f3303d478671596c193952f512e5464b42f62cdb9812e32f0')]

_CANONICAL = {
    'previous-C-gap-1-0': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'previous-C-gap-1-directive-1': ('literal', '#define _POSIX_C_SOURCE 200809L\n', 32, '11ea95c064d1e73e0d5455f1d458da179992d79a98c47145a42a7b23143ea0d9'),
    'previous-C-gap-1-directive-3': ('literal', '#include<stdint.h>\n', 19, '584b1c0f6bfcab3462f5b9844577878d32d3294984b8acf8fa8c2f2abda5384a'),
    'previous-C-gap-1-directive-5': ('literal', '#include<stdatomic.h>\n', 22, 'a740a5395dbfde8ac09071c7abf7d888a5fbf5e0aba601e90bc30b1462366d03'),
    'previous-C-gap-1-directive-7': ('literal', '#include<pthread.h>\n', 20, 'b690be08ad0c8b9c01829574562cb7f1d2946aaec2de5f2582a853b2380a22fb'),
    'previous-C-gap-1-directive-9': ('literal', '#include<stdlib.h>\n', 19, 'deea8bab8a65384fd9135e9551d500cb53697e9ed87d6a4b3299a0c3fe44c7aa'),
    'previous-C-gap-1-directive-11': ('literal', '#include<stdio.h>\n', 18, '61003fe92a2bd78aae61845c10ca5e83ed1fbdb24e8a6a34f34b05ee93074794'),
    'previous-C-gap-1-directive-13': ('literal', '#include<string.h>\n', 19, 'cbca550dcde6d7c9b3019139dc9d8e34ac0bfd76b99008441c2ef60264f5f1e9'),
    'previous-C-gap-1-directive-15': ('literal', '#include<time.h>\n', 17, '6fb69b34661e4f3144eadd1b53bef029c8d6d2e1438e324eb8683b2400a30591'),
    'previous-C-gap-1-16': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'previous-C-gap-1-directive-17': ('literal', '#include<limits.h>\n', 19, '7286646545feb8d6ca9c1251f5faf211ff27478b3fc577cf08f52e783536e1d7'),
    'previous-C-gap-1-18-before': ('literal', '\n\n', 2, '75a11da44c802486bc6f65640aa48a730f0f684c5c07a42ba3cd1735eb3fb070'),
    'previous-C-gap-1-18': ('code', r'''typedef uint64_t M ;
typedef unsigned T ;
typedef struct {
    int8_t b [ 128 ] ;
    int16_t x [ 8 ] ;
    int s , c , e , k [ 2 ] , zL ;
    M h , r ;
}
za ;''', 108, 'fa816e6c0fb502293fa00f52c4c227c28a606687b1024e0b2728521383fc506c'),
    'previous-C-gap-1-18-after': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'previous-C-gap-1-directive-19': ('literal', '#define FROM(m) ((m)&119)\n', 26, '7004b6439eb6090f452e54dc659edca24d46eafc8c8990475be3b122dbaf281a'),
    'previous-C-gap-1-directive-21': ('literal', '#define TO(m) (((m)>>7)&127)\n', 29, '25cc7985aee055405a1a857a91b9a49d3a343740fac739183da61d7d7bddea1b'),
    'previous-C-gap-1-directive-23': ('literal', '#define PROMO(m) (((m)>>14)&7)\n', 31, '01cdc98c1d5367674370e727c58d60bf4ef270bd71dfc236ffba81a5490e091e'),
    'previous-C-gap-1-directive-25': ('literal', '#define MOVE(f,t,p) ((T)(f)|((T)(t)<<7)|((T)(p)<<14))\n', 54, '19b5f02ab2bf106f7dcee2d40141f8354112cbfdae1eec40dbc79307bf4020b9'),
    'previous-C-gap-1-26': ('code', r'''typedef struct {
    atomic_flag zY ;
    M zP , zA ;
}
zb ;
typedef struct {
    int id , zB , yl ;
    T zi ;
    M z4 , zQ [ 4096 + 128 ] ;
    int16_t zM [ 128 ] [ 128 ] , zw [ 13 ] [ 13 ] , zx [ 1024 ] ;
}
zd ;
zb * table ;
zd workers [ 2 ] ;
atomic_int stopped ;
M deadline , game_keys [ 4096 ] ;
int game_length ;
za position ;
M k ( void ) {
    struct timespec t ;
    clock_gettime ( CLOCK_MONOTONIC , & t ) ;
    return ( M ) t . tv_sec * 1000 + t . tv_nsec / 1000000 ;
}
static const int steps [ 16 ] = {
    33 , 31 , 18 , 14 , - 14 , - 18 , - 31 , - 33 , 1 , - 1 , 16 , - 16 , 17 , 15 , - 15 , - 17
}
;
M c ( M x ) {
    x += 0x9e3779b97f4a7c15 ;
    x = ( x ^ ( x >> 30 ) ) * 0xbf58476d1ce4e5b9 ;
    x = ( x ^ ( x >> 27 ) ) * 0x94d049bb133111eb ;
    return x ^ ( x >> 31 ) ;
}''', 537, 'a4fb82ef7ea31f568ec3ba6e2a33272c028705b3414ed3b4a0380474b16eb034'),
    'previous-C-gap-3-0': ('code', r'''static int W ( const za * , T * , int , int ) ;
int b ( const za * p , int a , int d ) {
    return W ( p , 0 , a , d ) ;
}
int s ( const za * p ) {
    int d = 0 ;
    for ( int q = 0 ;
    q < 128 ;
    q ++ ) if ( ! ( q & 0x88 ) ) {
        int a = abs ( p -> b [ q ] ) ;
        if ( a == 2 ) {
            if ( d ) return 0 ;
            d = - 1 ;
        }
        else if ( a == 3 ) {
            if ( d < 0 ) return 0 ;
            d |= 1 << ( ( q + ( q >> 4 ) ) & 1 ) ;
            if ( d == 3 ) return 0 ;
        }
        else if ( a && a < 6 ) return 0 ;
    }
    return 1 ;
}
static void C ( za * p ) {
    if ( p -> e < 0 ) return ;
    for ( int d = - 1 ;
    d <= 1 ;
    d += 2 ) {
        int q = p -> e - p -> s * 16 + d ;
        if ( ! ( q & 0x88 ) && p -> b [ q ] == p -> s ) {
            za t = * p ;
            t . b [ q ] = t . b [ p -> e - p -> s * 16 ] = 0 ;
            t . b [ p -> e ] = ( int8_t ) p -> s ;
            if ( ! b ( & t , p -> k [ p -> s < 0 ] , - p -> s ) ) return ;
        }
    }
    p -> e = - 1 ;
}
static int O ( int q ) {
    return q == 4 ? 3 : q == 116 ? 12 : q == 0 ? 2 : q == 7 ? 1 : q == 112 ? 8 : q == 119 ? 4 : 0 ;
}
int e ( const za * p , T m , za * t ) {
    int a = FROM ( m ) , d = TO ( m ) , f = PROMO ( m ) , s = p -> s ;
    int v = p -> b [ a ] , i = p -> b [ d ] ;
    if ( abs ( i ) == 6 ) return 0 ;
    * t = * p ;
    t -> h ^= R ( p ) ;
    t -> zL ++ ;
    t -> e = - 1 ;
    if ( abs ( v ) == 1 ) {
        t -> zL = 0 ;
        if ( d == p -> e && ! i ) K ( t , d - s * 16 , 0 ) ;
        if ( abs ( d - a ) == 32 ) t -> e = a + s * 16 ;
        if ( f ) v = s * f ;
    }
    if ( i ) t -> zL = 0 ;
    if ( abs ( v ) == 6 && abs ( d - a ) == 2 ) {
        int j = d > a ? a + 3 : a - 4 , n = d > a ? a + 1 : a - 1 ;
        K ( t , j , 0 ) ;
        K ( t , n , s * 4 ) ;
    }
    K ( t , a , 0 ) ;
    K ( t , d , v ) ;
    t -> c &= ~ ( O ( a ) | O ( d ) ) ;
    t -> s = - s ;
    if ( b ( t , t -> k [ s < 0 ] , - s ) ) return 0 ;
    C ( t ) ;
    t -> h ^= R ( t ) ;
    t -> r = t -> zL ? ( ( p -> r << 1 ) | ( p -> r >> 63 ) ) ^ t -> h : t -> h ;
    return 1 ;
}
static void g ( T * a , int * n , int zJ , int to , int d ) {
    int f = d > 1 && ! ( to + 16 & 96 ) ;
    for ( int z = f ? 2 : 0 ;
    z <= ( f ? 5 : 0 ) ;
    z ++ ) {
        if ( * n >= 512 ) abort ( ) ;
        a [ ( * n ) ++ ] = MOVE ( zJ , to , z ) | ( d & 1 ) * 8 ;
    }
}
static int W ( const za * p , T * f , int j , int s ) {
    int n = 0 ;
    for ( int m = 0 ;
    m < 128 ;
    m ++ ) {
        if ( m & 0x88 ) {
            m += 7 ;
            continue ;
        }
        int a = abs ( p -> b [ m ] ) ;
        if ( p -> b [ m ] * s <= 0 ) continue ;
        if ( f && a == 1 ) {
            int q = m + s * 16 ;
            if ( ! ( q & 0x88 ) && ! p -> b [ q ] ) {
                g ( f , & n , m , q , 2 ) ;
                if ( ( m >> 4 ) == ( s > 0 ? 1 : 6 ) && ! p -> b [ q + s * 16 ] ) g ( f , & n , m , q + s * 16 , 0 ) ;
            }
        }
        int t = a == 1 ? ( s > 0 ? 12 : 14 ) : a == 2 ? 0 : a == 3 ? 12 : 8 ;
        int u = a == 1 ? t + 2 : a == 2 ? 8 : a == 4 ? 12 : 16 ;
        for ( int i = t ;
        i < u ;
        i ++ ) {
            int d = steps [ i ] ;
            for ( int v = m + d ;
            ! ( v & 0x88 ) ;
            v += d ) {
                int w = p -> b [ v ] ;
                if ( ! f && v == j ) return 1 ;
                if ( w * s > 0 || ( f && a == 1 && ! w && v != p -> e ) ) break ;
                if ( f ) g ( f , & n , m , v , a == 1 ? 3 : ! ! w ) ;
                if ( w || a < 3 || a == 6 ) break ;
            }
        }
        if ( f && a == 6 ) {
            int x = s > 0 ? 4 : 116 , z = s > 0 ? 0 : 2 ;
            if ( m == x && ! b ( p , x , - s ) ) {
                if ( ( p -> c & ( 1 << z ) ) && ! p -> b [ x + 1 ] && ! p -> b [ x + 2 ] && ! b ( p , x + 1 , - s ) ) g ( f , & n , m , x + 2 , 0 ) ;
                if ( ( p -> c & ( 2 << z ) ) && ! p -> b [ x - 1 ] && ! p -> b [ x - 2 ] && ! p -> b [ x - 3 ] && ! b ( p , x - 1 , - s ) ) g ( f , & n , m , x - 2 , 0 ) ;
            }
        }
    }
    return n ;
}
int r ( const za * p , T * a ) {
    return W ( p , a , 0 , p -> s ) ;
}
void q ( za * p ) {
    static const int back [ 8 ] = {
        4 , 2 , 3 , 5 , 6 , 3 , 2 , 4
    }
    ;
    za t = {
        0
    }
    ;
    t . s = 1 ;
    t . c = 15 ;
    t . e = - 1 ;
    for ( int f = 0 ;
    f < 8 ;
    f ++ ) {
        K ( & t , f , back [ f ] ) ;
        K ( & t , 16 + f , 1 ) ;
        K ( & t , 96 + f , - 1 ) ;
        K ( & t , 112 + f , - back [ f ] ) ;
    }
    t . h ^= R ( & t ) ;
    t . r = t . h ;
    * p = t ;
}''', 2214, '805d68e9260e4d755f36e721da0a0482bfc058386de2273cfc0eddb350ec059e'),
    'previous-C-gap-3-0-after': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'previous-C-gap-4-0': ('code', r'''static M J ( M a , M f ) {
    zb * e = table + ( a & ( ( 1u << 18 ) - 1 ) ) ;
    if ( atomic_flag_test_and_set_explicit ( & e -> zY , memory_order_acquire ) ) return 0 ;
    if ( f ) e -> zP = a , e -> zA = f ;
    else f = e -> zP == a ? e -> zA : 0 ;
    atomic_flag_clear_explicit ( & e -> zY , memory_order_release ) ;
    return f ;
}
static int o ( zd * w ) {
    if ( atomic_load_explicit ( & stopped , memory_order_relaxed ) ) return 0 ;
    if ( ! ( w -> z4 & 255 ) && k ( ) >= deadline ) {
        atomic_store ( & stopped , 1 ) ;
        return 0 ;
    }
    ++ w -> z4 ;
    return 1 ;
}
static void E ( int16_t * a , int d ) {
    * a += ( d - * a * d / 16384 ) ;
}
static int I ( int p ) {
    return p + 6 ;
}
static int P ( zd * w , const za * p , int a , int d , int f , int n , int yb , T * u ) {
    if ( ! o ( w ) ) return 0 ;
    int v = b ( p , p -> k [ p -> s < 0 ] , - p -> s ) , x = p -> zL >= 100 ;
    int z = 0 , A = game_length + n ;
    for ( int i = A - 3 ;
    i >= 0 && i >= A - 1 - p -> zL ;
    i -= 2 ) z += w -> zQ [ i ] == p -> h ;
    x |= z >= 2 || s ( p ) ;
    T B [ 512 ] , zj = 0 ;
    int L [ 512 ] , X = r ( p , B ) , Y = 0 , Z = d , zi = - 30000 ;
    int zF = p -> s * U ( p ) ;
    x |= 2 * ( n == 128 - 1 ) ;
    M zP = p -> h ^ c ( p -> r + ( unsigned ) p -> zL ) , zA = x ? 0 : J ( zP , 0 ) ;
    T tt = zA & 131071 ;
    int yl = ( int16_t ) ( zA >> 17 ) , zo = ( zA >> 41 ) & 3 , yz = ( zA >> 33 ) & 255 ;
    if ( yl > 30000 - 128 ) yl -= n ;
    if ( yl < - 30000 + 128 ) yl += n ;
    if ( n && zo && yz >= ( a > 0 ? a : 0 ) && ( zo == 1 || ( zo == 2 && yl >= f ) || ( zo == 3 && yl <= d ) ) ) return yl ;
    int ye = ! x && a <= 0 && ! v ;
    if ( ye ) {
        zi = zF ;
        if ( zi > d ) d = zi ;
    }
    for ( int i = 0 ;
    i < X ;
    i ++ ) {
        T m = B [ i ] ;
        int zJ = FROM ( m ) , to = TO ( m ) , pi = I ( p -> b [ zJ ] ) ;
        L [ i ] = m == tt ? 1000000 : m & 8 ? 500000 + abs ( h ( p -> b [ to ] , to ) ) * 16 - abs ( h ( p -> b [ zJ ] , zJ ) ) : w -> zM [ zJ ] [ to ] + w -> zw [ yb ] [ pi ] + ( int ) ( ( m * 37u + w -> id * 19u ) % 17 ) ;
        if ( PROMO ( m ) ) L [ i ] += 400000 + PROMO ( m ) * 1000 ;
    }
    for ( int i = 0 ;
    i < X ;
    i ++ ) {
        int j = i ;
        for ( int k = i + 1 ;
        k < X ;
        k ++ ) if ( L [ k ] > L [ j ] ) j = k ;
        T m = B [ j ] ;
        B [ j ] = B [ i ] ;
        L [ j ] = L [ i ] ;
        za q ;
        if ( ! e ( p , m , & q ) ) continue ;
        if ( x ) {
            if ( x == 2 ) atomic_store ( & stopped , 1 ) ;
            return 0 ;
        }
        ++ Y ;
        int zJ = FROM ( m ) , to = TO ( m ) , yu = ( m & 8 ) || PROMO ( m ) , pi = I ( q . b [ to ] ) ;
        if ( ye && ( ! yu || d >= f ) ) continue ;
        w -> zQ [ A ] = q . h ;
        if ( Y == 1 || a <= 0 ) yl = - P ( w , & q , a - 1 , - f , - d , n + 1 , pi , 0 ) ;
        else {
            int yg = a >= 4 && Y >= 4 && ! yu && ! v && ! b ( & q , q . k [ q . s < 0 ] , - q . s ) ;
            if ( yg ) {
                yg = zF + w -> zx [ p -> h & 1023 ] / 64 < d + 100 ;
            }
            yl = - P ( w , & q , a - 1 - yg , - d - 1 , - d , n + 1 , pi , 0 ) ;
            if ( yg && yl > d ) yl = - P ( w , & q , a - 1 , - d - 1 , - d , n + 1 , pi , 0 ) ;
            if ( yl > d && yl < f ) yl = - P ( w , & q , a - 1 , - f , - d , n + 1 , pi , 0 ) ;
        }
        if ( atomic_load_explicit ( & stopped , memory_order_relaxed ) ) return 0 ;
        if ( yl > zi ) {
            zi = yl ;
            zj = m ;
            if ( u ) * u = m ;
        }
        if ( yl > d ) d = yl ;
        if ( d >= f ) {
            if ( a > 0 && ! yu ) {
                int zn = a * a ;
                E ( & w -> zM [ zJ ] [ to ] , zn ) ;
                E ( & w -> zw [ yb ] [ pi ] , zn ) ;
            }
            break ;
        }
    }
    if ( ! Y ) return v ? - 30000 + n : 0 ;
    zo = zi <= Z ? 3 : zi >= f ? 2 : 1 ;
    if ( a > 0 && zo == 1 && ! v && zj && ! ( zj & 8 ) && ! PROMO ( zj ) && abs ( zi ) < 30000 - 128 ) {
        int zE = zi - zF ;
        if ( zE > 256 ) zE = 256 ;
        if ( zE < - 256 ) zE = - 256 ;
        w -> zx [ p -> h & 1023 ] += zE - w -> zx [ p -> h & 1023 ] / 64 ;
    }
    yl = zi ;
    if ( yl > 30000 - 128 ) yl += n ;
    if ( yl < - 30000 + 128 ) yl -= n ;
    zA = zj | ( ( M ) ( uint16_t ) yl << 17 ) | ( ( M ) ( a > 0 ? a : 0 ) << 33 ) | ( ( M ) zo << 41 ) ;
    J ( zP , zA ) ;
    return zi ;
}
void d ( zd * w , const za * p ) {
    w -> z4 = 0 ;
    w -> zB = 0 ;
    w -> yl = 0 ;
    w -> zi = 0 ;
    memcpy ( w -> zQ , game_keys , game_length * sizeof ( M ) ) ;
    for ( int a = 1 ;
    a <= 128 - 2 ;
    a ++ ) {
        T d = w -> zi ;
        int f = P ( w , p , a , - 30000 , 30000 , 0 , 6 , & d ) ;
        if ( atomic_load_explicit ( & stopped , memory_order_relaxed ) ) break ;
        w -> zi = d ;
        w -> yl = f ;
        w -> zB = a ;
    }
}
static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER ;
static pthread_cond_t command = PTHREAD_COND_INITIALIZER ;
static unsigned epoch ;
static int pending = 2 , quitting ;
static void S ( T m , char * s ) {
    if ( ! m ) {
        strcpy ( s , "0000" ) ;
        return ;
    }
    s [ 0 ] = 'a' + ( FROM ( m ) & 7 ) ;
    s [ 1 ] = '1' + ( FROM ( m ) >> 4 ) ;
    s [ 2 ] = 'a' + ( TO ( m ) & 7 ) ;
    s [ 3 ] = '1' + ( TO ( m ) >> 4 ) ;
    s [ 4 ] = "  nbrq" [ PROMO ( m ) ] ;
    s [ 4 + ! ! PROMO ( m ) ] = 0 ;
}
static T G ( const za * b , const char * s , za * c ) {
    T a [ 512 ] ;
    char d [ 6 ] ;
    int n = r ( b , a ) ;
    for ( int i = 0 ;
    i < n ;
    i ++ ) {
        if ( s ) {
            S ( a [ i ] , d ) ;
            if ( strcmp ( s , d ) ) continue ;
        }
        if ( e ( b , a [ i ] , c ) ) return a [ i ] ;
    }
    return 0 ;
}
static void N ( void ) {
    zd * w = workers + ( workers [ 1 ] . zB > workers [ 0 ] . zB ) ;
    za fb ;
    T a = w -> zi ? w -> zi : G ( & position , 0 , & fb ) ;
    char d [ 6 ] ;
    S ( a , d ) ;
    printf ( "bestmove %s\n" , d ) ;
    fflush ( stdout ) ;
}
static void * u ( void * p ) {
    zd * w = 0 ;
    unsigned a = 0 ;
    pthread_mutex_lock ( & mutex ) ;
    for ( ;
    ;
    ) {
        if ( ! -- pending ) {
            if ( w ) N ( ) ;
            pthread_cond_broadcast ( & command ) ;
        }
        while ( a == epoch && ! quitting ) pthread_cond_wait ( & command , & mutex ) ;
        if ( quitting ) break ;
        w = p ;
        a = epoch ;
        pthread_mutex_unlock ( & mutex ) ;
        d ( w , & position ) ;
        pthread_mutex_lock ( & mutex ) ;
    }
    pthread_mutex_unlock ( & mutex ) ;
    return NULL ;
}
static void V ( void ) {
    atomic_store ( & stopped , 1 ) ;
    pthread_mutex_lock ( & mutex ) ;
    while ( pending ) pthread_cond_wait ( & command , & mutex ) ;
    pthread_mutex_unlock ( & mutex ) ;
}
static void y ( void ) {
    for ( size_t i = 0 ;
    i < ( 1 << 18 ) ;
    i ++ ) atomic_flag_clear ( & table [ i ] . zY ) ;
}
static char * nt ( void ) {
    return strtok ( NULL , " \t\r\n" ) ;
}
static void Q ( void ) {
    za b , c ;
    M a [ 4096 ] ;
    int n = 1 ;
    char * d = nt ( ) ;
    if ( ! d || strcmp ( d , "startpos" ) ) return ;
    q ( & b ) ;
    a [ 0 ] = b . h ;
    d = nt ( ) ;
    if ( d ) {
        if ( strcmp ( d , "moves" ) ) return ;
        while ( ( d = nt ( ) ) ) {
            if ( n == 4096 || ! G ( & b , d , & c ) ) return ;
            b = c ;
            a [ n ++ ] = b . h ;
        }
    }
    position = b ;
    game_length = n ;
    memcpy ( game_keys , a , n * sizeof * a ) ;
}
static M F ( const char * s ) {
    char * e ;
    if ( ! s || ( unsigned ) ( * s - '0' ) > 9 ) return 0 ;
    M n = strtoull ( s , & e , 10 ) ;
    return * e || n >> 63 ? 0 : n ;
}
static void D ( void ) {
    V ( ) ;
    M a = - 1 , d = 0 , f = 0 ;
    for ( char * t = nt ( ) ;
    t ;
    t = nt ( ) ) {
        if ( ( * t == 'w' || * t == 'b' ) && ( ! strcmp ( t + 1 , "time" ) || ! strcmp ( t + 1 , "inc" ) ) ) {
            M n = F ( nt ( ) ) ;
            if ( ( * t == 'w' ) == ( position . s > 0 ) ) {
                if ( t [ 1 ] == 't' ) a = n ;
                else d = n ;
            }
        }
    }
    if ( ~ a ) {
        f = a / 30 + ( d > 86400000 ? 86400000 : d ) * 3 / 4 ;
        if ( f > a / 5 ) f = a / 5 ;
        if ( ! f ) f = 1 ;
    }
    else f = 1000 ;
    deadline = k ( ) + ( f > 86400000 ? 86400000 : f ) ;
    atomic_store ( & stopped , 0 ) ;
    pthread_mutex_lock ( & mutex ) ;
    pending = 2 ;
    epoch ++ ;
    pthread_cond_broadcast ( & command ) ;
    pthread_mutex_unlock ( & mutex ) ;
}
int main ( void ) {
    pthread_t a [ 2 ] ;
    int d = 0 , f = 0 ;
    char j [ 32768 ] ;
    table = calloc ( 1 << 18 , sizeof * table ) ;
    if ( ! table ) return 2 ;
    y ( ) ;
    q ( & position ) ;
    game_keys [ 0 ] = position . h ;
    game_length = 1 ;
    for ( ;
    d < 2 ;
    d ++ ) {
        workers [ d ] . id = d ;
        if ( pthread_create ( a + d , NULL , u , workers + d ) ) {
            f = 2 ;
            goto shutdown ;
        }
    }
    V ( ) ;
    while ( fgets ( j , sizeof j , stdin ) ) {
        if ( ! strchr ( j , '\n' ) ) {
            int n = getchar ( ) ;
            if ( n != EOF && n != '\n' ) {
                do {
                    n = getchar ( ) ;
                }
                while ( n != EOF && n != '\n' ) ;
                continue ;
            }
        }
        char * p = strtok ( j , " \t\r\n" ) ;
        if ( ! p ) continue ;
        if ( ! strcmp ( p , "uci" ) ) {
            puts ( "uciok" ) ;
            fflush ( stdout ) ;
        }
        else if ( ! strcmp ( p , "isready" ) ) {
            puts ( "readyok" ) ;
            fflush ( stdout ) ;
        }
        else if ( ! strcmp ( p , "quit" ) ) break ;
        else if ( ! strcmp ( p , "position" ) ) {
            V ( ) ;
            Q ( ) ;
        }
        else if ( ! strcmp ( p , "go" ) ) D ( ) ;
    }
    V ( ) ;
    shutdown : pthread_mutex_lock ( & mutex ) ;
    quitting = 1 ;
    pthread_cond_broadcast ( & command ) ;
    pthread_mutex_unlock ( & mutex ) ;
    for ( int i = 0 ;
    i < d ;
    i ++ ) if ( pthread_join ( a [ i ] , NULL ) ) f = 2 ;
    free ( table ) ;
    return f ;
}''', 5621, 'fb73e1445c2ee1982c0d7e13f9443aa4f21f1ef54e45deff71c8e74f3f8719bd'),
    'previous-C-gap-4-0-after': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'selected-common-C-gap-1-0': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'selected-common-C-gap-1-directive-1': ('literal', '#define _POSIX_C_SOURCE 200809L\n', 32, '11ea95c064d1e73e0d5455f1d458da179992d79a98c47145a42a7b23143ea0d9'),
    'selected-common-C-gap-1-directive-3': ('literal', '#include <stdint.h>\n', 20, 'dd1e65241020275e480c9f023566ad3d27cad42dfac5d4d1b9c176732d1eede5'),
    'selected-common-C-gap-1-directive-5': ('literal', '#include <stdatomic.h>\n', 23, 'c3eccdb5117e4d76c50ac3ced5b73fe8dda3c3583e47e85e5f898d60b3532e10'),
    'selected-common-C-gap-1-directive-7': ('literal', '#include <pthread.h>\n', 21, 'e6c0a1187a7165fe16302207e55480caf91c82e13efa73a49e920b520d7d8e49'),
    'selected-common-C-gap-1-directive-9': ('literal', '#include <stdlib.h>\n', 20, '0255684c4d6c1527072949458c753df8cd146612251d4ba3fe3b22a7e063cec1'),
    'selected-common-C-gap-1-directive-11': ('literal', '#include <stdio.h>\n', 19, 'd3139b187138b0a2b1fd9b889746cb293f2dfc1ec526153bb345b1617eca9ef4'),
    'selected-common-C-gap-1-directive-13': ('literal', '#include <string.h>\n', 20, '7c7dfb862fbd4063378bb2086e49db0857322c3de8cb9d570f175da1d253a682'),
    'selected-common-C-gap-1-directive-15': ('literal', '#include <time.h>\n', 18, 'b0435d5a79b71fa5959ff0c96fa0ff267156768e8d969da1e22f3c7c1a27e6f7'),
    'selected-common-C-gap-1-directive-17': ('literal', '#include<limits.h>\n', 19, '7286646545feb8d6ca9c1251f5faf211ff27478b3fc577cf08f52e783536e1d7'),
    'selected-common-C-gap-1-18': ('literal', '\n\n', 2, '75a11da44c802486bc6f65640aa48a730f0f684c5c07a42ba3cd1735eb3fb070'),
    'selected-common-C-gap-1-directive-19': ('literal', '#define PLY 128\n', 16, 'a8b473df816395dc9069d1f58a9ce5d355011b97fb601ff4984ec7b666eba274'),
    'selected-common-C-gap-1-20': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'selected-common-C-gap-1-directive-21': ('literal', '#define MOVES 512\n', 18, 'bcdfa8ec7224a0bfac75c77fa0d2a71f7c5c6ef1075a51e5aa6c7d8ac1c0673d'),
    'selected-common-C-gap-1-directive-23': ('literal', '#define HISTORY 4096\n', 21, '6edade73b5b7915ea348837ea97c9ccbcb19229e6f1391131360760e2b5fb124'),
    'selected-common-C-gap-1-directive-25': ('literal', '#define MATE 30000\n', 19, '0c746e959c8ba01c163f409945c463b789f3aaebcf5cb78ab38711445a09c28f'),
    'selected-common-C-gap-1-26': ('code', r'''typedef uint64_t W ;
typedef int16_t X ;
typedef unsigned Y ;
typedef struct {
    int8_t b [ 128 ] ;
    int16_t x [ 8 ] ;
    int s , c , e , k [ 2 ] , aI ;
    W h , r ;
}
E ;''', 125, '74fc3bbbe83f63a660392dee47f234c18087726e1873207adb3f3015dcc3c434'),
    'selected-common-C-gap-1-26-after': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'selected-common-C-gap-1-directive-27': ('literal', '#define FROM(m) ((m)&119)\n', 26, '7004b6439eb6090f452e54dc659edca24d46eafc8c8990475be3b122dbaf281a'),
    'selected-common-C-gap-1-directive-29': ('literal', '#define TO(m) (((m)>>7)&127)\n', 29, '25cc7985aee055405a1a857a91b9a49d3a343740fac739183da61d7d7bddea1b'),
    'selected-common-C-gap-1-directive-31': ('literal', '#define PROMO(m) (((m)>>14)&7)\n', 31, '01cdc98c1d5367674370e727c58d60bf4ef270bd71dfc236ffba81a5490e091e'),
    'selected-common-C-gap-1-directive-33': ('literal', '#define MOVE(f,t,p) ((Y)(f)|((Y)(t)<<7)|((Y)(p)<<14))\n', 54, '1d3b6274e74c471732e79536b09eaaac5160a4305b7d5d39c2a235af4cf1e8e1'),
    'selected-common-C-gap-1-34': ('code', r'''typedef struct {
    atomic_flag zN ;
    W aT , U ;
}
Z ;
typedef struct {
    int id , C , l ;
    Y H ;
    W a5 , aA [ HISTORY + PLY ] ;
    X zC [ 128 ] [ 128 ] , an [ 13 ] [ 13 ] , ah [ 1024 ] ;
}
ai ;
Z * qq ;
ai qr [ 2 ] ;
atomic_int qp ;
W qc , qg [ HISTORY ] ;
int qh ;
E ql ;
W u ( void ) {
    struct timespec t ;
    clock_gettime ( CLOCK_MONOTONIC , & t ) ;
    return ( W ) t . tv_sec * 1000 + t . tv_nsec / 1000000 ;
}
static const int qo [ 16 ] = {
    33 , 31 , 18 , 14 , - 14 , - 18 , - 31 , - 33 , 1 , - 1 , 16 , - 16 , 17 , 15 , - 15 , - 17
}
;
W e ( W x ) {
    x += 0x9e3779b97f4a7c15 ;
    x = ( x ^ ( x >> 30 ) ) * 0xbf58476d1ce4e5b9 ;
    x = ( x ^ ( x >> 27 ) ) * 0x94d049bb133111eb ;
    return x ^ ( x >> 31 ) ;
}''', 486, 'b313a0d2be7fca512e56079ce45b9100ec1a03b8ac05d4084a4b930c5848b08b'),
    'selected-common-C-gap-3-0': ('code', r'''static int g ( const E * , Y * , int , int ) ;
int c ( const E * p , int a , int d ) {
    return g ( p , 0 , a , d ) ;
}
int ap ( const E * p ) {
    int d = 0 ;
    for ( int q = 0 ;
    q < 128 ;
    q ++ ) if ( ! ( q & 0x88 ) ) {
        int a = abs ( p -> b [ q ] ) ;
        if ( a == 2 ) {
            if ( d ) return 0 ;
            d = - 1 ;
        }
        else if ( a == 3 ) {
            if ( d < 0 ) return 0 ;
            d |= 1 << ( ( q + ( q >> 4 ) ) & 1 ) ;
            if ( d == 3 ) return 0 ;
        }
        else if ( a && a < 6 ) return 0 ;
    }
    return 1 ;
}
static void D ( E * p ) {
    if ( p -> e < 0 ) return ;
    for ( int d = - 1 ;
    d <= 1 ;
    d += 2 ) {
        int q = p -> e - p -> s * 16 + d ;
        if ( ! ( q & 0x88 ) && p -> b [ q ] == p -> s ) {
            E t = * p ;
            t . b [ q ] = t . b [ p -> e - p -> s * 16 ] = 0 ;
            t . b [ p -> e ] = ( int8_t ) p -> s ;
            if ( ! c ( & t , p -> k [ p -> s < 0 ] , - p -> s ) ) return ;
        }
    }
    p -> e = - 1 ;
}
static int n ( int q ) {
    return q == 4 ? 3 : q == 116 ? 12 : q == 0 ? 2 : q == 7 ? 1 : q == 112 ? 8 : q == 119 ? 4 : 0 ;
}
int v ( const E * p , Y m , E * w ) {
    int o = FROM ( m ) , a = TO ( m ) , d = PROMO ( m ) , s = p -> s , v = p -> b [ o ] , f = p -> b [ a ] ;
    if ( abs ( f ) == 6 ) return 0 ;
    * w = * p ;
    w -> h ^= l ( p ) ;
    w -> aI ++ ;
    w -> e = - 1 ;
    if ( abs ( v ) == 1 ) {
        w -> aI = 0 ;
        if ( a == p -> e && ! f ) b ( w , a - s * 16 , 0 ) ;
        if ( abs ( a - o ) == 32 ) w -> e = o + s * 16 ;
        if ( d ) v = s * d ;
    }
    if ( f ) w -> aI = 0 ;
    if ( abs ( v ) == 6 && abs ( a - o ) == 2 ) {
        int g = a > o ? o + 3 : o - 4 , i = a > o ? o + 1 : o - 1 ;
        b ( w , g , 0 ) ;
        b ( w , i , s * 4 ) ;
    }
    b ( w , o , 0 ) ;
    b ( w , a , v ) ;
    w -> c &= ~ ( n ( o ) | n ( a ) ) ;
    w -> s = - s ;
    if ( c ( w , w -> k [ s < 0 ] , - s ) ) return 0 ;
    D ( w ) ;
    w -> h ^= l ( w ) ;
    w -> r = w -> aI ? ( ( p -> r << 1 ) | ( p -> r >> 63 ) ) ^ w -> h : w -> h ;
    return 1 ;
}
static void k ( Y * B , int * n , int o , int to , int a ) {
    int d = a > 1 && ! ( to + 16 & 96 ) ;
    for ( int z = d ? 2 : 0 ;
    z <= ( d ? 5 : 0 ) ;
    z ++ ) {
        if ( * n >= 512 ) abort ( ) ;
        B [ ( * n ) ++ ] = MOVE ( o , to , z ) | ( a & 1 ) * 8 ;
    }
}
static int g ( const E * p , Y * B , int f , int s ) {
    int n = 0 ;
    for ( int o = 0 ;
    o < 128 ;
    o ++ ) {
        if ( o & 0x88 ) {
            o += 7 ;
            continue ;
        }
        int a = abs ( p -> b [ o ] ) ;
        if ( p -> b [ o ] * s <= 0 ) continue ;
        if ( B && a == 1 ) {
            int g = o + s * 16 ;
            if ( ! ( g & 0x88 ) && ! p -> b [ g ] ) {
                k ( B , & n , o , g , 2 ) ;
                if ( ( o >> 4 ) == ( s > 0 ? 1 : 6 ) && ! p -> b [ g + s * 16 ] ) k ( B , & n , o , g + s * 16 , 0 ) ;
            }
        }
        int j = a == 1 ? ( s > 0 ? 12 : 14 ) : a == 2 ? 0 : a == 3 ? 12 : 8 , m = a == 1 ? j + 2 : a == 2 ? 8 : a == 4 ? 12 : 16 ;
        for ( int i = j ;
        i < m ;
        i ++ ) {
            int d = qo [ i ] ;
            for ( int q = o + d ;
            ! ( q & 0x88 ) ;
            q += d ) {
                int t = p -> b [ q ] ;
                if ( ! B && q == f ) return 1 ;
                if ( t * s > 0 || ( B && a == 1 && ! t && q != p -> e ) ) break ;
                if ( B ) k ( B , & n , o , q , a == 1 ? 3 : ! ! t ) ;
                if ( t || a < 3 || a == 6 ) break ;
            }
        }
        if ( B && a == 6 ) {
            int u = s > 0 ? 4 : 116 , w = s > 0 ? 0 : 2 ;
            if ( o == u && ! c ( p , u , - s ) ) {
                if ( ( p -> c & ( 1 << w ) ) && ! p -> b [ u + 1 ] && ! p -> b [ u + 2 ] && ! c ( p , u + 1 , - s ) ) k ( B , & n , o , u + 2 , 0 ) ;
                if ( ( p -> c & ( 2 << w ) ) && ! p -> b [ u - 1 ] && ! p -> b [ u - 2 ] && ! p -> b [ u - 3 ] && ! c ( p , u - 1 , - s ) ) k ( B , & n , o , u - 2 , 0 ) ;
            }
        }
    }
    return n ;
}
int T ( const E * p , Y * B ) {
    return g ( p , B , 0 , p -> s ) ;
}
void q ( E * p ) {
    static const int qa [ 8 ] = {
        4 , 2 , 3 , 5 , 6 , 3 , 2 , 4
    }
    ;
    E t = {
        0
    }
    ;
    t . s = 1 ;
    t . c = 15 ;
    t . e = - 1 ;
    for ( int f = 0 ;
    f < 8 ;
    f ++ ) {
        b ( & t , f , qa [ f ] ) ;
        b ( & t , 16 + f , 1 ) ;
        b ( & t , 96 + f , - 1 ) ;
        b ( & t , 112 + f , - qa [ f ] ) ;
    }
    t . h ^= l ( & t ) ;
    t . r = t . h ;
    * p = t ;
}''', 2185, '883f16018a6c853d20f281a88f8a2504a4c6533b9d90e5b86def97aa28606c88'),
    'selected-common-C-gap-3-0-after': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
    'selected-common-C-gap-4-0': ('code', r'''static W V ( W a , W U ) {
    Z * e = qq + ( a & ( ( 1u << 18 ) - 1 ) ) ;
    if ( atomic_flag_test_and_set_explicit ( & e -> zN , memory_order_acquire ) ) return 0 ;
    if ( U ) e -> aT = a , e -> U = U ;
    else U = e -> aT == a ? e -> U : 0 ;
    atomic_flag_clear_explicit ( & e -> zN , memory_order_release ) ;
    return U ;
}
static int ay ( ai * w ) {
    if ( atomic_load_explicit ( & qp , memory_order_relaxed ) ) return 0 ;
    if ( ! ( w -> a5 & 255 ) && u ( ) >= qc ) {
        atomic_store ( & qp , 1 ) ;
        return 0 ;
    }
    ++ w -> a5 ;
    return 1 ;
}
static void O ( X * a , int d ) {
    * a += ( d - * a * d / 16384 ) ;
}
static int s ( int p ) {
    return p + 6 ;
}
static int h ( ai * w , const E * p , int C , int G , int a , int d , int f , Y * g ) {
    if ( ! ay ( w ) ) return 0 ;
    int n = c ( p , p -> k [ p -> s < 0 ] , - p -> s ) , t = p -> aI >= 100 , u = 0 , x = qh + d - 1 - p -> aI ;
    if ( x < 0 ) x = 0 ;
    for ( int i = qh + d - 3 ;
    i >= x ;
    i -= 2 ) u += w -> aA [ i ] == p -> h ;
    t |= u >= 2 || ap ( p ) ;
    t |= ( d == PLY - 1 ) * 2 ;
    Y B [ MOVES ] , N = 0 ;
    int y [ MOVES ] , z = T ( p , B ) , A = 0 , D = G , H = - MATE , F = p -> s * U ( p ) ;
    W I = p -> h ^ e ( p -> r + ( unsigned ) p -> aI ) , U = t ? 0 : V ( I , 0 ) ;
    Y J = U & 131071 ;
    int l = ( X ) ( U >> 17 ) , K = ( U >> 41 ) & 3 , L = ( U >> 33 ) & 255 ;
    if ( l > MATE - PLY ) l -= d ;
    if ( l < - MATE + PLY ) l += d ;
    if ( d && K && L >= ( C > 0 ? C : 0 ) && ( K == 1 || ( K == 2 && l >= a ) || ( K == 3 && l <= G ) ) ) return l ;
    int M = ! t && C <= 0 && ! n ;
    if ( M ) {
        H = F ;
        if ( H > G ) G = H ;
    }
    for ( int i = 0 ;
    i < z ;
    i ++ ) {
        Y m = B [ i ] ;
        int o = FROM ( m ) , P = TO ( m ) , R = s ( p -> b [ o ] ) ;
        y [ i ] = m == J ? 1000000 : m & 8 ? 500000 + abs ( r ( p -> b [ P ] , P ) ) * 16 - abs ( r ( p -> b [ o ] , o ) ) : w -> zC [ o ] [ P ] + w -> an [ f ] [ R ] + ( int ) ( ( m * 37u + w -> id * 19u ) % 17 ) ;
        if ( PROMO ( m ) ) y [ i ] += 400000 + PROMO ( m ) * 1000 ;
    }
    for ( int i = 0 ;
    i < z ;
    i ++ ) {
        int j = i ;
        for ( int k = i + 1 ;
        k < z ;
        k ++ ) if ( y [ k ] > y [ j ] ) j = k ;
        Y m = B [ j ] ;
        B [ j ] = B [ i ] ;
        y [ j ] = y [ i ] ;
        E q ;
        if ( ! v ( p , m , & q ) ) continue ;
        if ( t ) {
            if ( t == 2 ) atomic_store ( & qp , 1 ) ;
            return 0 ;
        }
        ++ A ;
        int o = FROM ( m ) , P = TO ( m ) , Q = ( m & 8 ) || PROMO ( m ) , R = s ( q . b [ P ] ) ;
        if ( M && ( ! Q || G >= a ) ) continue ;
        w -> aA [ qh + d ] = q . h ;
        if ( A == 1 || C <= 0 ) l = - h ( w , & q , C - 1 , - a , - G , d + 1 , R , 0 ) ;
        else {
            int S = C >= 4 && A >= 4 && ! Q && ! n && ! c ( & q , q . k [ q . s < 0 ] , - q . s ) ;
            if ( S ) {
                S = F + w -> ah [ p -> h & 1023 ] / 64 < G + 100 ;
            }
            l = - h ( w , & q , C - 1 - S , - G - 1 , - G , d + 1 , R , 0 ) ;
            if ( S && l > G ) l = - h ( w , & q , C - 1 , - G - 1 , - G , d + 1 , R , 0 ) ;
            if ( l > G && l < a ) l = - h ( w , & q , C - 1 , - a , - G , d + 1 , R , 0 ) ;
        }
        if ( atomic_load_explicit ( & qp , memory_order_relaxed ) ) return 0 ;
        if ( l > H ) {
            H = l ;
            N = m ;
            if ( g ) * g = m ;
        }
        if ( l > G ) G = l ;
        if ( G >= a ) {
            if ( C > 0 && ! Q ) {
                int S = C * C ;
                O ( & w -> zC [ o ] [ P ] , S ) ;
                O ( & w -> an [ f ] [ R ] , S ) ;
            }
            break ;
        }
    }
    if ( ! A ) return n ? - MATE + d : 0 ;
    K = H <= D ? 3 : H >= a ? 2 : 1 ;
    if ( C > 0 && K == 1 && ! n && N && ! ( N & 8 ) && ! PROMO ( N ) && abs ( H ) < MATE - PLY ) {
        int S = H - F ;
        if ( S > 256 ) S = 256 ;
        if ( S < - 256 ) S = - 256 ;
        w -> ah [ p -> h & 1023 ] += S - w -> ah [ p -> h & 1023 ] / 64 ;
    }
    l = H ;
    if ( l > MATE - PLY ) l += d ;
    if ( l < - MATE + PLY ) l -= d ;
    U = N | ( ( W ) ( uint16_t ) l << 17 ) | ( ( W ) ( C > 0 ? C : 0 ) << 33 ) | ( ( W ) K << 41 ) ;
    V ( I , U ) ;
    return H ;
}
void C ( ai * w , const E * p ) {
    w -> a5 = 0 ;
    w -> C = 0 ;
    w -> l = 0 ;
    w -> H = 0 ;
    memcpy ( w -> aA , qg , qh * sizeof ( W ) ) ;
    for ( int C = 1 ;
    C <= PLY - 2 ;
    C ++ ) {
        Y H = w -> H ;
        int l = h ( w , p , C , - MATE , MATE , 0 , 6 , & H ) ;
        if ( atomic_load_explicit ( & qp , memory_order_relaxed ) ) break ;
        w -> H = H ;
        w -> l = l ;
        w -> C = C ;
    }
}
static pthread_mutex_t qj = PTHREAD_MUTEX_INITIALIZER ;
static pthread_cond_t qb = PTHREAD_COND_INITIALIZER ;
static unsigned qd ;
static int qk = 2 , qm ;
static void o ( Y m , char * s ) {
    if ( ! m ) {
        strcpy ( s , "0000" ) ;
        return ;
    }
    s [ 0 ] = 'a' + ( FROM ( m ) & 7 ) ;
    s [ 1 ] = '1' + ( FROM ( m ) >> 4 ) ;
    s [ 2 ] = 'a' + ( TO ( m ) & 7 ) ;
    s [ 3 ] = '1' + ( TO ( m ) >> 4 ) ;
    s [ 4 ] = "  nbrq" [ PROMO ( m ) ] ;
    s [ 4 + ! ! PROMO ( m ) ] = 0 ;
}
static Y i ( const E * b , const char * s , E * c ) {
    Y a [ MOVES ] ;
    char d [ 6 ] ;
    int n = T ( b , a ) ;
    for ( int i = 0 ;
    i < n ;
    i ++ ) {
        if ( s ) {
            o ( a [ i ] , d ) ;
            if ( strcmp ( s , d ) ) continue ;
        }
        if ( v ( b , a [ i ] , c ) ) return a [ i ] ;
    }
    return 0 ;
}
static void x ( void ) {
    ai * w = qr + ( qr [ 1 ] . C > qr -> C ) ;
    E fb ;
    Y H = w -> H ? w -> H : i ( & ql , 0 , & fb ) ;
    char a [ 6 ] ;
    o ( H , a ) ;
    printf ( "bestmove %s\n" , a ) ;
    fflush ( stdout ) ;
}
static void * A ( void * p ) {
    ai * w = 0 ;
    unsigned a = 0 ;
    pthread_mutex_lock ( & qj ) ;
    for ( ;
    ;
    ) {
        if ( ! -- qk ) {
            if ( w ) x ( ) ;
            pthread_cond_broadcast ( & qb ) ;
        }
        while ( a == qd && ! qm ) pthread_cond_wait ( & qb , & qj ) ;
        if ( qm ) break ;
        w = p ;
        a = qd ;
        pthread_mutex_unlock ( & qj ) ;
        C ( w , & ql ) ;
        pthread_mutex_lock ( & qj ) ;
    }
    pthread_mutex_unlock ( & qj ) ;
    return NULL ;
}
static void j ( void ) {
    atomic_store ( & qp , 1 ) ;
    pthread_mutex_lock ( & qj ) ;
    while ( qk ) pthread_cond_wait ( & qb , & qj ) ;
    pthread_mutex_unlock ( & qj ) ;
}
static void B ( void ) {
    for ( size_t i = 0 ;
    i < ( 1 << 18 ) ;
    i ++ ) atomic_flag_clear ( & qq [ i ] . zN ) ;
}
static char * nt ( void ) {
    return strtok ( NULL , " \t\r\n" ) ;
}
static void z ( void ) {
    E b , c ;
    W a [ HISTORY ] ;
    int n = 1 ;
    char * B = nt ( ) ;
    if ( ! B || strcmp ( B , "startpos" ) ) return ;
    q ( & b ) ;
    a [ 0 ] = b . h ;
    B = nt ( ) ;
    if ( B ) {
        if ( strcmp ( B , "moves" ) ) return ;
        while ( ( B = nt ( ) ) ) {
            if ( n == HISTORY || ! i ( & b , B , & c ) ) return ;
            b = c ;
            a [ n ++ ] = b . h ;
        }
    }
    ql = b ;
    qh = n ;
    memcpy ( qg , a , n * sizeof * a ) ;
}
static W y ( const char * s ) {
    char * e ;
    if ( ! s || ( unsigned ) ( * s - '0' ) > 9 ) return 0 ;
    W n = strtoull ( s , & e , 10 ) ;
    return * e || n >> 63 ? 0 : n ;
}
static void w ( void ) {
    j ( ) ;
    W a = - 1 , d = 0 , S = 0 ;
    for ( char * t = nt ( ) ;
    t ;
    t = nt ( ) ) {
        if ( ( * t == 'w' || * t == 'b' ) && ( ! strcmp ( t + 1 , "time" ) || ! strcmp ( t + 1 , "inc" ) ) ) {
            W n = y ( nt ( ) ) ;
            if ( ( * t == 'w' ) == ( ql . s > 0 ) ) {
                if ( t [ 1 ] == 't' ) a = n ;
                else d = n ;
            }
        }
    }
    if ( ~ a ) {
        S = a / 30 + ( d > 86400000 ? 86400000 : d ) * 3 / 4 ;
        if ( S > a / 5 ) S = a / 5 ;
        if ( ! S ) S = 1 ;
    }
    else S = 1000 ;
    qc = u ( ) + ( S > 86400000 ? 86400000 : S ) ;
    atomic_store ( & qp , 0 ) ;
    pthread_mutex_lock ( & qj ) ;
    qk = 2 ;
    qd ++ ;
    pthread_cond_broadcast ( & qb ) ;
    pthread_mutex_unlock ( & qj ) ;
}
int main ( void ) {
    pthread_t a [ 2 ] ;
    int V = 0 , d = 0 ;
    char R [ 32768 ] ;
    qq = calloc ( 1 << 18 , sizeof * qq ) ;
    if ( ! qq ) return 2 ;
    B ( ) ;
    q ( & ql ) ;
    qg [ 0 ] = ql . h ;
    qh = 1 ;
    for ( ;
    V < 2 ;
    V ++ ) {
        qr [ V ] . id = V ;
        if ( pthread_create ( a + V , NULL , A , qr + V ) ) {
            d = 2 ;
            goto shutdown ;
        }
    }
    j ( ) ;
    while ( fgets ( R , sizeof R , stdin ) ) {
        if ( ! strchr ( R , '\n' ) ) {
            int n = getchar ( ) ;
            if ( n != EOF && n != '\n' ) {
                do {
                    n = getchar ( ) ;
                }
                while ( n != EOF && n != '\n' ) ;
                continue ;
            }
        }
        char * g = strtok ( R , " \t\r\n" ) ;
        if ( ! g ) continue ;
        if ( ! strcmp ( g , "uci" ) ) {
            puts ( "uciok" ) ;
            fflush ( stdout ) ;
        }
        else if ( ! strcmp ( g , "isready" ) ) {
            puts ( "readyok" ) ;
            fflush ( stdout ) ;
        }
        else if ( ! strcmp ( g , "quit" ) ) break ;
        else if ( ! strcmp ( g , "position" ) ) {
            j ( ) ;
            z ( ) ;
        }
        else if ( ! strcmp ( g , "go" ) ) w ( ) ;
    }
    j ( ) ;
    shutdown : pthread_mutex_lock ( & qj ) ;
    qm = 1 ;
    pthread_cond_broadcast ( & qb ) ;
    pthread_mutex_unlock ( & qj ) ;
    for ( int i = 0 ;
    i < V ;
    i ++ ) if ( pthread_join ( a [ i ] , NULL ) ) d = 2 ;
    free ( qq ) ;
    return d ;
}''', 5172, '05d80e2dbbaf858be18910a24c78b49f093b0721057fc8caac1248f7d078f161'),
    'selected-common-C-gap-4-0-after': ('literal', '\n', 1, '01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b'),
}

_OLD_LAYOUT = [('canonical', 'previous-C-gap-1-0'), ('canonical', 'previous-C-gap-1-directive-1'), ('canonical', 'previous-C-gap-1-directive-3'), ('canonical', 'previous-C-gap-1-directive-5'), ('canonical', 'previous-C-gap-1-directive-7'), ('canonical', 'previous-C-gap-1-directive-9'), ('canonical', 'previous-C-gap-1-directive-11'), ('canonical', 'previous-C-gap-1-directive-13'), ('canonical', 'previous-C-gap-1-directive-15'), ('canonical', 'previous-C-gap-1-16'), ('canonical', 'previous-C-gap-1-directive-17'), ('canonical', 'previous-C-gap-1-18-before'), ('canonical', 'previous-C-gap-1-18'), ('canonical', 'previous-C-gap-1-18-after'), ('canonical', 'previous-C-gap-1-directive-19'), ('canonical', 'previous-C-gap-1-directive-21'), ('canonical', 'previous-C-gap-1-directive-23'), ('canonical', 'previous-C-gap-1-directive-25'), ('canonical', 'previous-C-gap-1-26'), ('model', 'weights-HCE'), ('model', 'sidehash-setter'), ('canonical', 'previous-C-gap-3-0'), ('canonical', 'previous-C-gap-3-0-after'), ('model', 'SIMD128'), ('canonical', 'previous-C-gap-4-0'), ('canonical', 'previous-C-gap-4-0-after')]
_NEW_LAYOUT = [('canonical', 'selected-common-C-gap-1-0'), ('canonical', 'selected-common-C-gap-1-directive-1'), ('canonical', 'selected-common-C-gap-1-directive-3'), ('canonical', 'selected-common-C-gap-1-directive-5'), ('canonical', 'selected-common-C-gap-1-directive-7'), ('canonical', 'selected-common-C-gap-1-directive-9'), ('canonical', 'selected-common-C-gap-1-directive-11'), ('canonical', 'selected-common-C-gap-1-directive-13'), ('canonical', 'selected-common-C-gap-1-directive-15'), ('canonical', 'selected-common-C-gap-1-directive-17'), ('canonical', 'selected-common-C-gap-1-18'), ('canonical', 'selected-common-C-gap-1-directive-19'), ('canonical', 'selected-common-C-gap-1-20'), ('canonical', 'selected-common-C-gap-1-directive-21'), ('canonical', 'selected-common-C-gap-1-directive-23'), ('canonical', 'selected-common-C-gap-1-directive-25'), ('canonical', 'selected-common-C-gap-1-26'), ('canonical', 'selected-common-C-gap-1-26-after'), ('canonical', 'selected-common-C-gap-1-directive-27'), ('canonical', 'selected-common-C-gap-1-directive-29'), ('canonical', 'selected-common-C-gap-1-directive-31'), ('canonical', 'selected-common-C-gap-1-directive-33'), ('canonical', 'selected-common-C-gap-1-34'), ('model', 'weights-HCE'), ('model', 'sidehash-setter'), ('canonical', 'selected-common-C-gap-3-0'), ('canonical', 'selected-common-C-gap-3-0-after'), ('model', 'SIMD128'), ('canonical', 'selected-common-C-gap-4-0'), ('canonical', 'selected-common-C-gap-4-0-after')]

METADATA = {
    'stage': 'late-C-common-core-signed-net-SIMD128',
    'input_bytes': INPUT_PIN[0], 'input_sha256': INPUT_PIN[1],
    'output_bytes': OUTPUT_PIN[0], 'output_sha256': OUTPUT_PIN[1],
    'physical_int16_lanes': 8, 'SIMD_load_bits': 128,
    'fixed_workers': 2, 'fixed_TT_bits': 18, 'target_ISA': '-mavx2',
    'actual_C_model_and_phase_body_bound': True,
    'source_inverse': True, 'canonical_DEV_earlier_guards_unchanged': True,
    'compiler_policy': 'selected common A implicit GNU17/Os/strip plus fixed C -mavx2',
    'old_C_trace_equivalence_claimed': False,
    'EP_scratch': 'attack-only mailbox scratch deliberately has stale lanes',
    'runtime_strength_performance_claimed': False,
}

def _pin(data):
    return len(data),hashlib.sha256(data).hexdigest()

def _need(value,message):
    if not value:raise ValueError('C common composition: '+message)

def _guard(data,pin,label):
    _need(type(data) is bytes and _pin(data)==pin,label+' fixed bytes')

def _partition(data,gaps):
    for at,size,digest in gaps:
        _need(_pin(data[at:at+size])==(size,digest),'protected nonmodel gap')

def _extract(data,models):
    result={}
    for name,(at,size,digest) in models.items():
        body=data[at:at+size]
        _guard(body,(size,digest),name+' actual body')
        result[name]=body
    return result

def _bind(models,reverse=False):
    result={}
    for name,body in models.items():
        rows=list(reversed(_BINDINGS[name])) if reverse else _BINDINGS[name]
        for old,new,count in rows:
            before,after=(new,old) if reverse else (old,new)
            _need(body.count(before)==count,name+' fixed role ownership')
            body=body.replace(before,after)
        expected=(_INPUT_MODELS if reverse else _OUTPUT_MODELS)[name]
        _guard(body,expected[1:],name+' bound body')
        result[name]=body
    return result

def _assemble(layout,models,compact):
    _need(callable(compact),'existing pinned compact_source callback')
    parts=[]
    for kind,name in layout:
        if kind=='model':parts.append(models[name]);continue
        presentation,readable,size,digest=_CANONICAL[name]
        if presentation=='literal':body=readable.encode('ascii')
        else:
            packed=compact(readable.encode('ascii'),'c')
            _need(type(packed) is bytes and packed.endswith(b'\n'),name+' compactor result')
            body=packed[:-1]
        _guard(body,(size,digest),name+' canonical tokens')
        parts.append(body)
    return b''.join(parts)

def _forward(source,compact):
    _guard(source,INPUT_PIN,'previous C chain')
    _partition(source,_INPUT_GAPS)
    result=_assemble(_NEW_LAYOUT,_bind(_extract(source,_INPUT_MODELS)),compact)
    _guard(result,OUTPUT_PIN,'selected C source')
    _partition(result,_OUTPUT_GAPS)
    return result

def restore_source(source,*,compact):
    """Regenerate old C using the actual selected model and original C regions."""
    _guard(source,OUTPUT_PIN,'selected C inverse input')
    _partition(source,_OUTPUT_GAPS)
    result=_assemble(_OLD_LAYOUT,_bind(_extract(source,_OUTPUT_MODELS),True),compact)
    _guard(result,INPUT_PIN,'previous C inverse output')
    _partition(result,_INPUT_GAPS)
    _need(_forward(result,compact)==source,'source inverse roundtrip')
    return result

def transform_source(source,*,compact):
    result=_forward(source,compact)
    _need(restore_source(result,compact=compact)==source,'whole previous source inverse')
    return result,dict(METADATA)

_BOOT_INPUT_PIN = (10566, 'b0b1fffcbbef0d38b8d96c8fe7ec639a231f4738afed8a1929b4026bc3906391')
_BOOT_OUTPUT_PIN = (10054, '14405494f35ef3fcc40646d487adf57b35de10b0ef9e0182b5333e9be9be2d68')
_BOOT_COMPILER_BEFORE = b"['cc', '-std=c11', '-Os', '-pthread', '-DWORKERS=2', '-DTT_BITS=18', '-mavx2', '-DDEV=0', '-x', 'c', '-', '-o', 'x']"
_BOOT_COMPILER_AFTER = b"'cc -Os -mavx2 -x c - -o x -s'.split()"
BOOTSTRAP_METADATA = {
    'input_bytes': _BOOT_INPUT_PIN[0], 'input_sha256': _BOOT_INPUT_PIN[1],
    'output_bytes': _BOOT_OUTPUT_PIN[0], 'output_sha256': _BOOT_OUTPUT_PIN[1],
    'actual_previous_literal_and_template_consumed': True,
    'selected_literal': 'triple-double raw bytes after actual common validation',
    'owned_regions': 2, 'protected_gaps': 3, 'full_inverse': True,
    'compiler_policy': 'selected common A flags plus C -mavx2; old DEV/preprocessor unchanged',
}

def transform_bootstrap(previous, *, before, source, old_expression, expression, compact):
    """Consume the actual old C package script, then replace compiler/literal."""
    _guard(previous, _BOOT_INPUT_PIN, 'actual previous C bootstrap')
    _guard(before, INPUT_PIN, 'actual restored C source')
    _guard(source, OUTPUT_PIN, 'selected C source')
    _need(restore_source(source,compact=compact)==before, 'literal source inverse consumed')
    _need(type(old_expression) is str and type(expression) is str, 'actual literal expressions required')
    _need(ast.literal_eval(old_expression)==before and ast.literal_eval(expression)==source,
          'actual old/new literals restore complete source')
    # The selected A envelope uses triple-double raw bytes. The previous
    # common literal is still actually consumed and validated above.
    quote=chr(34)*3
    _need(source.isascii() and quote.encode() not in source and b'\r' not in source,
          'selected raw triple-double source domain')
    selected_expression='br'+quote+source.decode('ascii')+quote
    _need(ast.literal_eval(selected_expression)==source, 'selected raw bytes literal inverse')
    rows = [
        (_BOOT_COMPILER_BEFORE, _BOOT_COMPILER_AFTER),
        (old_expression.encode('ascii'), selected_expression.encode('ascii')),
    ]
    edits=[]
    for old,new in rows:
        _need(previous.count(old)==1, 'fixed previous bootstrap region')
        edits.append((previous.index(old),old,new))
    edits.sort()
    parts=[];inverse=[];gaps=[];cursor=output_cursor=0
    for at,old,new in edits:
        _need(at>=cursor, 'nonoverlapping bootstrap regions')
        gap=previous[cursor:at];parts.extend((gap,new))
        gaps.append((cursor,at,output_cursor,output_cursor+len(gap)))
        output_cursor+=len(gap);inverse.append((output_cursor,old,new))
        output_cursor+=len(new);cursor=at+len(old)
    parts.append(previous[cursor:]);result=b''.join(parts)
    gaps.append((cursor,len(previous),output_cursor,len(result)))
    for lo,hi,out_lo,out_hi in gaps:
        _need(previous[lo:hi]==result[out_lo:out_hi], 'protected bootstrap gap')
    restored=result
    for at,old,new in reversed(inverse):
        _need(restored[at:at+len(new)]==new, 'bootstrap inverse fixed region')
        restored=restored[:at]+old+restored[at+len(new):]
    _need(restored==previous, 'actual previous bootstrap full inverse')
    _guard(result,_BOOT_OUTPUT_PIN,'selected bootstrap')
    calls=[node for node in ast.walk(ast.parse(result))
           if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
           and node.func.attr=='communicate']
    _need(len(calls)==1 and len(calls[0].args)==1
          and ast.literal_eval(calls[0].args[0])==source, 'selected literal C stdin')
    return result,dict(BOOTSTRAP_METADATA)
