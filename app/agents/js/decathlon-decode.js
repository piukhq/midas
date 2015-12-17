//https://github.com/doloopwhile/PyExecJS
//https://github.com/PiotrDabkowski/Js2Py

Nlf = {
    115: 1
}
var uOf = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
var L6e;
var qrb = {};
jnf = '';
Vrf = 'number';
HOf = 'java.lang.'
JOf = '[Ljava.lang.';
mE = {e: "char", c: 1};
lE = v8e('byte', ' B')
Anb = t8e(HOf, 'Character', 3042)
apb = s8e(jnf, '[C', 3139, mE);
Nnb = t8e(HOf, 'Object', 1)
oqb = s8e(JOf, 'Object;', 3133, Nnb)
Inb = t8e(HOf, 'Integer', 3049)
mqb = s8e(JOf, 'Integer;', 3143, Inb)
lqb = s8e(JOf, 'Character;', 3141, Anb)
unf = ' ';

function Jlf() {};
function SD() {};
function fk() {};
function r8e() {};
function v8e(a, b) {
    var c;
    c = new r8e;
    c.e = jnf + a;
    x8e(b) && y8e(b, c);
    c.c = 1;
    return c
}
function w8e(a) {
    var b = qrb[a.d];
    a = null ;
    return b
}
function y8e(a, b) {
    var c;
    b.d = a;
    if (a == 2) {
        c = String.prototype
    } else {
        if (a > 0) {
            var d = w8e(b);
            if (d) {
                c = d.prototype
            } else {
                d = qrb[a] = function() {}
                ;
                d.cZ = b;
                return
            }
        } else {
            return
        }
    }
    c.cZ = b
}
function t8e(a, b, c) {
    var d;
    d = new r8e;
    d.e = a + b;
    x8e(c) && y8e(c, d);
    return d
}
function x8e(a) {
    return typeof a == Vrf && a > 0
}
_ob = s8e(jnf, '[B', 3145, lE)
function h9e() {
    h9e = Jlf;
    g9e = XD(mqb, Nlf, 127, 256, 0)
    //g9e = XD(1, Nlf, 127, 256, 0)
}
function X8e(a) {
    this.b = a
}

function f9e(a) {
    var b, c;
    if (a > -129 && a < 128) {
        b = a + 128;
        c = (h9e(),
        g9e)[b];
        !c && (c = g9e[b] = new X8e(a));
        return c
    }
    return new X8e(a)
}
function s8e(a, b, c, d) {
    var e;
    e = new r8e;
    e.e = a + b;
    x8e(c != 0 ? -c : 0) && y8e(c != 0 ? -c : 0, e);
    e.c = 4;
    e.b = d;
    return e
}
function p8e() {
    p8e = Jlf;
    o8e = XD(lqb, Nlf, 119, 128, 0);
}
///////////
////
function YD(a, b, c, d) {
    aE();
    cE(d, $D, _D);
    d.cZ = a;
    d.cM = b;
    d.qI = c;
    return d
}
function WD(a, b) {
    var c = new Array(b);
    if (a == 3) {
        for (var d = 0; d < b; ++d) {
            var e = new Object;
            e.l = e.m = e.h = 0;
            c[d] = e
        }
    } else if (a > 0) {
        var e = [null , 0, false][a];
        for (var d = 0; d < b; ++d) {
            c[d] = e
        }
    }
    return c
}
function XD(a, b, c, d, e) {
    var f;
    f = WD(e, d);
    YD(a, b, c, f);
    return f
}

// function XD(a, b, c, d, e){
//     var data = [];
//     var length = e; // user defined length

