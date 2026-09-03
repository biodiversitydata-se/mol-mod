#!/usr/bin/env python3
"""
Read-only audit of mol-mod export zips: version consistency per zip.

For every *.zip in DIR (default: current dir) it reports three version
numbers and flags mismatches:

  pkgId   - from eml.xml   <eml:eml packageId=".../vX.Y">   (authoritative)
  EMLcit  - from the resource <citation> element (no identifier=) in eml.xml
  README  - from the "Citation:" line in README.txt

STATUS values:
  ok                         all present versions agree
  EML OFF-BY-ONE             EMLcit == pkgId + 1  (the IPT "next version" bug)
  EML mismatch               EMLcit != pkgId, not off-by-one
  README != pkgId            README citation version disagrees with packageId
  no EML citation version    no <citation> (no id) with a Version in eml.xml
  no packageId               eml.xml has no packageId

Writes nothing.

Usage:  audit-export-versions.py [DIR]
"""
import html
import os
import re
import sys
import zipfile

PKG = re.compile(r'packageId="[^"]*/v([0-9]+(?:\.[0-9]+)+)"')
CITEL = re.compile(r'<citation\b([^>]*)>(.*?)</citation>', re.S)
VER = re.compile(r'\bVersion\s+([0-9]+(?:\.[0-9]+)+)')


def res_citation(eml: str):
    for attrs, body in CITEL.findall(eml):
        if 'identifier' not in attrs:
            return html.unescape(re.sub(r'\s+', ' ', body)).strip()
    return None


def as_tuple(v):
    return tuple(int(x) for x in v.split('.')) if v else None


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else '.'
    if not os.path.isdir(d):
        print(f'No such directory: {d}', file=sys.stderr)
        return 1
    zips = sorted(f for f in os.listdir(d) if f.endswith('.zip'))
    if not zips:
        print(f'No .zip files in {d}', file=sys.stderr)
        return 0

    hdr = f'{"ZIP":38} {"pkgId":7} {"EMLcit":7} {"README":7}  STATUS'
    print(hdr)
    print('-' * len(hdr))

    counts = {}
    for name in zips:
        path = os.path.join(d, name)
        try:
            with zipfile.ZipFile(path) as z:
                mem = set(z.namelist())
                eml = (z.read('eml.xml').decode('utf-8', 'replace')
                       if 'eml.xml' in mem else '')
                rd = (z.read('README.txt').decode('utf-8', 'replace')
                      if 'README.txt' in mem else '')
        except zipfile.BadZipFile:
            print(f'{name:38} {"-":7} {"-":7} {"-":7}  bad zip')
            counts['bad zip'] = counts.get('bad zip', 0) + 1
            continue

        pkg_m = PKG.search(eml)
        pkg_v = pkg_m.group(1) if pkg_m else None
        cit = res_citation(eml)
        cit_m = VER.search(cit) if cit else None
        cit_v = cit_m.group(1) if cit_m else None
        rl = next((l for l in rd.splitlines()
                   if l.startswith('Citation:')), '')
        rd_m = VER.search(rl)
        rd_v = rd_m.group(1) if rd_m else None

        if not pkg_v:
            st = 'no packageId'
        elif not cit_v:
            st = 'no EML citation version'
        else:
            pt, ct = as_tuple(pkg_v), as_tuple(cit_v)
            if ct == pt:
                if rd_v is None or rd_v == pkg_v:
                    st = 'ok'
                else:
                    st = f'README != pkgId (README={rd_v})'
            elif (len(ct) == len(pt) and ct[:-1] == pt[:-1]
                  and ct[-1] == pt[-1] + 1):
                st = f'EML OFF-BY-ONE (cit={cit_v} pkg={pkg_v})'
            else:
                st = f'EML mismatch (cit={cit_v} pkg={pkg_v})'

        key = st.split(' (')[0]
        counts[key] = counts.get(key, 0) + 1
        print(f'{name:38} {pkg_v or "-":7} {cit_v or "-":7} '
              f'{rd_v or "-":7}  {st}')

    print()
    for k in sorted(counts):
        print(f'{counts[k]:3}  {k}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
