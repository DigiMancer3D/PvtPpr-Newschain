import lzma
import base64
import jinja2
import re
import os
from pathlib import Path
from urllib.parse import quote
import gzip
import io
import requests
import execjs
import logging
import time

# Clear and initialize logging
log_file = 'decode_errors.log'
if os.path.exists(log_file):
    os.remove(log_file)
logging.basicConfig(filename=log_file, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
startup_time = int(time.time())
logging.info(f"{startup_time} [start up stamp]")
logging.getLogger().handlers[0].flush()  # Force flush to ensure stamp is written

# Setup Jinja2 environment
template_env = jinja2.Environment(loader=jinja2.FileSystemLoader("."))

# Base input class with sanitization
class PvtPprInput:
    def __init__(self, placeholder, allow_html=False, allow_links=False):
        self.value = ""
        self.placeholder = placeholder
        self.allow_html = allow_html
        self.allow_links = allow_links

    def sanitize(self):
        if not self.allow_html and "<" in self.value:
            self.value = re.sub(r"<[^>]+>", "", self.value)  # Strip HTML
        if not self.allow_links and any(self.value.startswith(x) for x in ["http", "ipfs", "magnet", "base64"]):
            self.value = ""  # Clear invalid links
        return self.value

    def validate(self):
        self.sanitize()
        if self.value and self.allow_links:
            link_pattern = r"^(https?://.*|ipfs://.*|ipns://.*|magnet:.*|[A-Za-z0-9+/=]{44,})$"
            if not re.match(link_pattern, self.value):
                raise ValueError("Invalid link format.")
        return True

    def render(self):
        return self.value

class TitleTextInput(PvtPprInput):
    def __init__(self):
        super().__init__(placeholder="Title Goes Here", allow_html=True)

    def render(self):
        return f"<h1>{self.sanitize()}</h1>" if self.value else f"<h1>{self.placeholder}</h1>"

class BodyTextField(PvtPprInput):
    def __init__(self):
        super().__init__(placeholder="Write Here. HTML & JS is allowed.", allow_html=True)

    def count_stats(self):
        text = re.sub(r"<[^>]+>", "", self.sanitize())
        chars = len(text)
        words = len(text.split())
        reading_time = round(chars / 200)
        return {"chars": chars, "words": words, "reading_time": reading_time}

    def render(self):
        stats = self.count_stats()
        return f"""
        <div>{self.sanitize()}</div>
        <div>Chars: {stats['chars']} | Words: {stats['words']} | Reading Time: {stats['reading_time']} min</div>
        """

class LinkInput(PvtPprInput):
    def __init__(self):
        super().__init__(placeholder="Image Link Here", allow_links=True)

    def render(self):
        if self.validate() and self.value:
            return f'<img src="{self.sanitize()}" alt="Embedded Link" />'
        return ""

# Template for basic PvtPpr
pvtppr_template = template_env.from_string("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="btc_snapshot" content="{{ btc_snapshot }}">
    <title>{{ title }}</title>
</head>
<body>
    {{ title_html }}
    {{ body_html }}
    {{ link_html }}
</body>
</html>
""")

def generate_hashlink(title_input: TitleTextInput, body_input: BodyTextField, link_input: LinkInput, btc_snapshot=""):
    title_input.validate()
    body_input.validate()
    link_input.validate()

    title_html = title_input.render()
    body_html = body_input.render()
    link_html = link_input.render()

    html_content = pvtppr_template.render(
        title=title_input.value,
        title_html=title_html,
        body_html=body_html,
        link_html=link_html,
        btc_snapshot=btc_snapshot
    )

    compressed = lzma.compress(html_content.encode(), format=lzma.FORMAT_ALONE, preset=9)
    b64_encoded = base64.b64encode(compressed).decode()
    title_encoded = quote(title_input.value or title_input.placeholder, safe='')
    return f"https://itty.bitty.site/#{title_encoded}/?{b64_encoded}"

# Simplified JS LZMA worker focusing on decompression
JS_LZMA_WORKER = """
var global = global || this;
var navigator = { userAgent: 'node' };
var location = { hash: '' };
function atob(base64) { return Buffer.from(base64, 'base64').toString('binary'); }
var e = function(){"use strict";function r(e,r){postMessage({action:nr,cbn:r,result:e})}function o(e){var r=[];return r[e-1]=void 0,r} function n(e,r){return i(e[0]+r[0],e[1]+r[1])}function t(e,r){var o,n;return e[0]==r[0]&&e[1]==r[1]?0:(o=0>e[1],n=0>r[1],o&&!n?-1:!o&&n?1:d(e,r)[1]<0?-1:1)} function i(e,r){var o,n;for(r%=0x10000000000000000,e%=0x10000000000000000,o=r%ir,n=Math.floor(e/ir)*ir,r=r-o+n,e=e-n+o;0>e;)e+=ir,r-=ir;for(;e>4294967295;)e-=ir,r+=ir;for(r%=0x10000000000000000;r>0x7fffffff00000000;)r-=0x10000000000000000;for(;-0x8000000000000000>r;)r+=0x10000000000000000;return[e,r]}function u(e){return e>=0?[e,0]:[e+ir,-ir]} function s(e){return e[0]>=2147483648?~~Math.max(Math.min(e[0]-ir,2147483647),-2147483648):~~Math.max(Math.min(e[0],2147483647),-2147483648)} function d(e,r){return i(e[0]-r[0],e[1]-r[1])}function c(e,r){return e.ab=r,e.cb=0,e.O=r.length,e} function m(e){return e.cb>=e.O?-1:255&e.ab[e.cb++]}function a(e){return e.ab=o(32),e.O=0,e} function _(e){var r=e.ab;return r.length=e.O,r} function f(e,r,o,n){p(r,o,e.ab,e.O,n),e.O+=n} function p(e,r,o,n,t){for(var i=0;t>i;++i)o[n+i]=e[r+i]}function D(e,r,o){var n,t,i,s,d="",c=[];for(t=0;5>t;++t){if(i=m(r),-1==i)throw Error("truncated input");c[t]=i<<24>>24} if(n=N({}),!z(n,c))throw Error("corrupted input");for(t=0;64>t;t+=8){if(i=m(r),-1==i)throw Error("truncated input");i=i.toString(16),1==i.length&&(i="0"+i),d=i+""+d}/^0+$|^f+$/i.test(d)?e.N=ur:(s=parseInt(d,16),e.N=s>4294967295?ur:u(s)),e.Q=B(n,r,o,e.N)}function l(e,r){return e.S=a({}),D(e,c({},r),e.S),e} function g(e,r,o){var n=e.D-r-1;for(0>n&&(n+=e.c);0!=o;--o)n>=e.c&&(n=0),e.x[e.D++]=e.x[n++],e.D>=e.c&&w(e)}function v(e,r){(null==e.x||e.c!=r)&&(e.x=o(r)),e.c=r,e.D=0,e.w=0} function w(e){var r=e.D-e.w;r&&(f(e.V,e.x,e.w,r),e.D>=e.c&&(e.D=0),e.w=e.D)}function R(e,r){var o=e.D-r-1;return 0>o&&(o+=e.c),e.x[o]} function h(e,r){e.x[e.D++]=r,e.D>=e.c&&w(e)}function P(e){w(e),e.V=null} function C(e){return e-=2,4>e?e:3} function S(e){return 4>e?0:10>e?e-3:e-6} function M(e,r){return e.h=r,e.bb=null,e.X=1,e} function L(e){if(!e.X)throw Error("bad state");if(e.bb)throw Error("No encoding");return y(e),e.X} function y(e){var r=I(e.h);if(-1==r)throw Error("corrupted input");e.$=ur,e.Z=e.h.d,(r||t(e.h.U,sr)>=0&&t(e.h.d,e.h.U)>=0)&&(w(e.h.b),P(e.h.b),e.h.a.K=null,e.X=0)}function B(e,r,o,n){return e.a.K=r,P(e.b),e.b.V=o,b(e),e.f=0,e.l=0,e.T=0,e.R=0,e._=0,e.U=n,e.d=sr,e.I=0,M({},e)}function I(e){var r,o,i,d,c,m;if(m=s(e.d)&e.P,Q(e.a,e.q,(e.f<<4)+m)){if(Q(e.a,e.E,e.f))i=0,Q(e.a,e.s,e.f)?(Q(e.a,e.u,e.f)?(Q(e.a,e.r,e.f)?(o=e._,e._=e.R):o=e.R,e.R=e.T):o=e.T,e.T=e.l,e.l=o):Q(e.a,e.n,(e.f<<4)+m)||(e.f=7>e.f?9:11,i=1),i||(i=x(e.o,e.a,m)+2,e.f=7>e.f?8:11);else if(e._=e.R,e.R=e.T,e.T=e.l,i=2+x(e.C,e.a,m),e.f=7>e.f?7:10,c=q(e.j[C(i)],e.a),c>=4){if(d=(c>>1)-1,e.l=(2|1&c)<<d,14>c)e.l+=J(e.J,e.l-c-1,e.a,d);else if(e.l+=U(e.a,d-4)<<4,e.l+=F(e.t,e.a),0>e.l)return-1==e.l?1:-1}else e.l=c;if(t(u(e.l),e.d)>=0||e.l>=e.m)return-1;g(e.b,e.l,i),e.d=n(e.d,u(i)),e.I=R(e.b,0)}else r=Z(e.k,s(e.d),e.I),e.I=7>e.f?T(r,e.a):$(r,e.a,R(e.b,e.l)),h(e.b,e.I),e.f=S(e.f),e.d=n(e.d,dr);return 0} function N(e){e.b={},e.a={},e.q=o(192),e.E=o(12),e.s=o(12),e.u=o(12),e.r=o(12),e.n=o(192),e.j=o(4),e.J=o(114),e.t=K({},4),e.C=G({}),e.o=G({}),e.k={};for(var r=0;4>r;++r)e.j[r]=K({},6);return e} function b(e){e.b.w=0,e.b.D=0,X(e.q),X(e.n),X(e.E),X(e.s),X(e.u),X(e.r),X(e.J),H(e.k);for(var r=0;4>r;++r)X(e.j[r].B);A(e.C),A(e.o),X(e.t.B),V(e.a)} function z(e,r){var o,n,t,i,u,s,d;if(5>r.length)return 0;for(d=255&r[0],t=d%9,s=~~(d/9),i=s%5,u=~~(s/5),o=0,n=0;4>n;++n)o+=(255&r[1+n])<<8*n;return o>99999999||!W(e,t,i,u)?0:O(e,o)}function O(e,r){return 0>r?0:(e.z!=r&&(e.z=r,e.m=Math.max(e.z,1),v(e.b,Math.max(e.m,4096))),1)}function W(e,r,o,n){if(r>8||o>4||n>4)return 0;E(e.k,o,r);var t=1<<n;return k(e.C,t),k(e.o,t),e.P=t-1,1} function k(e,r){for(;r>e.e;++e.e)e.G[e.e]=K({},3),e.H[e.e]=K({},3)} function x(e,r,o){if(!Q(r,e.M,0))return q(e.G[o],r);var n=8;return n+=Q(r,e.M,1)?8+q(e.L,r):q(e.H[o],r)} function G(e){return e.M=o(2),e.G=o(16),e.H=o(16),e.L=K({},8),e.e=0,e} function A(e){X(e.M);for(var r=0;e.e>r;++r)X(e.G[r].B),X(e.H[r].B);X(e.L.B)} function E(e,r,n){var t,i;if(null==e.F||e.g!=n||e.y!=r)for(e.y=r,e.Y=(1<<r)-1,e.g=n,i=1<<e.g+e.y,e.F=o(i),t=0;i>t;++t)e.F[t]=j({})} function Z(e,r,o){return e.F[((r&e.Y)<<e.g)+((255&o)>>>8-e.g)]} function H(e){var r,o;for(o=1<<e.g+e.y,r=0;o>r;++r)X(e.F[r].v)} function T(e,r){var o=1;do o=o<<1|Q(r,e.v,o);while(256>o);return o<<24>>24} function $(e,r,o){var n,t,i=1;do if(t=o>>7&1,o<<=1,n=Q(r,e.v,(1+t<<8)+i),i=i<<1|n,t!=n){for(;256>i;)i=i<<1|Q(r,e.v,i);break}while(256>i);return i<<24>>24} function j(e){return e.v=o(768),e} function K(e,r){return e.A=r,e.B=o(1<<r),e} function q(e,r){var o,n=1;for(o=e.A;0!=o;--o)n=(n<<1)+Q(r,e.B,n);return n-(1<<e.A)} function F(e,r){var o,n,t=1,i=0;for(n=0;e.A>n;++n)o=Q(r,e.B,t),t<<=1,t+=o,i|=o<<n;return i} function J(e,r,o,n){var t,i,u=1,s=0;for(i=0;n>i;++i)t=Q(o,e,r+u),u<<=1,u+=t,s|=t<<i;return s} function Q(e,r,o){var n,t=r[o];return n=(e.i>>>11)*t,(-2147483648^n)>(-2147483648^e.p)?(e.i=n,r[o]=t+(2048-t>>>5)<<16>>16,-16777216&e.i||(e.p=e.p<<8|m(e.K),e.i<<=8),0):(e.i-=n,e.p-=n,r[o]=t-(t>>>5)<<16>>16,-16777216&e.i||(e.p=e.p<<8|m(e.K),e.i<<=8),1)} function U(e,r){var o,n,t=0;for(o=r;0!=o;--o)e.i>>=1,n=e.p-e.i>>>31,e.p-=e.i&n-1,t=t<<1|1-n,-16777216&e.i||(e.p=e.p<<8|m(e.K),e.i<<=8);return t} function V(e){e.p=0,e.i=-1;for(var r=0;5>r;++r)e.p=e.p<<8|m(e.K)} function X(e){for(var r=e.length-1;r>=0;--r)e[r]=1024} function Y(e){for(var r,o,n,t=0,i=0,u=e.length,s=[],d=[];u>t;++t,++i){if(r=255&e[t],128&r)if(192==(224&r)){if(t+1>=u)return e;if(o=255&e[++t],128!=(192&o))return e;d[i]=(31&r)<<6|63&o}else{if(224!=(240&r))return e;if(t+2>=u)return e;if(o=255&e[++t],128!=(192&o))return e;if(n=255&e[++t],128!=(192&n))return e;d[i]=(15&r)<<12|(63&o)<<6|63&n}else{if(!r)return e;d[i]=r}16383==i&&(s.push(String.fromCharCode.apply(String,d)),i=-1)}return i>0&&(d.length=i,s.push(String.fromCharCode.apply(String,d))),s.join("")}function er(e){return e[1]+e[0]}function rr(e,o,n){function t(){try{for(var e,r=0,u=(new Date).getTime();L(c.d.Q);)if(++r%1e3==0&&(new Date).getTime()-u>200)return s&&(i=er(c.d.Q.h.d)/d,n(i)),tr(t,0),0;n(1),e=Y(_(c.d.S)),tr(o.bind(null,e),0)}catch(m){o(null,m)}}var i,u,s,d,c={},m=void 0===o&&void 0===n;if("function"!=typeof o&&(u=o,o=n=0),n=n||function(e){return void 0!==u?r(s?e:-1,u):void 0},o=o||function(e,r){return void 0!==u?postMessage({action:or,cbn:u,result:e,error:r}):void 0},m){for(c.d=l({},e);L(c.d.Q););return Y(_(c.d.S))}try{c.d=l({},e),d=er(c.d.N),s=d>-1,n(0)}catch(a){return o(null,a)}tr(t,0)}var or=2,nr=3,tr="function"==typeof setImmediate?setImmediate:setTimeout,ir=4294967296,ur=[4294967295,-ir],sr=[0,0],dr=[1,0];return"undefined"==typeof onmessage||"undefined"!=typeof window&&void 0!==window.document||!function(){onmessage=function(r){r&&r.W&&r.W.action==or&&e.decompress(r.W.W,r.W.cbn)}}(),{decompress:rr}}();this.LZMA=this.LZMA_WORKER=e;
"""

def decode_hashlink(hashlink: str):
    short_hashlink = f"{hashlink[:6]}...{hashlink[-6:]}"
    version = "Unknown"
    try:
        logging.info(f"Starting decode_hashlink for {short_hashlink}")
        # Check for reroute trick (data:text/html;charset=utf-8;base64)
        reroute_match = re.match(r"https://itty\.bitty\.site/[^#]*#(?:[^/]*)/?(?:#|/)?data:text/html;charset=utf-8;base64,(.+)", hashlink)
        if reroute_match:
            version = "PvtPpr v0 (reroute)"
            logging.info(f"Phase: Reroute check")
            b64_data = reroute_match.group(1)
            try:
                decoded_html = base64.b64decode(b64_data).decode('utf-8')
                logging.info(f"Phase: Reroute success (Version: {version})")
                return decoded_html, version
            except Exception as e:
                logging.error(f"Invalid base64 data in reroute for {short_hashlink}: {e}")
                return f"Failed to decode hashlink: Invalid base64 data in reroute", version

        # Check for standard IBS v1/iPvtPpr or PvtPpr v0 format (#title/?base64data)
        standard_match = re.match(r"https://itty\.bitty\.site/#(.*?)/\?(.*)", hashlink)
        if standard_match:
            version = "IBS v1 / PvtPpr v1"
            logging.info(f"Phase: Standard format check")
            _, b64_part = standard_match.groups()
            # Dynamic padding attempts
            for padding in range(4):
                try:
                    padded_b64 = b64_part + '=' * padding
                    logging.info(f"Phase: Padding attempt with {padding} '=' characters for {short_hashlink}")
                    compressed = base64.b64decode(padded_b64)
                    header_lengths = [0, 5, 9, 13]
                    for skip in header_lengths:
                        try:
                            decompressed = lzma.decompress(compressed[skip:], format=lzma.FORMAT_ALONE)
                            logging.info(f"Phase: Padding success (Version: {version}) for {short_hashlink}")
                            return decompressed.decode('utf-8'), version
                        except lzma.LZMAError as lzma_err:
                            logging.error(f"LZMA error with skip {skip} for {short_hashlink}: {lzma_err}")
                            continue
                except base64.binascii.Error as base_err:
                    logging.error(f"Padding attempt {padding} failed for {short_hashlink}: {base_err}")
                    continue

        # Try JS fail-safe for PvtPpr v0
        logging.info(f"Phase: JS decompression attempt for {short_hashlink}")
        try:
            version = "PvtPpr v0 (JS worker)"
            ctx = execjs.compile(JS_LZMA_WORKER)
            if standard_match:
                _, b64_part = standard_match.groups()
            else:
                # Fallback for non-standard format
                b64_part = hashlink.split('/?')[-1]
            padded_b64 = b64_part + '=' * ((4 - len(b64_part) % 4) % 4)
            compressed = base64.b64decode(padded_b64)
            compressed_list = list(compressed)
            decompressed = ctx.eval(f"LZMA.decompress(new Uint8Array({compressed_list}))")
            if isinstance(decompressed, str):
                logging.info(f"Phase: JS decompression success (Version: {version}) for {short_hashlink}")
                return decompressed, version
            elif isinstance(decompressed, bytes):
                logging.info(f"Phase: JS decompression success (Version: {version}) for {short_hashlink}")
                return decompressed.decode('utf-8'), version
        except (execjs.Error, base64.binascii.Error) as js_err:
            logging.error(f"JS decompression failed for {short_hashlink}: {js_err}")
            # Continue to IBS fetch

        # Final fail-safe: IBS fetch with enhanced handling
        logging.info(f"Phase: IBS fetch attempt for {short_hashlink}")
        try:
            version = "Fail-safe (official site)"
            response = requests.get(hashlink, timeout=10)
            if response.status_code == 200:
                html_content = response.text
                logging.info(f"IBS fetch: Received response (status: {response.status_code}) for {short_hashlink}")
                # Auto-accept persistent storage prompt
                if '<div id="toast">' in html_content:
                    html_content = html_content.replace('<button onclick="dismiss()">I understand</button>', '<script>dismiss();</script>')
                    html_content = re.sub(r'<div id="toast".*?</div>', '', html_content, flags=re.DOTALL)
                    logging.info(f"IBS fetch: Auto-accepted persistent storage prompt for {short_hashlink}")
                # Handle v1 redirect
                redirect_match = re.search(r'<script nomodule> location\.href = "/v1/" \+ location\.hash </script>', html_content)
                if redirect_match:
                    hash_part = hashlink.split('#')[1]
                    retry_hashlink = f"https://itty.bitty.site/v1/#{hash_part}"
                    logging.info(f"IBS fetch: Detected v1 redirect, retrying with {retry_hashlink[:6]}...{retry_hashlink[-6:]}")
                    retry_response = requests.get(retry_hashlink, timeout=10)
                    if retry_response.status_code == 200:
                        retry_html = retry_response.text
                        if '<div id="toast">' in retry_html:
                            retry_html = retry_html.replace('<button onclick="dismiss()">I understand</button>', '<script>dismiss();</script>')
                            retry_html = re.sub(r'<div id="toast".*?</div>', '', retry_html, flags=re.DOTALL)
                            logging.info(f"IBS fetch: Auto-accepted persistent storage prompt on retry for {short_hashlink}")
                        body_match = re.search(r'<body[^>]*>(.*?)</body>', retry_html, re.IGNORECASE | re.DOTALL)
                        if body_match:
                            logging.info(f"Phase: IBS fetch success (via v1 retry) for {short_hashlink}")
                            return body_match.group(1).strip(), f"{version} (via v1 retry)"
                        else:
                            logging.error(f"IBS fetch: No body content in retry HTML for {short_hashlink}: {retry_html[:500]}...")
                    else:
                        logging.error(f"IBS fetch: Retry failed with status {retry_response.status_code} for {short_hashlink}")
                # Try extracting body from initial response
                body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.IGNORECASE | re.DOTALL)
                if body_match:
                    logging.info(f"Phase: IBS fetch success for {short_hashlink}")
                    return body_match.group(1).strip(), version
                else:
                    logging.error(f"IBS fetch: No body content in initial HTML for {short_hashlink}: {html_content[:500]}...")
                return f"Failed to decode hashlink: Unable to extract content from official site response", version
            else:
                logging.error(f"IBS fetch: Initial request failed with status {response.status_code} for {short_hashlink}")
                return f"Failed to decode hashlink: Official site returned status {response.status_code}", version
        except requests.exceptions.ConnectionError:
            logging.error(f"No network connection available for official site fetch for {short_hashlink}")
            return f"Failed to decode hashlink: No network connection available for official site fetch", version
        except Exception as e:
            logging.error(f"Official site fetch failed for {short_hashlink}: {e}")
            return f"Failed to decode hashlink: Official site fetch failed - {e}", version

        return "Failed to decode hashlink: Unknown format", version
    except Exception as e:
        logging.error(f"Unexpected error in decode_hashlink for {short_hashlink}: {e}")
        return f"Failed to decode hashlink: {e}", version

def main():
    title = TitleTextInput()
    title.value = "My First PvtPpr"
    body = BodyTextField()
    body.value = "<p>Hello, this is a test PvtPpr!</p>"
    link = LinkInput()
    link.value = "https://example.com/image.jpg"

    hashlink = generate_hashlink(title, body, link, btc_snapshot="dummy_snapshot_hash")
    print(f"Generated Hashlink: {hashlink}")

    decoded, version = decode_hashlink(hashlink)
    print(f"Decoded Content (Version: {version}):\n{decoded}")

    example_hashlink = "https://itty.bitty.site/#Streaming%204%20Free/?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"
    decoded, version = decode_hashlink(example_hashlink)
    print(f"Decoded Example Content (Version: {version}):\n{decoded}")

if __name__ == "__main__":
    main()