//     for(var i = 0; i < length; i++) {
//         data.push(0);
//     }
//     return data;
// }
function N6e() {
    N6e = Jlf;
    var a, b;
    L6e = XD(apb, Nlf, -1, 64, 1);
    //L6e = XD(1, Nlf, -1, 64, 1);
    b = 0;
    for (a = 65; a <= 90; ++a) {
        L6e[b++] = a
    }
    for (a = 97; a <= 122; ++a) {
        L6e[b++] = a
    }
    for (a = 48; a <= 57; ++a) {
        L6e[b++] = a
    }
    L6e[b++] = 43;
    L6e[b++] = 47;
    M6e = XD(_ob, Nlf, -1, 128, 1);
    //M6e = XD(1, Nlf, -1, 128, 1);
    for (b = 0; b < M6e.length; ++b) {
        M6e[b] = -1
    }
    for (b = 0; b < 64; ++b) {
        M6e[L6e[b]] = ~~(b << 24) >> 24
    }
}

function O6e(a) {
    var b, c, d, e, f, g, i, j;
    g = gaf(a);
    b = XD(_ob, Nlf, -1, g.length * 2, 1);
    //b = XD(1, Nlf, -1, g.length * 2, 1)
    i = 0;
    for (e = 0,
    f = g.length; e < f; ++e) {
        d = g[e];
        if (d < 128) {
            b[i] = ~~(d << 24) >> 24;
            ++i
        } else {
            b[i] = -61;
            ++i;
            b[i] = ~~(d - 320 << 24) >> 24;
            ++i
        }
    }
    c = XD(_ob, Nlf, -1, i, 1);
    //c = XD(1, Nlf, -1, i, 1);
    for (j = 0; j < i; ++j) {
        c[j] = b[j]
    }
    return c
}

function vaf(a) {
    return String.fromCharCode.apply(null , a)
}
function V9e(a, b, c, d) {
    var e;
    for (e = 0; e < b; ++e) {
        c[d++] = a.charCodeAt(e)
    }
}

function gaf(a) {
    var b, c;
    c = a.length;
    b = XD(apb, Nlf, -1, c, 1);
    V9e(a, c, b, 0);
    return b
}

function XD(a, b, c, d, e) {
    var f;
    f = WD(e, d);
    YD(a, b, c, f);
    return f
}

function WD(a, b) {
    var c = new Array(b);
    if (a == 3) {
        for (var d = 0; d < b; ++d) {
            var e = new Object;
            e.l = e.m = e.h = 0;
            c[d] = e
        }
    } else if (a > 0) {
        var e = [null , 0, false][a];
        for (var d = 0; d < b; ++d) {
            c[d] = e
        }
    }
    return c
}
function YD(a, b, c, d) {
    aE();
    cE(d, $D, _D);
    d.cZ = a;
    d.cM = b;
    d.qI = c;
    return d
}

function cE(a, b, c) {
    aE();
    for (var d = 0, e = b.length; d < e; ++d) {
        a[b[d]] = c[d]
    }
}

function P6e(a, b) {
    var c, d, e, f, g, i, j, k, n, o, p, q;
    n = ~~((b * 4 + 2) / 3);
    o = ~~((b + 2) / 3) * 4;
    q = XD(apb, Nlf, -1, o, 1);
    f = 0;
    p = 0;
    while (f < b) {
        c = a[f++] & 255;
        d = f < b ? a[f++] & 255 : 0;
        e = f < b ? a[f++] & 255 : 0;
        g = ~~c >>> 2;
        i = (c & 3) << 4 | ~~d >>> 4;
        j = (d & 15) << 2 | ~~e >>> 6;
        k = e & 63;
        q[p++] = L6e[g];
        q[p++] = L6e[i];
        q[p] = p < n ? L6e[j] : 61;
        ++p;
        q[p] = p < n ? L6e[k] : 61;
        ++p
    }
    return q
}

function Q6e(a) {
    N6e();
    var b;
    b = O6e(a);
    return vaf(P6e(b, b.length))
}
function aE() {
    aE = Jlf;
    $D = [];
    _D = [];
    bE(new SD, $D, _D)
}
function bE(a, b, c) {
    var d = 0, e;
    for (var f in a) {
        if (e = a[f]) {
            b[d] = f;
            c[d] = e;
            ++d
        }
    }
}
function Vff(a) {
    a.b = XD(oqb, Nlf, 0, 0, 0);
    a.c = 0;
    //a.b = XD(1, Nlf, 0, 0, 0)
}
function ggf() {
    Vff(this)
}
function dE(a, b) {
    return a.cM && !!a.cM[b]
}
function iE(a) {
    return a.tM == Jlf || dE(a, 1)
}
function Cb(a, b) {
    var c;
    return c = a,
    iE(c) ? c.eQ(b) : c === b
}

function olf(a, b) {
    return jE(a) === jE(b) || a != null  && Cb(a, b)
}
function jE(a) {
    return a == null  ? null  : a
}
function b8e(a) {
    this.b = a
}
function _ff(a, b, c) {
    for (; c < a.c; ++c) {
        if (olf(b, a.b[c])) {
            return c
        }
    }
    return -1
}
function p8e() {
    p8e = Jlf;
    o8e = XD(lqb, Nlf, 119, 128, 0)
    //o8e = XD(1, Nlf, 119, 128, 0)
}
function n8e(a) {
    var b;
    if (a < 128) {
        b = (p8e(),
        o8e)[a];
        !b && (b = o8e[a] = new b8e(a));
        return b
    }
    return new b8e(a)
}
function ZD(a, b, c) {
    if (c != null ) {
        if (a.qI > 0 && !eE(c, a.qI)) {
            throw new y7e
        } else if (a.qI == -1 && (c.tM == Jlf || dE(c, 1))) {
            throw new y7e
        } else if (a.qI < -1 && !(c.tM != Jlf && !dE(c, 1)) && !eE(c, -a.qI)) {
            throw new y7e
        }
    }
    return a[b] = c
}
function Xff(a, b) {
    ZD(a.b, a.c++, b);
    return true
}
function iaf(c) {
    if (c.length == 0 || c[0] > unf && c[c.length - 1] > unf) {
        return c
    }
    var a = c.replace(/^(\s*)/, jnf);
    var b = a.replace(/\s*$/, jnf);
    return b
}
function Qaf(a) {
    a.b = new fk
}
function abf() {
    Qaf(this)
}
// diff in here
function R6e(a) {
    var b, c, d, e, f, g, i;
    g = gaf(a);
    i = 0;
    e = XD(apb, Nlf, -1, g.length, 1);
    f = new ggf;
    for (c = 0,
    d = g.length; c < d; ++c) {
        b = g[c];
        if (_ff(f, n8e(b), 0) == -1) {
            e[i] = b;
            ++i;
            Xff(f, n8e(b))
        }
    }
    return iaf(vaf(e))
}
function W9e(b, a) {
    return b.indexOf(a)
}
function uaf(a) {
    return String.fromCharCode(a)
}
function dk(a, b) {
    a.b += b
}
function Raf(a, b) {
    dk(a.b, String.fromCharCode(b));
    return a
}
function R9e(b, a) {
    return b.charCodeAt(a)
}
function T6e(a, b) {
    var c, d, e, f;
    f = new abf;
    for (d = 0; d < b.length; ++d) {
        c = n8e(b.charCodeAt(d));
        e = f9e(W9e(uOf, uaf(c.b)));
        e.b == -1 || a.length < e.b ? Vaf(f, uaf(c.b)) : Raf(f, R9e(a, e.b))
    }
    return f.b.b
}
function U6e(a) {
    var b, c, d;
    c = Q6e('cacher email');
    d = Q6e(a);
    b = R6e(c + uOf);
    return T6e(b, d)
}

function X6e(a, b) {
    var c, d, e;
    d = Q6e(a != null  ? a.toLowerCase() : null );
    e = Q6e(b);
    c = R6e(d + uOf);
    return T6e(c, e)
}
function hash_credentials(email, password) {
    return {
        'mdp': X6e(email, password).substring(9),
        'email': U6e(email).substring(9)
    }
}